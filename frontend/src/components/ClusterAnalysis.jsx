import Icon from "./Icon";
import "./ClusterAnalysis.css";

const CONFIDENCE_TONE = {
  observed: "strong",
  strongly_supported: "strong",
  likely: "medium",
  possible: "weak",
  unknown: "none",
};

const PRIORITY_TONE = { high: "high", medium: "medium", low: "low" };

const LAYER_ORDER = ["tool", "agent", "prompt", "data", "observability"];

const LAYER_LABEL = {
  tool: "Tool Layer",
  agent: "Agent Layer",
  prompt: "Prompt Layer",
  data: "Data Layer",
  observability: "Observability",
};

function humanize(value) {
  return String(value).replace(/_/g, " ");
}

function groupByLayer(remediation) {
  const groups = new Map();
  remediation.forEach((item) => {
    const layer = item.layer || "unknown";
    if (!groups.has(layer)) groups.set(layer, []);
    groups.get(layer).push(item);
  });

  return [...groups.entries()]
    .sort((a, b) => {
      const ia = LAYER_ORDER.indexOf(a[0]);
      const ib = LAYER_ORDER.indexOf(b[0]);
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
    })
    .map(([layer, items]) => ({
      layer,
      label: LAYER_LABEL[layer] || humanize(layer),
      items: [...items].sort(
        (a, b) =>
          (PRIORITY_TONE[a.priority] === "high" ? 0 : 1) - (PRIORITY_TONE[b.priority] === "high" ? 0 : 1),
      ),
    }));
}

function ConfidenceBadge({ confidence }) {
  const tone = CONFIDENCE_TONE[confidence] || "none";
  return (
    <span className={`ai-confidence is-${tone}`}>
      <span className="ai-confidence-dot" aria-hidden="true" />
      {humanize(confidence)}
    </span>
  );
}

export default function ClusterAnalysis({ analysis, loading, error, section = "all" }) {
  if (loading) {
    return (
      <div className="ai-panel is-loading" role="status" aria-live="polite">
        <span className="ai-spinner" aria-hidden="true" />
        <span>Analyzing root cause, impact and fixes…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="ai-panel is-error" role="alert">
        <span className="ai-panel-icon" aria-hidden="true">
          ⚠
        </span>
        <div>
          <p className="ai-panel-title">Couldn't load the analysis</p>
          <p className="ai-panel-text">{error}</p>
        </div>
      </div>
    );
  }

  if (!analysis) return null;

  const { root_cause: rc, impact, remediation } = analysis;
  const layers = groupByLayer(remediation);
  const showRootCause = section === "all" || section === "root-cause";
  const showRemediation = section === "all" || section === "remediation";

  return (
    <div className="ai-analysis">
      {showRootCause && (
        <section className="ai-block">
          <header className="ai-block-head">
            <h3 className="ai-block-title">
              <Icon name="likely_root_cause" size={17} className="ai-block-icon" />
              Root cause
            </h3>
            {rc.confidence && <ConfidenceBadge confidence={rc.confidence} />}
          </header>

          <p className="ai-claim">{rc.root_cause}</p>

          {rc.causal_chain?.length > 0 && (
            <ol className="ai-timeline">
              {rc.causal_chain.map((step) => (
                <li className="ai-step" key={step.stage}>
                  <span className="ai-step-marker" aria-hidden="true">
                    <Icon name={step.stage} size={15} />
                  </span>
                  <div className="ai-step-body">
                    <p className="ai-step-name">{humanize(step.stage)}</p>
                    <p className="ai-step-text">{step.description}</p>
                  </div>
                </li>
              ))}
            </ol>
          )}

          {rc.contributing_factors?.length > 0 && (
            <div className="ai-factors">
              <p className="ai-factors-label">Contributing factors</p>
              <ul className="ai-factors-list">
                {rc.contributing_factors.map((factor) => (
                  <li key={factor}>{factor}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="ai-alert">
            <span className="ai-alert-icon" aria-hidden="true">
              ⚠️
            </span>
            <div className="ai-alert-body">
              <p className="ai-alert-label">Impact</p>
              <ul className="ai-list">
                {impact.observed_impact.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>

          <div className="ai-potential">
            <p className="ai-potential-label">Potential impact if unaddressed</p>
            <ul className="ai-list">
              {impact.potential_impact.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {showRemediation && (
        <section className="ai-block">
          <header className="ai-block-head">
            <h3 className="ai-block-title">
              <Icon name="preventive_control" size={17} className="ai-block-icon" />
              Recommended fixes
            </h3>
            <span className="ai-block-count">
              {remediation.length} across {layers.length} layer{layers.length > 1 ? "s" : ""}
            </span>
          </header>

          <div className="ai-layers">
            {layers.map((group) => (
              <div className="ai-layer" key={group.layer}>
                <p className="ai-layer-head">
                  <Icon name={group.layer} size={15} className="ai-layer-icon" />
                  {group.label}
                </p>
                <ul className="ai-fixes">
                  {group.items.map((item) => (
                    <li
                      className={`ai-fix is-${PRIORITY_TONE[item.priority] || "low"}`}
                      key={`${group.layer}-${item.recommendation}`}
                    >
                      <span className="ai-fix-priority">{item.priority}</span>
                      <p className="ai-fix-text">{item.recommendation}</p>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
