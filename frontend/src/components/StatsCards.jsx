import "./StatsCards.css";

function ChatIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 14a2 2 0 0 1-2 2H8l-4 3V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3.5 2.8 19a1 1 0 0 0 .87 1.5h16.66a1 1 0 0 0 .87-1.5z" />
      <path d="M12 9v4.5M12 16.8v.2" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 6.5 9.5 17 4 11.5" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3.2 5 6v5.2c0 4.2 2.9 8.1 7 9.6 4.1-1.5 7-5.4 7-9.6V6z" />
    </svg>
  );
}

function formatNumber(value) {
  return typeof value === "number" ? value.toLocaleString("en-US") : "—";
}

function computeFixRate(fixData) {
  if (!fixData) return null;
  const before = fixData.frequency_before_fix;
  const after = fixData.frequency_after_fix;
  if (typeof before !== "number" || typeof after !== "number" || before <= 0) return null;
  return Math.min(1, Math.max(0, (before - after) / before));
}

function StatCard({ label, value, hint, hintTitle, tone, icon, progress }) {
  return (
    <article className={`stats-card stats-card--${tone}`}>
      <div className="stats-card-top">
        <p className="stats-card-label">{label}</p>
        <span className="stats-card-icon" aria-hidden="true">
          {icon}
        </span>
      </div>
      <p className="stats-card-value">{value}</p>
      {progress !== undefined && progress !== null && (
        <div className="stats-card-track" role="presentation">
          <div className="stats-card-fill" style={{ width: `${Math.round(progress * 100)}%` }} />
        </div>
      )}
      {hint && (
        <p className="stats-card-hint" title={hintTitle}>
          {hint}
        </p>
      )}
    </article>
  );
}

export default function StatsCards({ summary, clusters, fixData }) {
  const fixRate = computeFixRate(fixData);
  const before = fixData?.frequency_before_fix;
  const after = fixData?.frequency_after_fix;
  const occurrencesHint =
    typeof before === "number" && typeof after === "number" ? `${before} → ${after} occurrences` : null;

  const silentCluster = (clusters ?? []).find((c) => c.failure_type === "silent_tool_failure");
  const silentCount = silentCluster ? silentCluster.frequency : null;
  const totalTraces = summary?.total_conversations;
  const silentShare =
    typeof silentCount === "number" && typeof totalTraces === "number" && totalTraces > 0
      ? (silentCount / totalTraces) * 100
      : null;

  return (
    <div className="stats-grid">
      <StatCard
        label="Total Conversations"
        value={formatNumber(summary?.total_conversations)}
        hint="SupplyzPro agent conversations analysed"
        tone="neutral"
        icon={<ChatIcon />}
      />
      <StatCard
        label="Detected Failures"
        value={formatNumber(summary?.total_failures)}
        hint={`Across ${formatNumber(summary?.cluster_count)} root-cause clusters`}
        tone="danger"
        icon={<AlertIcon />}
      />
      <StatCard
        label="Silent failures"
        value={formatNumber(silentCount)}
        hint={silentShare === null ? "No silent-failure cluster detected" : `${silentShare.toFixed(1)}% of all traces`}
        tone="warning"
        icon={<ShieldIcon />}
      />
      <StatCard
        label="Fix Rate"
        value={fixRate === null ? "—" : `${Math.round(fixRate * 100)}%`}
        hint={occurrencesHint}
        hintTitle={fixData?.top_cluster_label}
        tone="success"
        icon={<CheckIcon />}
        progress={fixRate}
      />
    </div>
  );
}
