"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Application, ApplicationMatchScore } from "@/types";
import { api } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";
import {
  AlertCircle,
  Briefcase,
  Building2,
  Calendar,
  CheckCircle2,
  Clock,
  ExternalLink,
  MapPin,
  RefreshCw,
  Sparkles,
  XCircle,
} from "lucide-react";

const PIPELINE_STAGES = [
  { key: "applied", label: "Applied" },
  { key: "under_review", label: "Under Review" },
  { key: "shortlisted", label: "Shortlisted" },
  { key: "interview", label: "Interview" },
  { key: "selected", label: "Selected" },
];

export default function CandidateApplicationsPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedScore, setSelectedScore] = useState<ApplicationMatchScore | null>(null);
  const [scoreModalOpen, setScoreModalOpen] = useState(false);
  const [loadingScore, setLoadingScore] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
      return;
    }
    if (user) {
      loadApplications();
    }
  }, [user, authLoading]);

  const loadApplications = async () => {
    setLoading(true);
    try {
      const data = await api.getMyApplications();
      setApplications(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleViewMatchScore = async (appId: string) => {
    setLoadingScore(true);
    setScoreModalOpen(true);
    try {
      const score = await api.getMatchScore(appId);
      setSelectedScore(score);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingScore(false);
    }
  };

  const getStageIndex = (status: string) => {
    if (status === "rejected") return -1;
    return PIPELINE_STAGES.findIndex((s) => s.key === status);
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            My Applications
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Track your recruitment pipelines, interview rounds, and AI resume match scores.
          </p>
        </div>
        <button
          onClick={loadApplications}
          className="px-3.5 py-2 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-sm transition flex items-center gap-1.5"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Status
        </button>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-44 bg-slate-100 rounded-3xl animate-pulse" />
          ))}
        </div>
      ) : applications.length === 0 ? (
        <div className="py-20 text-center bg-white rounded-3xl border border-dashed border-slate-300">
          <Briefcase className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-slate-800">No applications submitted yet</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Browse our AI-ranked tech opportunities and submit your profile today.
          </p>
          <Link
            href="/"
            className="mt-5 inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-sm transition"
          >
            Explore Jobs
          </Link>
        </div>
      ) : (
        <div className="space-y-6">
          {applications.map((app) => {
            const currentStageIndex = getStageIndex(app.status);
            const isRejected = app.status === "rejected";

            return (
              <div
                key={app.id}
                className="bg-white rounded-3xl p-6 border border-slate-200/90 shadow-sm hover:shadow-md transition"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-slate-100">
                  <div>
                    <span className="text-xs font-semibold text-indigo-600 flex items-center gap-1">
                      <Building2 className="w-3.5 h-3.5" />
                      {app.job?.company?.name || "Company"}
                    </span>
                    <h3 className="text-lg font-bold text-slate-900 mt-0.5">
                      {app.job?.title || "Role"}
                    </h3>
                    <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5" /> {app.job?.location || "Remote"}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" /> Applied on{" "}
                        {new Date(app.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => handleViewMatchScore(app.id)}
                      className="px-3.5 py-2 rounded-xl bg-indigo-50 hover:bg-indigo-100 border border-indigo-200/80 text-indigo-700 text-xs font-semibold transition flex items-center gap-1.5 shadow-sm"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      AI Match Analysis
                    </button>

                    <span
                      className={`px-3 py-1 rounded-full text-xs font-semibold capitalize ${
                        isRejected
                          ? "bg-rose-50 text-rose-700 border border-rose-200"
                          : app.status === "selected"
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          : "bg-indigo-50 text-indigo-700 border border-indigo-200"
                      }`}
                    >
                      {app.status.replace("_", " ")}
                    </span>
                  </div>
                </div>

                {/* Status Pipeline Visualizer */}
                <div className="pt-6">
                  <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-4">
                    Application Journey
                  </h4>

                  {isRejected ? (
                    <div className="flex items-center gap-2 p-3 bg-rose-50 rounded-2xl border border-rose-100 text-rose-700 text-xs font-medium">
                      <XCircle className="w-4 h-4 shrink-0" />
                      <span>Application was not selected for this position.</span>
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                      {PIPELINE_STAGES.map((stage, idx) => {
                        const isCompleted = idx <= currentStageIndex;
                        const isCurrent = idx === currentStageIndex;

                        return (
                          <div
                            key={stage.key}
                            className={`p-3 rounded-2xl border transition text-center ${
                              isCurrent
                                ? "bg-indigo-600 text-white border-indigo-600 shadow-sm"
                                : isCompleted
                                ? "bg-indigo-50/60 text-indigo-900 border-indigo-100"
                                : "bg-slate-50 text-slate-400 border-slate-200/60"
                            }`}
                          >
                            <div className="flex items-center justify-center mb-1">
                              {isCompleted ? (
                                <CheckCircle2 className={`w-4 h-4 ${isCurrent ? "text-white" : "text-indigo-600"}`} />
                              ) : (
                                <Clock className="w-4 h-4 text-slate-300" />
                              )}
                            </div>
                            <span className="text-xs font-semibold block">{stage.label}</span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* AI Match Score Modal */}
      {scoreModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl shadow-2xl max-w-xl w-full max-h-[90vh] overflow-y-auto p-6 sm:p-8 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start justify-between pb-4 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 text-white flex items-center justify-center shadow-md shadow-indigo-100">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900">Explainable AI Match Breakdown</h3>
                  <p className="text-xs text-slate-500">TF-IDF Semantic & Skill Similarity Engine</p>
                </div>
              </div>
              <button
                onClick={() => setScoreModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            {loadingScore ? (
              <div className="py-16 text-center text-slate-400 text-xs">
                Computing AI match vectors...
              </div>
            ) : selectedScore ? (
              <div className="mt-6 space-y-6">
                {/* Score Pill / Header */}
                <div className="p-4 rounded-2xl bg-gradient-to-r from-indigo-50 to-violet-50 border border-indigo-100 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-indigo-700">Overall Match Quality</span>
                    <h4 className="text-2xl font-black text-indigo-900 mt-0.5">
                      {selectedScore.overall_score}%
                    </h4>
                  </div>
                  <div className="text-right">
                    <span className="text-[11px] font-medium text-slate-500">Rating</span>
                    <p className="text-xs font-bold text-indigo-800">
                      {selectedScore.overall_score >= 80 ? "Strong Match" : selectedScore.overall_score >= 60 ? "Good Match" : "Moderate Match"}
                    </p>
                  </div>
                </div>

                {/* Multi-Factor Score Bars */}
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    Scoring Components
                  </h4>
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-600">Skills Overlap (50%)</span>
                      <span className="font-semibold text-slate-900">{selectedScore.skills_score}%</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                      <div className="h-full bg-indigo-600 rounded-full" style={{ width: `${selectedScore.skills_score}%` }} />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-600">TF-IDF Semantic Similarity (35%)</span>
                      <span className="font-semibold text-slate-900">{selectedScore.semantic_score}%</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                      <div className="h-full bg-violet-600 rounded-full" style={{ width: `${selectedScore.semantic_score}%` }} />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-600">Experience Alignment (15%)</span>
                      <span className="font-semibold text-slate-900">{selectedScore.experience_score}%</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                      <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${selectedScore.experience_score}%` }} />
                    </div>
                  </div>
                </div>

                {/* Skills Match vs Gaps */}
                <div>
                  <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                    Skill Insights
                  </h4>
                  <div className="space-y-2">
                    <div>
                      <span className="text-[11px] text-slate-500 block mb-1">Matched Required Skills:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedScore.matching_skills.length > 0 ? (
                          selectedScore.matching_skills.map((s) => (
                            <span key={s} className="px-2 py-0.5 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-medium">
                              ✓ {s}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-slate-400">None detected</span>
                        )}
                      </div>
                    </div>

                    {selectedScore.missing_skills.length > 0 && (
                      <div className="mt-2">
                        <span className="text-[11px] text-slate-500 block mb-1">Missing Target Skills:</span>
                        <div className="flex flex-wrap gap-1.5">
                          {selectedScore.missing_skills.map((s) => (
                            <span key={s} className="px-2 py-0.5 rounded-md bg-slate-100 border border-slate-200 text-slate-600 text-xs font-medium">
                              ✕ {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Strengths & Gap Analysis */}
                <div className="space-y-3 pt-2">
                  {selectedScore.strengths.length > 0 && (
                    <div className="p-3 bg-emerald-50/60 rounded-xl border border-emerald-100 text-xs text-emerald-900 space-y-1">
                      <span className="font-bold block text-emerald-800">Profile Strengths:</span>
                      {selectedScore.strengths.map((str, idx) => (
                        <p key={idx}>• {str}</p>
                      ))}
                    </div>
                  )}

                  {selectedScore.gap_analysis.length > 0 && (
                    <div className="p-3 bg-amber-50/60 rounded-xl border border-amber-100 text-xs text-amber-900 space-y-1">
                      <span className="font-bold block text-amber-800">Growth Recommendations:</span>
                      {selectedScore.gap_analysis.map((gap, idx) => (
                        <p key={idx}>• {gap}</p>
                      ))}
                    </div>
                  )}
                </div>

                {selectedScore.summary && (
                  <p className="text-xs text-slate-500 italic bg-slate-50 p-3 rounded-xl border border-slate-100">
                    "{selectedScore.summary}"
                  </p>
                )}
              </div>
            ) : (
              <div className="py-12 text-center text-slate-400 text-xs">
                Score analysis not available.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

