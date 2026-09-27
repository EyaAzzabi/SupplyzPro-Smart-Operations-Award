import EmptyState from "../EmptyState";

export default function EvaluationPage({ onBack }) {
  return (
    <EmptyState
      icon="📊"
      title="Evaluation Metrics"
      description="Review the precision, recall and latency metrics of our AI model."
      onBack={onBack}
    />
  );
}
