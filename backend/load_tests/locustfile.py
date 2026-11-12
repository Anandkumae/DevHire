import random
import uuid
from locust import HttpUser, between, task


class DevHirePublicUser(HttpUser):
    """Simulates anonymous public traffic visiting the job board."""
    wait_time = between(1, 3)

    @task(5)
    def browse_jobs(self):
        self.client.get("/api/v1/jobs?limit=10")

    @task(3)
    def search_jobs(self):
        keywords = ["python", "fastapi", "react", "engineer", "lead"]
        query = random.choice(keywords)
        self.client.get(f"/api/v1/jobs?search={query}&limit=5")

    @task(2)
    def health_check(self):
        self.client.get("/health")
        self.client.get("/ready")


class CandidateUser(HttpUser):
    """Simulates authenticated candidate behavior: searching, applying, tracking status."""
    wait_time = between(1, 3)

    def on_start(self):
        """Log in as candidate using pre-seeded credentials."""
        self.email = "candidate@gmail.com"
        self.password = "Password123!"

        res = self.client.post(
            "/api/v1/auth/login",
            json={"email": self.email, "password": self.password}
        )
        if res.status_code == 200:
            token = res.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            self.headers = {}

    @task(4)
    def browse_and_filter_jobs(self):
        self.client.get("/api/v1/jobs?limit=20", headers=self.headers)

    @task(2)
    def check_my_applications(self):
        self.client.get("/api/v1/applications/me", headers=self.headers)

    @task(1)
    def check_notifications(self):
        self.client.get("/api/v1/notifications", headers=self.headers)


class RecruiterUser(HttpUser):
    """Simulates recruiter behavior: managing jobs, ranking candidates by AI match score."""
    wait_time = between(1, 3)

    def on_start(self):
        self.email = "recruiter@techcorp.com"
        self.password = "Password123!"

        res = self.client.post(
            "/api/v1/auth/login",
            json={"email": self.email, "password": self.password}
        )
        if res.status_code == 200:
            token = res.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            self.headers = {}

    @task(3)
    def view_active_jobs(self):
        self.client.get("/api/v1/jobs", headers=self.headers)

    @task(1)
    def poll_notifications(self):
        self.client.get("/api/v1/notifications?unread_only=true", headers=self.headers)

