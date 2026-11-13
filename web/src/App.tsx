import { useEffect, useState } from "react";
import {
  type Build,
  type CompareRow,
  type Dashboard,
  type Investigation,
  compareBuilds,
  loadBuilds,
  loadDashboard,
  loadInvestigations,
  startInvestigation,
  submitReview,
} from "./api";
import { formatRate, formatTemp } from "./format";

type Panel = "investigate" | "compare" | "review" | "reliability";

const CODES = ["SYN-CODE-THERM", "SYN-CODE-LINK", "SYN-CODE-POWER", "SYN-CODE-LAT"];

export function App() {
  const [panel, setPanel] = useState<Panel>("investigate");
  const [token, setToken] = useState("lab-ida");
  const [builds, setBuilds] = useState<Build[]>([]);
  const [buildId, setBuildId] = useState("SYN-FW-417");
  const [code, setCode] = useState("SYN-CODE-THERM");
  const [left, setLeft] = useState("SYN-FW-416");
  const [right, setRight] = useState("SYN-FW-417");
  const [rows, setRows] = useState<CompareRow[]>([]);
  const [draft, setDraft] = useState<Investigation | null>(null);
  const [queue, setQueue] = useState<Investigation[]>([]);
  const [correction, setCorrection] = useState("");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    loadBuilds(token)
      .then((body) => setBuilds(body.builds))
      .catch((reason: Error) => setError(reason.message));
  }, [token]);

  async function onStart() {
    setError("");
    try {
      const body = await startInvestigation(token, buildId, code);
      setDraft(body);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "start failed");
    }
  }

  async function onCompare() {
    setError("");
    try {
      const body = await compareBuilds(token, left, right);
      setRows(body.rows);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "compare failed");
    }
  }

  async function onLoadQueue() {
    setError("");
    try {
      const body = await loadInvestigations(token);
      setQueue(body.investigations);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "queue failed");
    }
  }

  async function onReview(item: Investigation, action: "approve" | "correct") {
    setError("");
    try {
      await submitReview(token, item.investigation_id, action, correction);
      await onLoadQueue();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "review failed");
    }
  }

  async function onDashboard() {
    setError("");
    try {
      setDashboard(await loadDashboard(token));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "dashboard failed");
    }
  }

  return (
    <div className="app">
      <header className="top">
        <div>
          <h1>Ridgebench lab workbench</h1>
          <div className="notice">DRAFT_NOT_A_PRODUCT_DISPOSITION · synthetic firmware lab</div>
        </div>
        <label>
          Fixture token
          <input
            aria-label="Fixture token"
            value={token}
            onChange={(event) => setToken(event.target.value)}
          />
        </label>
      </header>
      <div className="shell">
        <nav>
          {(["investigate", "compare", "review", "reliability"] as Panel[]).map((item) => (
            <button
              key={item}
              className={panel === item ? "active" : ""}
              onClick={() => setPanel(item)}
            >
              {item}
            </button>
          ))}
        </nav>
        <main>
          {error !== "" && <p className="error">{error}</p>}
          {panel === "investigate" && (
            <section className="card">
              <h2>Start investigation</h2>
              <div className="row">
                <label>
                  Build
                  <select
                    aria-label="Build"
                    value={buildId}
                    onChange={(event) => setBuildId(event.target.value)}
                  >
                    {builds.map((build) => (
                      <option key={build.build_id} value={build.build_id}>
                        {build.build_id}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Failure code
                  <select aria-label="Failure code" value={code} onChange={(event) => setCode(event.target.value)}>
                    {CODES.map((item) => (
                      <option key={item}>{item}</option>
                    ))}
                  </select>
                </label>
                <button className="primary" onClick={() => void onStart()}>
                  Start investigation
                </button>
              </div>
              {draft !== null && (
                <div>
                  <p>
                    {draft.classification} · {draft.status} · {draft.notice}
                  </p>
                  <p>{draft.cause === "" ? "No cause claimed." : draft.cause}</p>
                  <ol>
                    {draft.steps.map((step) => (
                      <li key={step.name}>
                        {step.name}: {step.detail}
                      </li>
                    ))}
                  </ol>
                  <p>Citations: {draft.citations.join(", ") || "none"}</p>
                </div>
              )}
            </section>
          )}
          {panel === "compare" && (
            <section className="card">
              <h2>Compare builds</h2>
              <div className="row">
                <label>
                  Left
                  <select aria-label="Left build" value={left} onChange={(event) => setLeft(event.target.value)}>
                    {builds.map((build) => (
                      <option key={build.build_id}>{build.build_id}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Right
                  <select aria-label="Right build" value={right} onChange={(event) => setRight(event.target.value)}>
                    {builds.map((build) => (
                      <option key={build.build_id}>{build.build_id}</option>
                    ))}
                  </select>
                </label>
                <button className="primary" onClick={() => void onCompare()}>
                  Compare
                </button>
              </div>
              <table>
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Left failures</th>
                    <th>Right failures</th>
                    <th>Left rate</th>
                    <th>Right rate</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.code}>
                      <td>{row.code}</td>
                      <td>{row.left_failures}</td>
                      <td>{row.right_failures}</td>
                      <td>{formatRate(row.left_rate)}</td>
                      <td>{formatRate(row.right_rate)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
          {panel === "review" && (
            <section className="card">
              <h2>Review drafts</h2>
              <p className="muted">Use lab-otto. The requester cannot approve their own draft.</p>
              <button className="primary" onClick={() => void onLoadQueue()}>
                Load drafts
              </button>
              <label>
                Correction
                <input
                  aria-label="Correction"
                  value={correction}
                  onChange={(event) => setCorrection(event.target.value)}
                />
              </label>
              <table>
                <thead>
                  <tr>
                    <th>Id</th>
                    <th>Case</th>
                    <th>Class</th>
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {queue.map((item) => (
                    <tr key={item.investigation_id}>
                      <td>{item.investigation_id}</td>
                      <td>
                        {item.build_id} {item.failure_code}
                      </td>
                      <td>{item.classification}</td>
                      <td>{item.status}</td>
                      <td>
                        <button onClick={() => void onReview(item, "approve")}>Approve</button>
                        <button onClick={() => void onReview(item, "correct")}>Correct</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
          {panel === "reliability" && (
            <section className="card">
              <h2>Reliability</h2>
              <button className="primary" onClick={() => void onDashboard()}>
                Load dashboard
              </button>
              {dashboard !== null && (
                <div>
                  <p>Data-quality failures: {dashboard.dq_failures}</p>
                  <p>Device calls: {dashboard.device_calls}</p>
                  <p>
                    Reviews {dashboard.reviews}, corrections {dashboard.corrections}, correction rate{" "}
                    {formatRate(dashboard.correction_rate)}
                  </p>
                  <p>
                    Investigate events {dashboard.usage.investigate_events}, repeated subjects{" "}
                    {dashboard.usage.repeated_subjects}
                  </p>
                  <table>
                    <thead>
                      <tr>
                        <th>Build</th>
                        <th>Pass rate</th>
                        <th>Mean temperature</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dashboard.pass_rates.map((row) => {
                        const temp = dashboard.mean_temperature_c.find(
                          (item) => item.build_id === row.build_id,
                        );
                        return (
                          <tr key={row.build_id}>
                            <td>{row.build_id}</td>
                            <td>
                              <div className="bar">
                                <span style={{ width: `${row.pass_rate * 100}%` }} />
                              </div>
                              {formatRate(row.pass_rate)}
                            </td>
                            <td>{formatTemp(temp?.mean_temperature_c ?? null)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
