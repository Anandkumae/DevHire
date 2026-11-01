"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Company, Job } from "@/types";
import { api } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";
import {
  Briefcase,
  Building2,
  Calendar,
  DollarSign,
  MapPin,
  Plus,
  RefreshCw,
  Sparkles,
  Users,
  X,
} from "lucide-react";

export default function RecruiterDashboardPage() {
  const router = useRouter();
  const { user, isRecruiter, isAdmin, loading: authLoading } = useAuth();
  const [company, setCompany] = useState<Company | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  // New Company Modal
  const [companyModalOpen, setCompanyModalOpen] = useState(false);
  const [compName, setCompName] = useState("");
  const [compIndustry, setCompIndustry] = useState("");
  const [compLocation, setCompLocation] = useState("");
  const [creatingComp, setCreatingComp] = useState(false);

  // Post Job Modal
  const [jobModalOpen, setJobModalOpen] = useState(false);
  const [jobTitle, setJobTitle] = useState("");
  const [jobDesc, setJobDesc] = useState("");
  const [jobLocation, setJobLocation] = useState("");
  const [jobEmpType, setJobEmpType] = useState("full_time");
  const [jobExpLevel, setJobExpLevel] = useState("mid_level");
  const [jobSalaryMin, setJobSalaryMin] = useState<number | undefined>();
  const [jobSalaryMax, setJobSalaryMax] = useState<number | undefined>();
  const [jobSkillsStr, setJobSkillsStr] = useState("");
  const [postingJob, setPostingJob] = useState(false);
  const [jobError, setJobError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading) {
      if (!user || (!isRecruiter && !isAdmin)) {
        router.push("/login");
        return;
      }
      loadDashboardData();
    }
  }, [user, isRecruiter, isAdmin, authLoading]);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const myComp = await api.getMyCompany().catch(() => null);
      setCompany(myComp);

      const allJobs = await api.listJobs();
      if (myComp) {
        setJobs(allJobs.filter((j) => j.company_id === myComp.id));
      } else {
        setJobs(allJobs);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingComp(true);
    try {
      const created = await api.createCompany({
        name: compName,
        industry: compIndustry,
        location: compLocation,
      });
      setCompany(created);
      setCompanyModalOpen(false);
    } catch (err: any) {
      alert(err.message || "Failed to create company");
    } finally {
      setCreatingComp(false);
    }
  };

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setPostingJob(true);
    setJobError(null);
    try {
      const skillsArray = jobSkillsStr
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      await api.createJob({
        title: jobTitle,
        description: jobDesc,
        location: jobLocation,
        employment_type: jobEmpType,
        experience_level: jobExpLevel,
        salary_min: jobSalaryMin || null,
        salary_max: jobSalaryMax || null,
        status: "published",
        skills: skillsArray as any,
      });

      setJobModalOpen(false);
      // Reset form
      setJobTitle("");
      setJobDesc("");
      setJobLocation("");
      setJobSkillsStr("");
      loadDashboardData();
    } catch (err: any) {
      setJobError(err.message || "Failed to publish job");
    } finally {
      setPostingJob(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Recruiter Hub & ATS
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Manage your company profile, publish job requisitions, and rank applicants using AI.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {company && (
            <button
              onClick={() => setJobModalOpen(true)}
              className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-md shadow-indigo-100 transition flex items-center gap-1.5"
            >
              <Plus className="w-4 h-4" /> Post New Job
            </button>
          )}
          <button
            onClick={loadDashboardData}
            className="p-2.5 rounded-xl bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 shadow-sm transition"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Company Verification Banner */}
      {!loading && !company && (
        <div className="mb-8 p-6 bg-gradient-to-r from-indigo-50 to-violet-50 rounded-3xl border border-indigo-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-indigo-600 text-white flex items-center justify-center shadow-md">
              <Building2 className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">Register Your Company Profile</h3>
              <p className="text-xs text-slate-600 mt-0.5">
                You must register an organization before publishing jobs and receiving AI candidate rankings.
              </p>
            </div>
          </div>
          <button
            onClick={() => setCompanyModalOpen(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-sm transition"
          >
            Create Company Profile
          </button>
        </div>
      )}

      {/* Company Info Header */}
      {company && (
        <div className="mb-8 p-6 bg-white rounded-3xl border border-slate-200/90 shadow-sm flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-100 text-indigo-700 font-bold text-xl flex items-center justify-center">
              {company.name.charAt(0)}
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">{company.name}</h2>
              <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                <span>{company.industry || "Technology"}</span>
                {company.location && <span>• {company.location}</span>}
              </div>
            </div>
          </div>
          <div className="text-right">
            <span className="text-xs font-semibold text-indigo-600 bg-indigo-50 border border-indigo-100 px-3 py-1 rounded-full">
              {jobs.length} Active Listings
            </span>
          </div>
        </div>
      )}

      {/* Posted Jobs List */}
      <div>
        <h2 className="text-lg font-bold text-slate-900 mb-4">Posted Requisitions</h2>

        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-28 bg-slate-100 rounded-2xl animate-pulse" />
            ))}
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-3xl border border-dashed border-slate-300">
            <Briefcase className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <h3 className="text-sm font-semibold text-slate-800">No jobs posted yet</h3>
            <p className="text-xs text-slate-500 mt-1">Click 'Post New Job' above to start receiving candidates.</p>
          </div>
        ) : (
          <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm overflow-hidden divide-y divide-slate-100">
            {jobs.map((job) => (
              <div key={job.id} className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50/60 transition">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-slate-900">{job.title}</h3>
                    <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-[10px] font-semibold border border-emerald-200 capitalize">
                      {job.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5" /> {job.location}
                    </span>
                    <span className="flex items-center gap-1 capitalize">
                      <Briefcase className="w-3.5 h-3.5" /> {job.experience_level.replace("_", " ")}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <Link
                    href={`/recruiter/candidates/${job.id}`}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-sm transition flex items-center gap-1.5"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    Rank Candidates With AI
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Company Modal */}
      {companyModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl shadow-2xl max-w-md w-full p-6 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">Register Company</h3>
              <button onClick={() => setCompanyModalOpen(false)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>
            <form onSubmit={handleCreateCompany} className="mt-4 space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Company Name</label>
                <input
                  type="text"
                  required
                  value={compName}
                  onChange={(e) => setCompName(e.target.value)}
                  placeholder="TechNova Solutions"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Industry</label>
                <input
                  type="text"
                  value={compIndustry}
                  onChange={(e) => setCompIndustry(e.target.value)}
                  placeholder="Artificial Intelligence / SaaS"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Location</label>
                <input
                  type="text"
                  value={compLocation}
                  onChange={(e) => setCompLocation(e.target.value)}
                  placeholder="Bengaluru, India"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none"
                />
              </div>
              <button
                type="submit"
                disabled={creatingComp}
                className="w-full mt-2 py-2.5 bg-indigo-600 text-white rounded-xl text-xs font-semibold hover:bg-indigo-700 transition"
              >
                {creatingComp ? "Registering..." : "Save Company"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Post Job Modal */}
      {jobModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto p-6 sm:p-8 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">Post New Requisition</h3>
              <button onClick={() => setJobModalOpen(false)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>

            {jobError && (
              <div className="mt-3 p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 font-medium">
                {jobError}
              </div>
            )}

            <form onSubmit={handleCreateJob} className="mt-4 space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Job Title</label>
                <input
                  type="text"
                  required
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                  placeholder="Senior Python Backend Engineer"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Description (used for AI semantic matching)</label>
                <textarea
                  rows={4}
                  required
                  value={jobDesc}
                  onChange={(e) => setJobDesc(e.target.value)}
                  placeholder="We are looking for a senior backend engineer with deep experience in FastAPI, PostgreSQL, and distributed task queues..."
                  className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Location</label>
                  <input
                    type="text"
                    required
                    value={jobLocation}
                    onChange={(e) => setJobLocation(e.target.value)}
                    placeholder="Bengaluru / Remote"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Employment Type</label>
                  <select
                    value={jobEmpType}
                    onChange={(e) => setJobEmpType(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none"
                  >
                    <option value="full_time">Full Time</option>
                    <option value="part_time">Part Time</option>
                    <option value="contract">Contract</option>
                    <option value="internship">Internship</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Experience Level</label>
                <select
                  value={jobExpLevel}
                  onChange={(e) => setJobExpLevel(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none"
                >
                  <option value="entry_level">Entry Level</option>
                  <option value="mid_level">Mid Level</option>
                  <option value="senior">Senior</option>
                  <option value="lead">Lead</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Target Technical Skills (comma separated)
                </label>
                <input
                  type="text"
                  value={jobSkillsStr}
                  onChange={(e) => setJobSkillsStr(e.target.value)}
                  placeholder="Python, FastAPI, PostgreSQL, Docker, AWS"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setJobModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={postingJob}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-sm transition disabled:opacity-50"
                >
                  {postingJob ? "Publishing..." : "Publish Job"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

