import EmptyState from "../EmptyState";

export default function FailureClustersPage({ onBack }) {
  return (
    <EmptyState
      icon="🕸️"
      title="Detailed Clusters"
      description="Vue détaillée et filtrable de tous les clusters d’échecs détectés."
      onBack={onBack}
    />
  );
}
