export type Scenario = {
  slug: string;
  version: string;
  track_slug: string;
  title: string;
  level: string;
  skills: string[];
  prerequisites: string[];
  duration_minutes: number;
  summary: string;
  incident: string;
  objectives: string[];
};

export type Learner = {
  id: string;
  display_name: string;
  created_at: string;
};

export type Skill = {
  slug: string;
  name: string;
  description: string;
};

export type ScenarioReadiness = {
  scenario_slug: string;
  scenario_title: string;
  scenario_version: string;
  state: "ready" | "locked" | "completed";
  skills: string[];
  prerequisites: string[];
  missing_prerequisites: string[];
  recommended: boolean;
};

export type LearningPath = {
  track_slug: string;
  mastered_skills: Skill[];
  scenarios: ScenarioReadiness[];
};

export type Session = {
  id: string;
  learner_name: string;
  track_slug: string;
  scenario_slug: string;
  scenario_version: string;
  attempt_number: number;
  replay_of_session_id: string | null;
  lab_active: boolean;
  status: string;
  started_at: string;
  deadline_at: string;
  score: number | null;
  result: Evaluation | null;
  connection: {
    host: string;
    port: number;
    database: string;
    username: string;
    password: string;
    sslmode: string;
  };
};

export type AttemptHistory = {
  id: string;
  scenario_slug: string;
  scenario_title: string;
  scenario_version: string;
  attempt_number: number;
  status: string;
  score: number | null;
  started_at: string;
  deadline_at: string;
  lab_active: boolean;
  replay_of_session_id: string | null;
};

export type ScenarioProgress = {
  scenario_slug: string;
  scenario_title: string;
  attempts: number;
  passed_attempts: number;
  best_score: number | null;
  latest_score: number | null;
  latest_status: string;
  latest_attempt_at: string;
};

export type LearnerProgress = {
  learner_id: string;
  total_attempts: number;
  completed_attempts: number;
  passed_attempts: number;
  scenarios_attempted: number;
  scenarios_passed: number;
  average_best_score: number | null;
  scenario_progress: ScenarioProgress[];
};

export type Evaluation = {
  passed: boolean;
  score: number;
  checks: Array<{
    name: string;
    passed: boolean;
    detail: string;
  }>;
  feedback: string[];
};
