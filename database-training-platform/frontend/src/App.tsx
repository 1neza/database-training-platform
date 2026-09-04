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
  const [selectedSlug, setSelectedSlug] = useState<string>("");
  const [name, setName] = useState("Learner");
  const [session, setSession] = useState<Session | null>(null);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [hints, setHints] = useState<string[]>([]);
  const [remaining, setRemaining] = useState("--:--");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const scenario = useMemo(() => {
    if (session) {
      return scenarios.find((item) => item.slug === session.scenario_slug);
    }
    return scenarios.find((item) => item.slug === selectedSlug);
  }, [scenarios, selectedSlug, session]);

  useEffect(() => {
    api.scenarios()
      .then((items) => {
        setScenarios(items);
        if (items.length > 0) setSelectedSlug(items[0].slug);
      })
      .catch((e) => setError(String(e)));
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

  async function endLab() {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      await api.deleteSession(session.id);
      setSelectedSlug(session.scenario_slug);
      setSession(null);
      setEvaluation(null);
      setHints([]);
      setRemaining("--:--");
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
            Diagnose incidents, change a real PostgreSQL environment, and get scored against the actual system state.
          </p>
        </div>
        <div className="badge">MVP 0.2</div>
      </header>

      {error && <div className="error">{error}</div>}

      {!session ? (
        <>
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
              return (
                <button
                  type="button"
                  key={item.slug}
                  className={`scenarioCard ${selected ? "selected" : ""}`}
                  onClick={() => setSelectedSlug(item.slug)}
                  aria-pressed={selected}
                >
                  <div className="scenarioNumber">0{index + 1}</div>
                  <div>
                    <p className="eyebrow">{item.level}</p>
                    <h3>{item.title}</h3>
                    <p>{item.summary}</p>
                    <div className="meta">
                      <span>{item.duration_minutes} min</span>
                      <span>{item.objectives.length} objectives</span>
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
                <p className="eyebrow">SELECTED INCIDENT</p>
                <h2>{scenario.title}</h2>
                <p>{scenario.incident}</p>

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
                <ol>
                  {scenario.objectives.map((item) => <li key={item}>{item}</li>)}
                </ol>
              </article>
            </section>
          )}
        </>
      ) : scenario ? (
        <>
          <section className="incident">
            <div>
              <p className="eyebrow">LIVE INCIDENT</p>
              <h2>{scenario.title}</h2>
              <p>{scenario.incident}</p>
            </div>
            <div className="incidentControls">
              <div className="timer">
                <span>TIME LEFT</span>
                <strong>{remaining}</strong>
              </div>
              <button className="secondary" disabled={busy} onClick={endLab}>
                End lab & return to catalog
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

              {evaluation.passed && (
                <button disabled={busy} onClick={endLab}>
                  Finish lab & choose another incident
                </button>
              )}
            </section>
          )}
        </>
      ) : (
        <div className="error">The active scenario could not be loaded.</div>
      )}
    </main>
  );
}
