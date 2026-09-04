import type {
  AttemptHistory,
  Evaluation,
  Learner,
  LearnerProgress,
  LearningPath,
  Scenario,
  Session,
} from "./types";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }

  return response.json();
}

export const api = {
  scenarios: () => request<Scenario[]>("/scenarios?track=postgresql-dba"),

  createLearner: (displayName: string) =>
    request<Learner>("/learners", {
      method: "POST",
      body: JSON.stringify({ display_name: displayName }),
    }),

  learner: (learnerId: string) => request<Learner>(`/learners/${learnerId}`),

  learnerAttempts: (learnerId: string) =>
    request<AttemptHistory[]>(`/learners/${learnerId}/attempts`),

  learnerProgress: (learnerId: string) =>
    request<LearnerProgress>(`/learners/${learnerId}/progress`),

  learnerLearningPath: (learnerId: string) =>
    request<LearningPath>(`/learners/${learnerId}/learning-path?track=postgresql-dba`),

  startSession: (learnerName: string, scenarioSlug: string, learnerId?: string) =>
    request<Session>("/sessions", {
      method: "POST",
      body: JSON.stringify({
        learner_name: learnerName,
        scenario_slug: scenarioSlug,
        learner_id: learnerId || null,
      }),
    }),

  evaluate: (sessionId: string) =>
    request<Evaluation>(`/sessions/${sessionId}/evaluate`, {
      method: "POST",
    }),

  finishSession: (sessionId: string) =>
    request<Session>(`/sessions/${sessionId}/finish`, {
      method: "POST",
    }),

  replaySession: (sessionId: string) =>
    request<Session>(`/sessions/${sessionId}/replay`, {
      method: "POST",
    }),

  deleteSession: (sessionId: string) =>
    request<{ deleted: boolean }>(`/sessions/${sessionId}`, {
      method: "DELETE",
    }),

  hints: (scenarioSlug: string) =>
    request<{ hints: string[] }>(`/scenarios/${scenarioSlug}/hints`),
};
