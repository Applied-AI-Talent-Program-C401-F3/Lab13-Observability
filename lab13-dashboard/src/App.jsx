import { useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

function formatNumber(value, digits = 0) {
  return Number(value || 0).toFixed(digits);
}

function MetricPill({ label, value, tone = "default" }) {
  return (
    <div className={`metric-pill metric-pill--${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Sparkline({ data, dataKey, color, suffix = "", threshold, maxOverride }) {
  const width = 360;
  const height = 120;
  const padding = 16;
  const values = data.map((item) => Number(item[dataKey] || 0));
  const maxValue = Math.max(maxOverride || 0, ...values, threshold || 0, 1);
  const step = values.length > 1 ? (width - padding * 2) / (values.length - 1) : width / 2;
  const points = values
    .map((value, index) => {
      const x = padding + index * step;
      const y = height - padding - (value / maxValue) * (height - padding * 2);
      return `${x},${y}`;
    })
    .join(" ");
  const area = values
    .map((value, index) => {
      const x = padding + index * step;
      const y = height - padding - (value / maxValue) * (height - padding * 2);
      return `${x},${y}`;
    })
    .join(" ");
  const thresholdY = threshold != null
    ? height - padding - (threshold / maxValue) * (height - padding * 2)
    : null;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="sparkline" preserveAspectRatio="none">
      <defs>
        <linearGradient id={`fill-${dataKey}`} x1="0%" x2="0%" y1="0%" y2="100%">
          <stop offset="0%" stopColor={color} stopOpacity="0.35" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <path
        d={`M ${padding} ${height - padding} L ${area} L ${width - padding} ${height - padding} Z`}
        fill={`url(#fill-${dataKey})`}
      />
      {thresholdY != null ? (
        <g>
          <line
            x1={padding}
            x2={width - padding}
            y1={thresholdY}
            y2={thresholdY}
            className="threshold-line"
          />
          <text x={width - padding} y={Math.max(12, thresholdY - 6)} className="threshold-text">
            SLO {threshold}{suffix}
          </text>
        </g>
      ) : null}
      <polyline fill="none" stroke={color} strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" points={points} />
    </svg>
  );
}

function Panel({ title, subtitle, children }) {
  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

export default function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    let stream;

    async function loadDashboard() {
      try {
        const response = await fetch(`${API_BASE}/dashboard-data?window_minutes=60`);
        if (!response.ok) {
          throw new Error(`Dashboard API returned ${response.status}`);
        }
        const payload = await response.json();
        if (!cancelled) {
          setData(payload);
          setError("");
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      }
    }

    loadDashboard();

    try {
      stream = new EventSource(`${API_BASE}/dashboard-stream?window_minutes=60`);
      stream.onmessage = (event) => {
        if (cancelled) {
          return;
        }
        try {
          const payload = JSON.parse(event.data);
          setData(payload);
          setError("");
          setLoading(false);
        } catch (parseError) {
          setError(parseError.message);
        }
      };
      stream.onerror = () => {
        if (!cancelled) {
          setError("Realtime stream disconnected. Showing last successful snapshot.");
        }
      };
    } catch (streamError) {
      if (!cancelled) {
        setError(streamError.message);
      }
    }

    return () => {
      cancelled = true;
      if (stream) {
        stream.close();
      }
    };
  }, []);

  if (loading) {
    return <main className="shell"><div className="empty-state">Loading dashboard data...</div></main>;
  }

  if (error || !data) {
    return (
      <main className="shell">
        <div className="empty-state">
          <h2>Dashboard unavailable</h2>
          <p>{error || "No payload returned from the API."}</p>
          <code>Start FastAPI on http://127.0.0.1:8000 before opening this dashboard.</code>
        </div>
      </main>
    );
  }

  const overview = data.overview;
  const latencySlo = Number(data.slo?.latency_p95_ms?.objective || 3000);
  const qualitySlo = Number(data.slo?.quality_score_avg?.objective || 0.75);
  const errorSlo = Number(data.slo?.error_rate_pct?.objective || 2);

  return (
    <main className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Lab 13 Observability</p>
          <h1>AI Agent Dashboard + Evidence Console</h1>
          <p className="hero__copy">
            Six core monitoring panels, live evidence pointers, and incident context for your FastAPI
            observability lab. Default time range is the last {data.window_minutes} minutes with live updates every second.
          </p>
        </div>
        <div className="hero__meta">
          <MetricPill label="Total Requests" value={overview.total_requests} tone="blue" />
          <MetricPill label="QPS" value={formatNumber(overview.qps, 4)} tone="amber" />
          <MetricPill label="Error Rate" value={`${formatNumber(overview.error_rate_pct, 2)}%`} tone="rose" />
          <MetricPill label="Last Refresh" value={new Date(data.generated_at).toLocaleTimeString()} tone="green" />
        </div>
      </header>

      <section className="grid">
        <Panel title="Latency P50 / P95 / P99" subtitle="Milliseconds over the last hour with the P95 SLO line">
          <div className="stat-row">
            <MetricPill label="P50" value={`${formatNumber(overview.latency_p50)} ms`} />
            <MetricPill label="P95" value={`${formatNumber(overview.latency_p95)} ms`} tone={overview.latency_p95 > latencySlo ? "rose" : "green"} />
            <MetricPill label="P99" value={`${formatNumber(overview.latency_p99)} ms`} />
          </div>
          <Sparkline data={data.timeseries} dataKey="requests" color="#5fa8ff" threshold={null} />
          <div className="panel__note">SLO target: P95 under {latencySlo} ms. Use this panel before and after `rag_slow`.</div>
        </Panel>

        <Panel title="Traffic" subtitle="Request count and average QPS across the active window">
          <div className="stat-row">
            <MetricPill label="Requests" value={overview.successful_requests} tone="blue" />
            <MetricPill label="QPS" value={formatNumber(overview.qps, 4)} tone="amber" />
          </div>
          <Sparkline data={data.timeseries} dataKey="requests" color="#2dd4bf" />
          <div className="panel__note">Use `python scripts/load_test.py --concurrency 5` to make this panel move.</div>
        </Panel>

        <Panel title="Error Rate + Breakdown" subtitle="Symptoms panel for failures and request_failed events">
          <div className="stat-row">
            <MetricPill label="Failed" value={overview.failed_requests} tone={overview.failed_requests ? "rose" : "green"} />
            <MetricPill label="Error Rate" value={`${formatNumber(overview.error_rate_pct, 2)}%`} tone={overview.error_rate_pct > errorSlo ? "rose" : "green"} />
          </div>
          <Sparkline data={data.timeseries} dataKey="errors" color="#fb7185" threshold={errorSlo} suffix="%" maxOverride={Math.max(errorSlo, 5)} />
          <div className="breakdown-list">
            {Object.keys(data.error_breakdown).length ? Object.entries(data.error_breakdown).map(([name, count]) => (
              <div className="breakdown-item" key={name}>
                <span>{name}</span>
                <strong>{count}</strong>
              </div>
            )) : <div className="breakdown-item"><span>No errors recorded in this window</span><strong>0</strong></div>}
          </div>
        </Panel>

        <Panel title="Cost Over Time" subtitle="USD burn in the active window, ready for cost_spike demos">
          <div className="stat-row">
            <MetricPill label="Total Cost" value={`$${formatNumber(overview.total_cost_usd, 4)}`} tone="amber" />
            <MetricPill label="Avg / Response" value={`$${formatNumber(overview.avg_cost_usd, 4)}`} />
          </div>
          <Sparkline data={data.timeseries} dataKey="cost_usd" color="#f59e0b" />
          <div className="panel__note">Trigger `cost_spike` to show a higher token and cost profile.</div>
        </Panel>

        <Panel title="Tokens In / Out" subtitle="Prompt and completion token volume from response logs">
          <div className="stat-row">
            <MetricPill label="Input Tokens" value={overview.tokens_in_total} tone="blue" />
            <MetricPill label="Output Tokens" value={overview.tokens_out_total} tone="green" />
          </div>
          <div className="token-bars">
            {data.timeseries.map((point) => {
              const total = Math.max(point.tokens_in + point.tokens_out, 1);
              const inWidth = `${(point.tokens_in / total) * 100}%`;
              const outWidth = `${(point.tokens_out / total) * 100}%`;
              return (
                <div className="token-row" key={point.time}>
                  <span>{point.time}</span>
                  <div className="token-track">
                    <div className="token-track__in" style={{ width: inWidth }} />
                    <div className="token-track__out" style={{ width: outWidth }} />
                  </div>
                  <strong>{point.tokens_in + point.tokens_out}</strong>
                </div>
              );
            })}
          </div>
        </Panel>

        <Panel title="Quality Proxy" subtitle="Heuristic quality score with visible SLO threshold">
          <div className="stat-row">
            <MetricPill label="Quality Avg" value={formatNumber(overview.quality_avg, 2)} tone={overview.quality_avg < qualitySlo ? "rose" : "green"} />
            <MetricPill label="Objective" value={formatNumber(qualitySlo, 2)} />
          </div>
          <Sparkline data={data.timeseries} dataKey="quality_avg" color="#34d399" threshold={qualitySlo} />
          <div className="panel__note">This uses the lab heuristic from the agent so you can still demonstrate quality without thumbs feedback.</div>
        </Panel>
      </section>

      <section className="evidence-layout">
        <section className="panel panel--wide">
          <div className="panel__header">
            <div>
              <h3>Evidence Checklist</h3>
              <p>What Member E should capture for the report and demo.</p>
            </div>
          </div>
          <div className="checklist">
            {data.evidence_checklist.map((item) => (
              <label key={item} className="checklist__item">
                <input type="checkbox" />
                <span>{item}</span>
              </label>
            ))}
          </div>
          <div className="runbook-grid">
            <div>
              <h4>Alert Rules</h4>
              {data.alert_rules.map((rule) => (
                <article key={rule.name} className="rule-card">
                  <strong>{rule.name}</strong>
                  <p>{rule.condition}</p>
                  <small>{rule.severity} • {rule.owner} • {rule.runbook}</small>
                </article>
              ))}
            </div>
            <div>
              <h4>Incident Prompts</h4>
              {Object.entries(data.incidents).map(([name, description]) => (
                <article key={name} className="rule-card">
                  <strong>{name}</strong>
                  <p>{description}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="panel">
          <div className="panel__header">
            <div>
              <h3>Recent Logs</h3>
              <p>Use these for correlation ID and PII evidence screenshots.</p>
            </div>
          </div>
          <div className="log-list">
            {data.recent_logs.map((log) => (
              <article className="log-item" key={`${log.ts}-${log.correlation_id}-${log.event}`}>
                <div className="log-item__meta">
                  <span>{log.event}</span>
                  <strong>{log.correlation_id || "n/a"}</strong>
                </div>
                <p>{log.payload?.message_preview || log.payload?.answer_preview || "-"}</p>
              </article>
            ))}
          </div>
          <div className="pii-box">
            <h4>PII Redaction Samples</h4>
            {data.pii_samples.length ? data.pii_samples.map((sample) => (
              <code key={`${sample.ts}-${sample.correlation_id}`}>{sample.preview}</code>
            )) : <p>No redaction sample in the current window yet.</p>}
          </div>
        </section>
      </section>
    </main>
  );
}
