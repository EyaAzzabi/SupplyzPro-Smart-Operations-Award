import "./SkeletonLoader.css";

function Status({ label, className, children }) {
  return (
    <div className={className} role="status" aria-busy="true">
      <span className="sr-only">{label}</span>
      {children}
    </div>
  );
}

function Bar({ className = "", style }) {
  return <span className={`skeleton ${className}`.trim()} style={style} />;
}

/** Grey block with a moving highlight. Base building block of every variant. */
export function SkeletonBlock({ width, height, radius = 8 }) {
  return <Bar className="skeleton-block" style={{ width, height, borderRadius: radius }} />;
}

/** Stacked lines of text, last one shortened like a real paragraph. */
export function SkeletonText({ lines = 3, label = "Loading…", className = "" }) {
  return (
    <Status label={label} className={`skeleton-text ${className}`.trim()}>
      {Array.from({ length: lines }, (_, index) => (
        <Bar
          key={index}
          className="skeleton-line"
          style={{ width: index === lines - 1 ? "58%" : "100%" }}
        />
      ))}
    </Status>
  );
}

/** Placeholder shaped like a stats card, so the grid does not jump on load. */
export function SkeletonCard({ height = 118, label = "Loading…" }) {
  return (
    <Status label={label} className="skeleton-card">
      <Bar className="skeleton-block" style={{ height, borderRadius: 12 }} />
    </Status>
  );
}

/**
 * Placeholder shaped like the cluster table: a caption row plus `rows` cards.
 * `columnWidths` mirrors the real column rhythm so the swap is seamless.
 */
export function SkeletonTable({
  rows = 5,
  columnWidths = ["24px", "48%", "56px", "48px"],
  label = "Loading…",
  className = "",
}) {
  return (
    <Status label={label} className={`skeleton-table ${className}`.trim()}>
      <div className="skeleton-table-head" aria-hidden="true">
        {columnWidths.map((width, index) => (
          <Bar key={index} className="skeleton-bar" style={{ width }} />
        ))}
      </div>

      {Array.from({ length: rows }, (_, rowIndex) => (
        <div className="skeleton-table-row" key={rowIndex} aria-hidden="true">
          {columnWidths.map((width, columnIndex) => (
            <Bar
              key={columnIndex}
              className={columnIndex === 0 ? "skeleton-bar skeleton-rank" : "skeleton-bar"}
              style={{ width }}
            />
          ))}
        </div>
      ))}
    </Status>
  );
}
