import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import "./Charts.css";

const SEVERITY_COLOR = { 3: "#ff3333", 2: "#f59e0b", 1: "#00e676" };

function prettify(failureType) {
  return String(failureType ?? "")
    .split("_")
    .filter(Boolean)
    .map((word, i) => (i === 0 ? word.charAt(0).toUpperCase() + word.slice(1) : word))
    .join(" ");
}

function DonutTooltip({ active, payload, total }) {
  if (!active || !payload || payload.length === 0) return null;
  const entry = payload[0];
  const raw = entry.payload?.value ?? entry.value;
  const share = total ? Math.round((raw / total) * 100) : 0;

  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-row">
        <span className="chart-tooltip-dot" style={{ background: entry.color }} />
        <span className="chart-tooltip-name">{entry.payload?.name ?? entry.name}</span>
        <strong>{raw}</strong>
      </p>
      <p className="chart-tooltip-share">{share}% of all failures</p>
    </div>
  );
}

/** Real data: one slice per detected root-cause cluster, from the actual
 * X-Ray pipeline output -- not a mock. `clusters` is the same array the
 * rest of the dashboard renders (useOverview()). */
export default function FailureFamiliesChart({ clusters }) {
  const hasData = Array.isArray(clusters) && clusters.length > 0;
  const data = hasData
    ? clusters.map((c) => ({
        name: prettify(c.failure_type),
        value: c.frequency,
        color: SEVERITY_COLOR[c.severity] || "#8892b0",
      }))
    : [];
  const total = data.reduce((sum, entry) => sum + entry.value, 0);

  return (
    <article className="chart-card">
      <header className="chart-head">
        <div className="chart-headings">
          <h3 className="chart-title">Failure families</h3>
          <p className="chart-subtitle">Share of failures by root-cause family</p>
        </div>
      </header>

      {!hasData ? (
        <div className="chart-body chart-body--empty">No detected failures yet.</div>
      ) : (
        <div className="chart-body chart-body--donut">
          <div className="donut-wrap">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={data}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={56}
                  outerRadius={84}
                  paddingAngle={2}
                  stroke="none"
                  startAngle={90}
                  endAngle={-270}
                >
                  {data.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip content={<DonutTooltip total={total} />} />
              </PieChart>
            </ResponsiveContainer>

            <div className="donut-center">
              <span className="donut-center-value">{total}</span>
              <span className="donut-center-label">failures</span>
            </div>
          </div>

          <ul className="donut-legend">
            {data.map((entry) => (
              <li key={entry.name} className="donut-legend-item">
                <span className="donut-legend-dot" style={{ background: entry.color }} />
                <span className="donut-legend-name">{entry.name}</span>
                <span className="donut-legend-pct">
                  {total ? Math.round((entry.value / total) * 100) : 0}%
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}
