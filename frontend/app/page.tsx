"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Job } from "@/types";
import { api } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";
import {
  Briefcase,
  Building2,
  Calendar,
  CheckCircle,
  Clock,
  DollarSign,
  Filter,
  MapPin,
  Search,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react";

export default function HomePage() {
  const router = useRouter();
  const { user } = useAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState("");
  const [location, setLocation] = useState("");
  const [employmentType, setEmploymentType] = useState("");
  const [experienceLevel, setExperienceLevel] = useState("");

  // Apply Modal state
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [coverLetter, setCoverLetter] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [applying, setApplying] = useState(false);
  const [applySuccess, setApplySuccess] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const data = await api.listJobs({
        search: search || undefined,
        location: location || undefined,
        employment_type: employmentType || undefined,
        experience_level: experienceLevel || undefined,
      });
      // Show only published jobs
      setJobs(data.filter((j) => j.status === "published"));
    } catch (err) {
      console.error("Error fetching jobs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [employmentType, experienceLevel]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchJobs();
  };

  const handleApply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedJob) return;

    if (!user) {
      router.push("/login");
      return;
    }

    setApplying(true);
    setApplyError(null);

    try {
      let resumeUrl: string | undefined = undefined;

      // If user uploaded a new resume file
      if (resumeFile) {
        const uploaded = await api.uploadResume(resumeFile, true);
        resumeUrl = uploaded.download_url;
      }

      await api.applyToJob({
        job_id: selectedJob.id,
        cover_letter: coverLetter || undefined,
        resume_url: resumeUrl,
      });

      setApplySuccess(true);
    } catch (err: any) {
      setApplyError(err.message || "Failed to submit application");
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Hero Header */}
      <div className="text-center max-w-3xl mx-auto mb-12">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-semibold mb-4">
          <Sparkles className="w-3.5 h-3.5" />
          AI-Powered Candidate Matching Engine
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold text-slate-900 tracking-tight leading-tight">
          Find High-Impact Tech Roles Matched To Your Resume
        </h1>
        <p className="mt-4 text-base sm:text-lg text-slate-600 leading-relaxed">
          DevHire pairs your technical skills with engineering opportunities using TF-IDF semantic relevance and real-time interview pipelines.
        </p>

        {/* Search & Filter Bar */}
        <form
          onSubmit={handleSearchSubmit}
          className="mt-8 p-2 bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200 flex flex-col md:flex-row gap-2"
        >
          <div className="flex-1 relative flex items-center">
            <Search className="w-5 h-5 text-slate-400 absolute left-3.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Job title, keywords, or skills..."
              className="w-full pl-11 pr-4 py-3 bg-transparent text-sm focus:outline-none placeholder:text-slate-400"
            />
          </div>

          <div className="w-full md:w-56 relative flex items-center border-t md:border-t-0 md:border-l border-slate-200">
            <MapPin className="w-5 h-5 text-slate-400 absolute left-3.5" />
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Location or Remote"
              className="w-full pl-11 pr-4 py-3 bg-transparent text-sm focus:outline-none placeholder:text-slate-400"
            />
          </div>

          <button
            type="submit"
            className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-semibold shadow-md shadow-indigo-100 transition"
          >
            Search
          </button>
        </form>

        {/* Quick Filter Pills */}
        <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-xs">
          <span className="text-slate-400 flex items-center gap-1">
            <Filter className="w-3 h-3" /> Filters:
          </span>
          <select
            value={employmentType}
            onChange={(e) => setEmploymentType(e.target.value)}
            className="bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-slate-700 focus:outline-none"
          >
            <option value="">All Employment Types</option>
            <option value="full_time">Full Time</option>
            <option value="part_time">Part Time</option>
            <option value="contract">Contract</option>
            <option value="internship">Internship</option>
          </select>

          <select
            value={experienceLevel}
            onChange={(e) => setExperienceLevel(e.target.value)}
            className="bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-slate-700 focus:outline-none"
          >
            <option value="">All Experience Levels</option>
            <option value="entry_level">Entry Level</option>
            <option value="mid_level">Mid Level</option>
            <option value="senior">Senior</option>
            <option value="lead">Lead</option>
          </select>
        </div>
      </div>

      {/* Jobs Grid */}
      <div className="mt-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold text-slate-900">
            Available Positions ({jobs.length})
          </h2>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-64 bg-slate-100 animate-pulse rounded-2xl" />
            ))}
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-3xl border border-dashed border-slate-300">
            <Briefcase className="w-10 h-10 text-slate-400 mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-slate-800">No jobs found matching your criteria</h3>
            <p className="text-xs text-slate-500 mt-1">Try clearing some filters or searching for generic terms.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {jobs.map((job) => (
              <div
                key={job.id}
                className="bg-white rounded-3xl p-6 border border-slate-200/90 shadow-sm hover:shadow-md transition flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <span className="text-xs font-semibold text-indigo-600 flex items-center gap-1">
                        <Building2 className="w-3.5 h-3.5" />
                        {job.company?.name || "Tech Company"}
                      </span>
                      <h3 className="text-base font-bold text-slate-900 mt-1 group-hover:text-indigo-600 transition">
                        {job.title}
                      </h3>
                    </div>
                    <span className="px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 text-[11px] font-medium capitalize">
                      {job.employment_type.replace("_", " ")}
                    </span>
                  </div>

                  <p className="text-xs text-slate-500 mt-3 line-clamp-3 leading-relaxed">
                    {job.description}
                  </p>

                  {/* Skills tags */}
                  {job.skills && job.skills.length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-1.5">
                      {job.skills.slice(0, 4).map((s) => (
                        <span
                          key={s.id}
                          className="px-2 py-0.5 rounded-md bg-indigo-50/70 border border-indigo-100/60 text-indigo-700 text-[10px] font-medium"
                        >
                          {s.name}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-1 text-slate-500">
                    <MapPin className="w-3.5 h-3.5" />
                    <span>{job.location}</span>
                  </div>

                  <button
                    onClick={() => {
                      setSelectedJob(job);
                      setApplySuccess(false);
                      setApplyError(null);
                    }}
                    className="px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-indigo-600 text-white font-medium transition shadow-sm"
                  >
                    View & Apply
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Application & Details Modal */}
      {selectedJob && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl shadow-2xl max-w-xl w-full max-h-[90vh] overflow-y-auto p-6 sm:p-8 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start justify-between pb-4 border-b border-slate-100">
              <div>
                <span className="text-xs font-semibold text-indigo-600 flex items-center gap-1">
                  <Building2 className="w-3.5 h-3.5" />
                  {selectedJob.company?.name || "Tech Company"}
                </span>
                <h3 className="text-xl font-bold text-slate-900 mt-1">
                  {selectedJob.title}
                </h3>
                <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5" /> {selectedJob.location}
                  </span>
                  <span className="flex items-center gap-1 capitalize">
                    <Briefcase className="w-3.5 h-3.5" /> {selectedJob.experience_level.replace("_", " ")}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setSelectedJob(null)}
                className="p-1 rounded-full text-slate-400 hover:text-slate-600 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {applySuccess ? (
              <div className="py-8 text-center">
                <div className="w-14 h-14 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
                  <CheckCircle className="w-8 h-8" />
                </div>
                <h4 className="text-lg font-bold text-slate-900">Application Submitted!</h4>
                <p className="text-xs text-slate-600 mt-2 max-w-sm mx-auto leading-relaxed">
                  Your application has been received and our AI engine is scoring your resume profile in real time.
                </p>
                <div className="mt-6 flex justify-center gap-3">
                  <Link
                    href="/candidate/applications"
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-sm transition"
                  >
                    View Status & AI Match
                  </Link>
                  <button
                    onClick={() => setSelectedJob(null)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition"
                  >
                    Close
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleApply} className="mt-6 space-y-4">
                <div>
                  <h4 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-1">
                    Job Description
                  </h4>
                  <p className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-xl max-h-36 overflow-y-auto">
                    {selectedJob.description}
                  </p>
                </div>

                {applyError && (
                  <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium">
                    {applyError}
                  </div>
                )}

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Cover Letter (Highlight skills for AI Match)
                  </label>
                  <textarea
                    rows={4}
                    value={coverLetter}
                    onChange={(e) => setCoverLetter(e.target.value)}
                    placeholder="Describe how your experience with Python, FastAPI, and databases makes you a great fit..."
                    className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Upload Resume (PDF only, up to 5MB)
                  </label>
                  <div className="border-2 border-dashed border-slate-200 hover:border-indigo-400 rounded-2xl p-4 text-center cursor-pointer transition bg-slate-50">
                    <input
                      type="file"
                      accept=".pdf"
                      onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
                      className="hidden"
                      id="resume-upload"
                    />
                    <label htmlFor="resume-upload" className="cursor-pointer">
                      <UploadCloud className="w-6 h-6 text-indigo-500 mx-auto mb-1" />
                      <span className="text-xs font-medium text-slate-700 block">
                        {resumeFile ? resumeFile.name : "Click to select a PDF resume"}
                      </span>
                      <span className="text-[10px] text-slate-400">
                        {resumeFile ? `${(resumeFile.size / 1024).toFixed(0)} KB` : "Supports PDF format"}
                      </span>
                    </label>
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setSelectedJob(null)}
                    className="px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={applying}
                    className="px-5 py-2.5 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-md shadow-indigo-100 transition disabled:opacity-50 flex items-center gap-1.5"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    {applying ? "Submitting Application..." : "Submit Application"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

