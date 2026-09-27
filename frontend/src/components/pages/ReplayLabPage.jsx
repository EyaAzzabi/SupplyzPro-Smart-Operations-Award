import EmptyState from "../EmptyState";

export default function ReplayLabPage({ onBack }) {
  return (
    <EmptyState
      icon="🧪"
      title="Replay Lab"
      description="Simulez des correctifs et rejouez des scénarios d’échec pour valider vos solutions."
      onBack={onBack}
    />
  );
}
