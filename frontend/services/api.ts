import {
  Application,
  ApplicationMatchScore,
  Company,
  Interview,
  Job,
  NotificationItem,
  RankedCandidate,
  Resume,
  User,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiService {
  private getAccessToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("devhire_access_token");
  }

  private setTokens(accessToken: string, refreshToken?: string) {
    if (typeof window === "undefined") return;
    localStorage.setItem("devhire_access_token", accessToken);
    if (refreshToken) {
      localStorage.setItem("devhire_refresh_token", refreshToken);
    }
  }

  public clearTokens() {
    if (typeof window === "undefined") return;
    localStorage.removeItem("devhire_access_token");
    localStorage.removeItem("devhire_refresh_token");
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getAccessToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    let url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint}`;
    let response = await fetch(url, { ...options, headers });

    // Handle token expiration & automatic refresh
    if (response.status === 401 && typeof window !== "undefined") {
      const refreshToken = localStorage.getItem("devhire_refresh_token");
      if (refreshToken) {
        try {
          const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refreshToken }),
          });
          if (refreshRes.ok) {
            const data = await refreshRes.json();
            this.setTokens(data.access_token, data.refresh_token);
            headers["Authorization"] = `Bearer ${data.access_token}`;
            response = await fetch(url, { ...options, headers });
          } else {
            this.clearTokens();
          }
        } catch {
          this.clearTokens();
        }
      }
    }

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      const detail = errorBody.detail || `Request failed with status ${response.status}`;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  // --- Auth APIs ---
  async register(data: { full_name: string; email: string; password: string }) {
    return this.request<{ id: string; email: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async login(data: { email: string; password: string }) {
    const res = await this.request<{ access_token: string; refresh_token: string }>(
      "/auth/login",
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
    this.setTokens(res.access_token, res.refresh_token);
    return res;
  }

  async getMe() {
    return this.request<User>("/protected/me");
  }

  // --- Companies APIs ---
  async createCompany(data: { name: string; description?: string; industry?: string; location?: string; website?: string }) {
    return this.request<Company>("/companies", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getMyCompany() {
    return this.request<Company>("/companies/me");
  }

  // --- Jobs APIs ---
  async listJobs(params?: { search?: string; location?: string; employment_type?: string; experience_level?: string; min_salary?: number; max_salary?: number }) {
    const query = new URLSearchParams();
    if (params?.search) query.append("search", params.search);
    if (params?.location) query.append("location", params.location);
    if (params?.employment_type) query.append("employment_type", params.employment_type);
    if (params?.experience_level) query.append("experience_level", params.experience_level);
    if (params?.min_salary) query.append("min_salary", params.min_salary.toString());
    if (params?.max_salary) query.append("max_salary", params.max_salary.toString());

    const qs = query.toString() ? `?${query.toString()}` : "";
    return this.request<Job[]>(`/jobs${qs}`);
  }

  async getJob(id: string) {
    return this.request<Job>(`/jobs/${id}`);
  }

  async createJob(data: Partial<Job>) {
    return this.request<Job>("/jobs", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // --- Applications APIs ---
  async applyToJob(data: { job_id: string; cover_letter?: string; resume_url?: string }) {
    return this.request<Application>("/applications", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getMyApplications() {
    return this.request<Application[]>("/applications/me");
  }

  async getJobApplications(jobId: string) {
    return this.request<Application[]>(`/applications/job/${jobId}`);
  }

  async updateApplicationStatus(applicationId: string, status: string, notes?: string) {
    return this.request<Application>(`/applications/${applicationId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status, notes }),
    });
  }

  // --- AI Resume Matching APIs ---
  async getRankedCandidates(jobId: string) {
    return this.request<RankedCandidate[]>(`/jobs/${jobId}/ranked-candidates`);
  }

  async getMatchScore(applicationId: string) {
    return this.request<ApplicationMatchScore>(`/applications/${applicationId}/match-score`);
  }

  async recomputeMatchScore(applicationId: string) {
    return this.request<ApplicationMatchScore>(`/applications/${applicationId}/recompute-match`, {
      method: "POST",
    });
  }

  // --- Resumes APIs ---
  async getMyResumes() {
    return this.request<Resume[]>("/resumes");
  }

  async uploadResume(file: File, isPrimary: boolean = true) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("is_primary", isPrimary.toString());

    const token = this.getAccessToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE_URL}/resumes/upload`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Upload failed");
    }
    return res.json() as Promise<Resume>;
  }

  // --- Interviews APIs ---
  async scheduleInterview(data: Partial<Interview>) {
    return this.request<Interview>("/interviews", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getApplicationInterviews(applicationId: string) {
    return this.request<Interview[]>(`/interviews/application/${applicationId}`);
  }

  // --- Notifications APIs ---
  async getNotifications(unreadOnly: boolean = false) {
    return this.request<NotificationItem[]>(`/notifications?unread_only=${unreadOnly}`);
  }

  async markNotificationRead(id: string) {
    return this.request<NotificationItem>(`/notifications/${id}/read`, {
      method: "PATCH",
    });
  }

  async markAllNotificationsRead() {
    return this.request<{ message: string; marked_read_count: number }>("/notifications/mark-all-read", {
      method: "POST",
    });
  }
}

export const api = new ApiService();

