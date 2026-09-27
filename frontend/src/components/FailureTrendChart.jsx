import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./Charts.css";

const SEVERITY_COLOR = { 3: "#ff3333", 2: "#f59e0b", 1: "#00e676" };
const SEVERITY_LABEL = { 3: "High", 2: "Medium", 1: "Low" };

function shortLabel(label) {
  const withoutParens = String(label ?? "").replace(/\s*\(.*\)\s*$/, "");
  return withoutParens.length > 22 ? `${withoutParens.slice(0, 21)}…` : withoutParens;
}

function TrendTooltip({ active, payload }) {
  if (!active || !payload || payload.length === 0) return null;
  const entry = payload[0].payload;

  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-label">{entry.fullLabel}</p>
      <p className="chart-tooltip-row">
        <span className="chart-tooltip-dot" style={{ background: entry.color }} />
        <span className="chart-tooltip-name">Occurrences</span>
        <strong>{entry.frequency}</strong>
      </p>
      <p className="chart-tooltip-share">
        {SEVERITY_LABEL[entry.severity]} severity · priority score {entry.priority_score}
      </p>
    </div>
  );
}

/** Real data: every detected root-cause cluster, ranked by priority score
 * (Frequency x Severity x Blast Radius) -- the actual output of
 * ai/prioritize.py, not a fabricated time series. There's no real daily
 * timestamp in the dataset to plot an honest trend, so this shows what we
 * actually have: which failure is worst, and by how much. */
export default function FailureTrendChart({ clusters }) {
  const hasData = Array.isArray(clusters) && clusters.length > 0;
  const data = hasData
    ? [...clusters]
        .sort((a, b) => b.priority_score - a.priority_score)
        .map((c) => ({
          label: shortLabel(c.label),
          fullLabel: c.label,
          frequency: c.frequency,
          severity: c.severity,
          priority_score: c.priority_score,
          color: SEVERITY_COLOR[c.severity] || "#8892b0",
        }))
    : [];

  return (
    <article className="chart-card">
      <header className="chart-head">
        <div className="chart-headings">
          <h3 className="chart-title">Failures by cluster</h3>
          <p className="chart-subtitle">Ranked by Priority Score = Frequency × Severity × Blast Radius</p>
        </div>
        <div className="chart-legend">
          {[3, 2, 1].map((sev) => (
            <span className="chart-legend-item" key={sev}>
              <i className="chart-dot" style={{ background: SEVERITY_COLOR[sev] }} />
              {SEVERITY_LABEL[sev]}
            </span>
          ))}
        </div>
      </header>

      {!hasData ? (
        <div className="chart-body chart-body--empty">No detected failures yet.</div>
      ) : (
        <div className="chart-body">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -20 }}>
              <CartesianGrid stroke="#eef2f7" vertical={false} />
              <XAxis
                dataKey="label"
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 10, fill: "#94a3b8" }}
                interval={0}
                angle={-20}
                textAnchor="end"
                height={50}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 11, fill: "#94a3b8" }}
                width={32}
                allowDecimals={false}
              />
              <Tooltip content={<TrendTooltip />} cursor={{ fill: "rgba(0, 210, 255, 0.08)" }} />
              <Bar dataKey="frequency" name="Occurrences" radius={[4, 4, 0, 0]}>
                {data.map((entry) => (
                  <Cell key={entry.label} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </article>
  );
}
