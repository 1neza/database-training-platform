import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type {
  AttemptHistory,
  Evaluation,
  Learner,
  LearnerProgress,
  Scenario,
  Session,
} from "./types";

const LEARNER_STORAGE_KEY = "databaselab.learnerId";

function formatRemaining(deadline: string) {
  const ms = new Date(deadline).getTime() - Date.now();
  if (ms <= 0) return "00:00";
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedSlug, setSelectedSlug] = useState<string>("");
  const [name, setName] = useState("Learner");
  const [learner, setLearner] = useState<Learner | null>(null);
  const [attempts, setAttempts] = useState<AttemptHistory[]>([]);
  const [progress, setProgress] = useState<LearnerProgress | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [hints, setHints] = useState<string[]>([]);
  const [remaining, setRemaining] = useState("--:--");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const scenario = useMemo(() => {
    if (session) return scenarios.find((item) => item.slug === session.scenario_slug);
    return scenarios.find((item) => item.slug === selectedSlug);
  }, [scenarios, selectedSlug, session]);

  async function refreshLearnerData(learnerId: string) {
    const [history, summary] = await Promise.all([
      api.learnerAttempts(learnerId),
      api.learnerProgress(learnerId),
    ]);
    setAttempts(history);
    setProgress(summary);
  }

  useEffect(() => {
    api.scenarios()
      .then((items) => {
        setScenarios(items);
        if (items.length > 0) setSelectedSlug(items[0].slug);
      })
      .catch((e) => setError(String(e)));

    const storedLearnerId = window.localStorage.getItem(LEARNER_STORAGE_KEY);
    if (storedLearnerId) {
      api.learner(storedLearnerId)
        .then(async (profile) => {
          setLearner(profile);
          setName(profile.display_name);
          await refreshLearnerData(profile.id);
        })
        .catch(() => {
          window.localStorage.removeItem(LEARNER_STORAGE_KEY);
        });
    }
  }, []);

  useEffect(() => {
    if (!session) return;
    const update = () => setRemaining(formatRemaining(session.deadline_at));
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, [session]);

  async function ensureLearner(): Promise<Learner> {
    if (learner) return learner;
    const profile = await api.createLearner(name || "Learner");
    window.localStorage.setItem(LEARNER_STORAGE_KEY, profile.id);
    setLearner(profile);
    setName(profile.display_name);
    return profile;
  }

  async function start() {
    if (!scenario) return;
    setBusy(true);
    setError("");
    try {
      const profile = await ensureLearner();
      const created = await api.startSession(profile.display_name, scenario.slug, profile.id);
      setSession(created);
      setEvaluation(null);
      setHints([]);
      await refreshLearnerData(profile.id);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function evaluate() {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      const result = await api.evaluate(session.id);
      setEvaluation(result);
      if (learner) await refreshLearnerData(learner.id);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function endLab() {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      await api.finishSession(session.id);
      setSelectedSlug(session.scenario_slug);
      setSession(null);
      setEvaluation(null);
      setHints([]);
      setRemaining("--:--");
      if (learner) await refreshLearnerData(learner.id);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function replayLab() {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      const replay = await api.replaySession(session.id);
      setSession(replay);
      setEvaluation(null);
      setHints([]);
      setRemaining(formatRemaining(replay.deadline_at));
      if (learner) await refreshLearnerData(learner.id);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function loadHints() {
    if (!scenario) return;
    const data = await api.hints(scenario.slug);
    setHints(data.hints);
  }

  function switchLearner() {
    window.localStorage.removeItem(LEARNER_STORAGE_KEY);
    setLearner(null);
    setAttempts([]);
    setProgress(null);
    setName("Learner");
  }

  if (scenarios.length === 0) {
    return <main className="shell"><p>Loading scenarios…</p></main>;
  }

  return (
    <main className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">DATABASELAB / POSTGRESQL DBA</p>
          <h1>Learn databases by operating one.</h1>
          <p className="sub">
            Diagnose incidents, change a real PostgreSQL environment, and build a measurable record of production database skills.
          </p>
        </div>
        <div className="badge">MVP 0.4</div>
      </header>

      {error && <div className="error">{error}</div>}

      {!session ? (
        <>
          {learner && progress && (
            <section className="progressPanel">
              <div className="progressHeader">
                <div>
                  <p className="eyebrow">LEARNER PROGRESS</p>
                  <h2>{learner.display_name}</h2>
                  <p className="catalogIntro">Your completed work now stays attached to this learner profile.</p>
                </div>
                <button className="secondary" onClick={switchLearner}>Use another learner</button>
              </div>

              <div className="statGrid">
                <div className="stat"><strong>{progress.total_attempts}</strong><span>Attempts</span></div>
                <div className="stat"><strong>{progress.scenarios_attempted}</strong><span>Scenarios tried</span></div>
                <div className="stat"><strong>{progress.scenarios_passed}</strong><span>Scenarios passed</span></div>
                <div className="stat">
                  <strong>{progress.average_best_score === null ? "—" : Math.round(progress.average_best_score)}</strong>
                  <span>Avg. best score</span>
                </div>
              </div>

              {attempts.length > 0 && (
                <div className="history">
                  <p className="eyebrow">RECENT ATTEMPTS</p>
                  {attempts.slice(0, 5).map((attempt) => (
                    <div className="historyRow" key={attempt.id}>
                      <div>
                        <strong>{attempt.scenario_title}</strong>
                        <span>v{attempt.scenario_version} · attempt {attempt.attempt_number} · {formatDate(attempt.started_at)}</span>
                      </div>
                      <div className="historyResult">
                        <span className={`status ${attempt.status}`}>{attempt.status}</span>
                        <strong>{attempt.score === null ? "—" : `${attempt.score}/100`}</strong>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          <section className="catalogHeader">
            <div>
              <p className="eyebrow">SCENARIO CATALOG</p>
              <h2>Choose your incident</h2>
              <p className="catalogIntro">
                Each lab launches an isolated PostgreSQL environment with a different production failure mode.
              </p>
            </div>
            <div className="scenarioCount">{scenarios.length} labs</div>
          </section>

          <section className="scenarioGrid">
            {scenarios.map((item, index) => {
              const selected = item.slug === selectedSlug;
              const scenarioProgress = progress?.scenario_progress.find((p) => p.scenario_slug === item.slug);
              return (
                <button
                  type="button"
                  key={item.slug}
                  className={`scenarioCard ${selected ? "selected" : ""}`}
                  onClick={() => setSelectedSlug(item.slug)}
                  aria-pressed={selected}
                >
                  <div className="scenarioNumber">{String(index + 1).padStart(2, "0")}</div>
                  <div>
                    <p className="eyebrow">{item.level} · v{item.version}</p>
                    <h3>{item.title}</h3>
                    <p>{item.summary}</p>
                    <div className="meta">
                      <span>{item.duration_minutes} min</span>
                      <span>{item.objectives.length} objectives</span>
                      {scenarioProgress?.best_score !== null && scenarioProgress?.best_score !== undefined && (
                        <span>Best {scenarioProgress.best_score}/100</span>
                      )}
                    </div>
                  </div>
                  <span className="selectMarker">{selected ? "Selected" : "Choose"}</span>
                </button>
              );
            })}
          </section>

          {scenario && (
            <section className="grid startPanel">
              <article className="card">
                <p className="eyebrow">SELECTED INCIDENT · v{scenario.version}</p>
                <h2>{scenario.title}</h2>
                <p>{scenario.incident}</p>

                <label>
                  Learner name
                  <input
                    value={name}
                    disabled={Boolean(learner)}
                    onChange={(e) => setName(e.target.value)}
                  />
                </label>

                <button disabled={busy} onClick={start}>
                  {busy ? "Provisioning lab…" : "Start production incident"}
                </button>
              </article>

              <article className="card muted">
                <p className="eyebrow">WHAT YOU WILL PRACTICE</p>
                <ol>{scenario.objectives.map((item) => <li key={item}>{item}</li>)}</ol>
              </article>
            </section>
          )}
        </>
      ) : scenario ? (
        <>
          <section className="incident">
            <div>
              <p className="eyebrow">LIVE INCIDENT · v{session.scenario_version} · ATTEMPT {session.attempt_number}</p>
              <h2>{scenario.title}</h2>
              <p>{scenario.incident}</p>
            </div>
            <div className="incidentControls">
              <div className="timer">
                <span>TIME LEFT</span>
                <strong>{remaining}</strong>
              </div>
              <button className="secondary" disabled={busy} onClick={endLab}>
                Finish attempt & return to catalog
              </button>
            </div>
          </section>

          <section className="grid">
            <article className="card">
              <p className="eyebrow">LAB CONNECTION</p>
              <dl className="credentials">
                <div><dt>Host</dt><dd>{session.connection.host}</dd></div>
                <div><dt>Port</dt><dd>{session.connection.port}</dd></div>
                <div><dt>Database</dt><dd>{session.connection.database}</dd></div>
                <div><dt>User</dt><dd>{session.connection.username}</dd></div>
                <div><dt>Password</dt><dd>{session.connection.password}</dd></div>
              </dl>
              <pre>{`psql -h ${session.connection.host} -p ${session.connection.port} -U ${session.connection.username} -d ${session.connection.database}`}</pre>
            </article>

            <article className="card">
              <p className="eyebrow">OBJECTIVES</p>
              <ol>{scenario.objectives.map((item) => <li key={item}>{item}</li>)}</ol>
              <div className="actions">
                <button className="secondary" onClick={loadHints}>Show hints</button>
                <button disabled={busy} onClick={evaluate}>{busy ? "Evaluating…" : "Evaluate environment"}</button>
              </div>
            </article>
          </section>

          {hints.length > 0 && (
            <section className="card section">
              <p className="eyebrow">HINTS</p>
              <ol>{hints.map((h) => <li key={h}>{h}</li>)}</ol>
            </section>
          )}

          {evaluation && (
            <section className="card section">
              <div className="resultHeader">
                <div>
                  <p className="eyebrow">ASSESSMENT · ATTEMPT {session.attempt_number}</p>
                  <h2>{evaluation.passed ? "Incident resolved" : "More work needed"}</h2>
                </div>
                <strong className="score">{evaluation.score}/100</strong>
              </div>

              <div className="checks">
                {evaluation.checks.map((check) => (
                  <div className="check" key={check.name}>
                    <span>{check.passed ? "✓" : "×"}</span>
                    <div>
                      <strong>{check.name}</strong>
                      <p>{check.detail}</p>
                    </div>
                  </div>
                ))}
              </div>

              <ul>{evaluation.feedback.map((f) => <li key={f}>{f}</li>)}</ul>

              <div className="actions">
                <button className="secondary" disabled={busy} onClick={replayLab}>
                  {busy ? "Provisioning replay…" : "Replay this incident"}
                </button>
                <button disabled={busy} onClick={endLab}>
                  Finish attempt & choose another incident
                </button>
              </div>
            </section>
          )}
        </>
      ) : (
        <div className="error">The active scenario could not be loaded.</div>
      )}
    </main>
  );
}
