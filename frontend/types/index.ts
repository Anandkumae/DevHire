export type UserRole = "candidate" | "recruiter" | "admin";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Company {
  id: string;
  name: string;
  description?: string | null;
  website?: string | null;
  industry?: string | null;
  location?: string | null;
  recruiter_id: string;
  created_at: string;
}

export interface Skill {
  id: string;
  name: string;
}

export interface Job {
  id: string;
  company_id: string;
  title: string;
  description: string;
  location: string;
  employment_type: string;
  experience_level: string;
  salary_min?: number | null;
  salary_max?: number | null;
  status: "draft" | "published" | "archived" | "closed";
  skills?: Skill[];
  company?: Company;
  created_at: string;
  updated_at: string;
}

export type ApplicationStatus =
  | "applied"
  | "under_review"
  | "shortlisted"
  | "interview"
  | "selected"
  | "rejected";

export interface ApplicationStatusHistory {
  id: string;
  from_status?: string | null;
  to_status: ApplicationStatus;
  notes?: string | null;
  created_at: string;
}

export interface ApplicationMatchScore {
  id: string;
  application_id: string;
  overall_score: number;
  skills_score: number;
  semantic_score: number;
  experience_score: number;
  matching_skills: string[];
  missing_skills: string[];
  strengths: string[];
  gap_analysis: string[];
  summary?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Application {
  id: string;
  candidate_id: string;
  job_id: string;
  cover_letter?: string | null;
  resume_url?: string | null;
  status: ApplicationStatus;
  created_at: string;
  updated_at: string;
  job?: Job;
  candidate?: User;
  status_history?: ApplicationStatusHistory[];
  match_score?: ApplicationMatchScore | null;
}

export interface RankedCandidate {
  application_id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  status: ApplicationStatus;
  applied_at: string;
  overall_score?: number | null;
  match_score?: ApplicationMatchScore | null;
}

export interface Resume {
  id: string;
  candidate_id: string;
  file_name: string;
  file_size_bytes: number;
  content_type: string;
  is_primary: boolean;
  download_url?: string;
  created_at: string;
}

export interface Interview {
  id: string;
  application_id: string;
  round_name: string;
  interview_type: string;
  scheduled_at: string;
  duration_minutes: number;
  meeting_link?: string | null;
  status: "scheduled" | "completed" | "cancelled" | "rescheduled";
  interviewer_id?: string | null;
}

export interface NotificationItem {
  id: string;
  user_id: string;
  type: string;
  title: string;
  message: string;
  data?: Record<string, any> | null;
  is_read: boolean;
  created_at: string;
}

