import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type { Evaluation, Scenario, Session } from "./types";

function formatRemaining(deadline: string) {
  const ms = new Date(deadline).getTime() - Date.now();
  if (ms <= 0) return "00:00";
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export default function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [name, setName] = useState("Learner");
  const [session, setSession] = useState<Session | null>(null);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [hints, setHints] = useState<string[]>([]);
  const [remaining, setRemaining] = useState("--:--");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const scenario = useMemo(
    () => scenarios.find((s) => s.slug === session?.scenario_slug) || scenarios[0],
    [scenarios, session]
  );

  useEffect(() => {
    api.scenarios().then(setScenarios).catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!session) return;
    const update = () => setRemaining(formatRemaining(session.deadline_at));
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, [session]);

  async function start() {
    if (!scenario) return;
    setBusy(true);
    setError("");
    try {
      const created = await api.startSession(name || "Learner", scenario.slug);
      setSession(created);
      setEvaluation(null);
      setHints([]);
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
      setEvaluation(await api.evaluate(session.id));
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

  if (!scenario) {
    return <main className="shell"><p>Loading scenarios…</p></main>;
  }

  return (
    <main className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">DATABASELAB / POSTGRESQL DBA</p>
          <h1>Learn databases by operating one.</h1>
          <p className="sub">
            Diagnose incidents, change a real PostgreSQL environment, and get scored against the actual system state.
          </p>
        </div>
        <div className="badge">MVP 0.1</div>
      </header>

      {error && <div className="error">{error}</div>}

      {!session ? (
        <section className="grid">
          <article className="card">
            <p className="eyebrow">SCENARIO</p>
            <h2>{scenario.title}</h2>
            <p>{scenario.summary}</p>
            <div className="meta">
              <span>{scenario.level}</span>
              <span>{scenario.duration_minutes} min</span>
            </div>

            <label>
              Learner name
              <input value={name} onChange={(e) => setName(e.target.value)} />
            </label>

            <button disabled={busy} onClick={start}>
              {busy ? "Provisioning lab…" : "Start production incident"}
            </button>
          </article>

          <article className="card muted">
            <p className="eyebrow">WHAT YOU WILL PRACTICE</p>
            <ul>
              {scenario.objectives.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </article>
        </section>
      ) : (
        <>
          <section className="incident">
            <div>
              <p className="eyebrow">LIVE INCIDENT</p>
              <h2>{scenario.title}</h2>
              <p>{scenario.incident}</p>
            </div>
            <div className="timer">
              <span>TIME LEFT</span>
              <strong>{remaining}</strong>
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
              <ol>
                {scenario.objectives.map((item) => <li key={item}>{item}</li>)}
              </ol>
              <div className="actions">
                <button className="secondary" onClick={loadHints}>Show hints</button>
                <button disabled={busy} onClick={evaluate}>
                  {busy ? "Evaluating…" : "Evaluate environment"}
                </button>
              </div>
            </article>
          </section>

          {hints.length > 0 && (
            <section className="card section">
              <p className="eyebrow">HINTS</p>
              <ol>
                {hints.map((h) => <li key={h}>{h}</li>)}
              </ol>
            </section>
          )}

          {evaluation && (
            <section className="card section">
              <div className="resultHeader">
                <div>
                  <p className="eyebrow">ASSESSMENT</p>
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

              <ul>
                {evaluation.feedback.map((f) => <li key={f}>{f}</li>)}
              </ul>
            </section>
          )}
        </>
      )}
    </main>
  );
}
