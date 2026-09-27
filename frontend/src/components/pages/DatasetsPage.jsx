import EmptyState from "../EmptyState";

export default function DatasetsPage({ onBack }) {
  return (
    <EmptyState
      icon="💾"
      title="Datasets"
      description="Manage the synthetic and real datasets used for training and evaluation."
      onBack={onBack}
    />
  );
}
