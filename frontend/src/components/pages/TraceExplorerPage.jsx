import EmptyState from "../EmptyState";

export default function TraceExplorerPage({ onBack }) {
  return (
    <EmptyState
      icon="🔍"
      title="Trace Explorer"
      description="Explorez en détail chaque conversation d’agent et visualisez les appels d’outils en temps réel."
      onBack={onBack}
    />
  );
}
