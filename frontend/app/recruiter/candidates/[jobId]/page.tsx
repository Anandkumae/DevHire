"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ApplicationStatus, Job, RankedCandidate } from "@/types";
import { api } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";
import {
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Clock,
  Mail,
  RefreshCw,
  Sparkles,
  User as UserIcon,
  Video,
  XCircle,
} from "lucide-react";

export default function JobRankedCandidatesPage() {
  const router = useRouter();
  const params = useParams();
  const jobId = params.jobId as string;
  const { user, isRecruiter, isAdmin, loading: authLoading } = useAuth();

  const [job, setJob] = useState<Job | null>(null);
  const [candidates, setCandidates] = useState<RankedCandidate[]>([]);
  const [loading, setLoading] = useState(true);

  // Interview Schedule Modal
  const [selectedCandidate, setSelectedCandidate] = useState<RankedCandidate | null>(null);
  const [interviewModalOpen, setInterviewModalOpen] = useState(false);
  const [roundName, setRoundName] = useState("Technical Round 1");
  const [interviewType, setInterviewType] = useState("video");
  const [scheduledAt, setScheduledAt] = useState("");
  const [meetingLink, setMeetingLink] = useState("https://meet.google.com/devhire-interview");
  const [durationMins, setDurationMins] = useState(60);
  const [scheduling, setScheduling] = useState(false);

  useEffect(() => {
    if (!authLoading) {
      if (!user || (!isRecruiter && !isAdmin)) {
        router.push("/login");
        return;
      }
      loadCandidates();
    }
  }, [user, isRecruiter, isAdmin, authLoading, jobId]);

  const loadCandidates = async () => {
    setLoading(true);
    try {
      const [jobData, candidateList] = await Promise.all([
        api.getJob(jobId),
        api.getRankedCandidates(jobId),
      ]);
      setJob(jobData);
      setCandidates(candidateList);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (applicationId: string, newStatus: ApplicationStatus) => {
    try {
      await api.updateApplicationStatus(applicationId, newStatus);
      setCandidates((prev) =>
        prev.map((c) => (c.application_id === applicationId ? { ...c, status: newStatus } : c))
      );
    } catch (err: any) {
      alert(err.message || "Failed to update status");
    }
  };

  const handleScheduleInterview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCandidate) return;

    setScheduling(true);
    try {
      await api.scheduleInterview({
        application_id: selectedCandidate.application_id,
        round_name: roundName,
        interview_type: interviewType,
        scheduled_at: new Date(scheduledAt || Date.now() + 86400000).toISOString(),
        duration_minutes: durationMins,
        meeting_link: meetingLink,
      });

      // Advance status to interview if not already
      await api.updateApplicationStatus(selectedCandidate.application_id, "interview");
      setCandidates((prev) =>
        prev.map((c) =>
          c.application_id === selectedCandidate.application_id
            ? { ...c, status: "interview" }
            : c
        )
      );
      setInterviewModalOpen(false);
      alert("Interview invitation sent successfully!");
    } catch (err: any) {
      alert(err.message || "Failed to schedule interview");
    } finally {
      setScheduling(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Back button */}
      <Link
        href="/recruiter/dashboard"
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-indigo-600 transition mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Dashboard
      </Link>

      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
        <div>
          <span className="text-xs font-semibold text-indigo-600 uppercase tracking-wider">
            AI Applicant Evaluation
          </span>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight mt-0.5">
            {job?.title || "Requisition"} Candidates
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Ranked descending by TF-IDF contextual similarity and technical skill alignment.
          </p>
        </div>

        <button
          onClick={loadCandidates}
          className="px-3.5 py-2 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-sm transition flex items-center gap-1.5"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Re-Rank
        </button>
      </div>

      {/* Candidates List */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-44 bg-slate-100 rounded-3xl animate-pulse" />
          ))}
        </div>
      ) : candidates.length === 0 ? (
        <div className="py-20 text-center bg-white rounded-3xl border border-dashed border-slate-300">
          <UserIcon className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-slate-800">No applications received yet</h3>
          <p className="text-xs text-slate-500 mt-1">
            When candidates submit applications, the AI matching engine will rank them automatically.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {candidates.map((cand, index) => {
            const score = cand.match_score;
            const overallScore = cand.overall_score || score?.overall_score || 0;

            const badgeColor =
              overallScore >= 80
                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                : overallScore >= 60
                ? "bg-indigo-50 text-indigo-700 border-indigo-200"
                : overallScore >= 45
                ? "bg-amber-50 text-amber-700 border-amber-200"
                : "bg-slate-100 text-slate-600 border-slate-200";

            return (
              <div
                key={cand.application_id}
                className="bg-white rounded-3xl p-6 border border-slate-200/90 shadow-sm hover:shadow-md transition"
              >
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 pb-4 border-b border-slate-100">
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-2xl bg-indigo-50 text-indigo-700 font-bold text-sm flex items-center justify-center shrink-0">
                      #{index + 1}
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-slate-900">
                        {cand.candidate_name}
                      </h3>
                      <div className="flex items-center gap-3 text-xs text-slate-500 mt-0.5">
                        <span className="flex items-center gap-1">
                          <Mail className="w-3.5 h-3.5" /> {cand.candidate_email}
                        </span>
                        <span>
                          Applied: {new Date(cand.applied_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    {/* AI Score Badge */}
                    <div className={`px-4 py-2 rounded-2xl border ${badgeColor} flex items-center gap-2`}>
                      <Sparkles className="w-4 h-4 shrink-0" />
                      <div>
                        <span className="text-xs font-black block leading-none">{overallScore}%</span>
                        <span className="text-[10px] font-semibold opacity-80">
                          {overallScore >= 80 ? "Strong Match" : overallScore >= 60 ? "Good Match" : "Moderate"}
                        </span>
                      </div>
                    </div>

                    {/* Status Changer */}
                    <select
                      value={cand.status}
                      onChange={(e) =>
                        handleStatusChange(cand.application_id, e.target.value as ApplicationStatus)
                      }
                      className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:outline-none capitalize"
                    >
                      <option value="applied">Applied</option>
                      <option value="under_review">Under Review</option>
                      <option value="shortlisted">Shortlisted</option>
                      <option value="interview">Interview</option>
                      <option value="selected">Selected</option>
                      <option value="rejected">Rejected</option>
                    </select>

                    {/* Interview Action */}
                    <button
                      onClick={() => {
                        setSelectedCandidate(cand);
                        setInterviewModalOpen(true);
                      }}
                      className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-sm transition flex items-center gap-1.5"
                    >
                      <Video className="w-3.5 h-3.5" /> Interview
                    </button>
                  </div>
                </div>

                {/* Score Breakdown & Explainability */}
                {score && (
                  <div className="mt-4 pt-2">
                    <div className="flex flex-wrap items-center gap-2 mb-3">
                      <span className="text-xs text-slate-400">Component Scores:</span>
                      <span className="px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 text-[11px] font-medium">
                        Skills: {score.skills_score}%
                      </span>
                      <span className="px-2 py-0.5 rounded-md bg-violet-50 text-violet-700 text-[11px] font-medium">
                        Semantic: {score.semantic_score}%
                      </span>
                      <span className="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 text-[11px] font-medium">
                        Experience: {score.experience_score}%
                      </span>
                    </div>

                    {/* Matched skills */}
                    {score.matching_skills.length > 0 && (
                      <div className="mb-2 flex flex-wrap items-center gap-1.5">
                        <span className="text-[11px] font-semibold text-emerald-800 mr-1">
                          Matched Skills:
                        </span>
                        {score.matching_skills.map((s) => (
                          <span
                            key={s}
                            className="px-2 py-0.5 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-medium"
                          >
                            ✓ {s}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Missing skills */}
                    {score.missing_skills.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-[11px] font-semibold text-slate-500 mr-1">
                          Missing Skills:
                        </span>
                        {score.missing_skills.map((s) => (
                          <span
                            key={s}
                            className="px-2 py-0.5 rounded-md bg-slate-100 border border-slate-200 text-slate-600 text-xs font-medium"
                          >
                            ✕ {s}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Summary Recommendation */}
                    {score.summary && (
                      <p className="mt-3 text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-100 italic">
                        "{score.summary}"
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Schedule Interview Modal */}
      {interviewModalOpen && selectedCandidate && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl shadow-2xl max-w-md w-full p-6 sm:p-8 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">
                Schedule Interview with {selectedCandidate.candidate_name}
              </h3>
              <button onClick={() => setInterviewModalOpen(false)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>

            <form onSubmit={handleScheduleInterview} className="mt-4 space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Round Name</label>
                <input
                  type="text"
                  required
                  value={roundName}
                  onChange={(e) => setRoundName(e.target.value)}
                  placeholder="System Design / Technical Round 1"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Date & Time</label>
                <input
                  type="datetime-local"
                  required
                  value={scheduledAt}
                  onChange={(e) => setScheduledAt(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Meeting Link (Google Meet / Zoom)</label>
                <input
                  type="url"
                  required
                  value={meetingLink}
                  onChange={(e) => setMeetingLink(e.target.value)}
                  placeholder="https://meet.google.com/xyz-abcd-efg"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Duration (minutes)</label>
                <input
                  type="number"
                  min={15}
                  max={180}
                  value={durationMins}
                  onChange={(e) => setDurationMins(Number(e.target.value))}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setInterviewModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={scheduling}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-sm transition disabled:opacity-50"
                >
                  {scheduling ? "Scheduling..." : "Send Invitation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

