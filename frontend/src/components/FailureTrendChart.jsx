import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./Charts.css";

const MOCK_TREND = [
  { date: "Sep 21", failures: 35, total: 40 },
  { date: "Sep 22", failures: 45, total: 50 },
  { date: "Sep 23", failures: 55, total: 60 },
  { date: "Sep 24", failures: 50, total: 65 },
  { date: "Sep 25", failures: 65, total: 70 },
  { date: "Sep 26", failures: 70, total: 75 },
  { date: "Today", failures: 85, total: 80 },
];

function TrendTooltip({ active, payload, label }) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-label">{label}</p>
      {payload.map((entry) => (
        <p key={entry.dataKey} className="chart-tooltip-row">
          <span className="chart-tooltip-dot" style={{ background: entry.color }} />
          <span className="chart-tooltip-name">{entry.name}</span>
          <strong>{entry.value}</strong>
        </p>
      ))}
    </div>
  );
}

export default function FailureTrendChart({ data = MOCK_TREND }) {
  return (
    <article className="chart-card">
      <header className="chart-head">
        <div className="chart-headings">
          <h3 className="chart-title">Failure trend</h3>
          <p className="chart-subtitle">Failed traces vs. all traces</p>
        </div>
        <div className="chart-legend">
          <span className="chart-legend-item">
            <i className="chart-dot chart-dot--failed" />
            Failed traces
          </span>
          <span className="chart-legend-item">
            <i className="chart-dot chart-dot--all" />
            All traces
          </span>
        </div>
      </header>

      <div className="chart-body">
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -20 }}>
            <CartesianGrid stroke="#eef2f7" vertical={false} />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              dy={6}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              width={48}
            />
            <Tooltip content={<TrendTooltip />} cursor={{ stroke: "#00d2ff", strokeWidth: 1.5 }} />
            <Line
              type="monotone"
              dataKey="total"
              name="All traces"
              stroke="#8892b0"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: "#cbd5e1", stroke: "#ffffff", strokeWidth: 2 }}
            />
            <Line
              type="monotone"
              dataKey="failures"
              name="Failed traces"
              stroke="#007bff"
              strokeWidth={2.5}
              dot={{ r: 3, fill: "#007bff", strokeWidth: 0 }}
              activeDot={{ r: 5, fill: "#007bff", stroke: "#ffffff", strokeWidth: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}
