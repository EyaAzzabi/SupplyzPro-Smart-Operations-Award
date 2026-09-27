import EmptyState from "../EmptyState";

export default function EvaluationPage({ onBack }) {
  return (
    <EmptyState
      icon="📊"
      title="Evaluation Metrics"
      description="Consultez les métriques de précision, rappel et latence de notre modèle IA."
      onBack={onBack}
    />
  );
}
