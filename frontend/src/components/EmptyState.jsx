import "./EmptyState.css";

function ArrowLeftIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="15"
      height="15"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M19 12H5M11 18l-6-6 6-6" />
    </svg>
  );
}

export default function EmptyState({ icon, title, description, onBack }) {
  return (
    <section className="empty-state">
      <div className="empty-state-inner">
        <span className="empty-state-icon" aria-hidden="true">
          {icon}
        </span>
        <h2 className="empty-state-title">{title}</h2>
        <p className="empty-state-description">{description}</p>
        <button type="button" className="empty-state-back" onClick={onBack}>
          <ArrowLeftIcon />
          Back to Dashboard
        </button>
      </div>
    </section>
  );
}
