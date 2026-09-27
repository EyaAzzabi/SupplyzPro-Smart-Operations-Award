import EmptyState from "../EmptyState";

export default function DatasetsPage({ onBack }) {
  return (
    <EmptyState
      icon="💾"
      title="Datasets"
      description="Gérez les jeux de données synthétiques et réels utilisés pour l’entraînement."
      onBack={onBack}
    />
  );
}
