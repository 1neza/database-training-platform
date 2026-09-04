export type Scenario = {
  slug: string;
  version: string;
  track_slug: string;
  title: string;
  level: string;
  duration_minutes: number;
  summary: string;
  incident: string;
  objectives: string[];
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
