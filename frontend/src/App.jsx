import { useState } from "react";
import Header from "./components/Header";
import Layout from "./components/Layout";
import DashboardPage from "./components/pages/DashboardPage";
import DatasetsPage from "./components/pages/DatasetsPage";
import EvaluationPage from "./components/pages/EvaluationPage";
import FailureClustersPage from "./components/pages/FailureClustersPage";
import ReplayLabPage from "./components/pages/ReplayLabPage";
import TraceExplorerPage from "./components/pages/TraceExplorerPage";
import "./App.css";

const PAGES = {
  dashboard: {
    component: DashboardPage,
    label: "Dashboard",
    title: "Dashboard Overview",
    subtitle: "Here's what X-Ray found in your agent traces.",
  },
  "failure-clusters": {
    component: FailureClustersPage,
    label: "Failure clusters",
    title: "Failure Clusters",
    subtitle: "Cluster d’échecs",
    placeholder: true,
  },
  "trace-explorer": {
    component: TraceExplorerPage,
    label: "Trace explorer",
    title: "Trace Explorer",
    subtitle: "Traces d’agents",
    placeholder: true,
  },
  "replay-lab": {
    component: ReplayLabPage,
    label: "Replay lab",
    title: "Replay Lab",
    subtitle: "Simulation de correctifs",
    placeholder: true,
  },
  datasets: {
    component: DatasetsPage,
    label: "Datasets",
    title: "Datasets",
    subtitle: "Jeux de données",
    placeholder: true,
  },
  evaluation: {
    component: EvaluationPage,
    label: "Evaluation",
    title: "Evaluation",
    subtitle: "Métriques du système",
    placeholder: true,
  },
};

export default function App() {
  const [activePage, setActivePage] = useState("dashboard");
  const page = PAGES[activePage] ?? PAGES.dashboard;
  const PageComponent = page.component;

  return (
    <Layout activePage={activePage} onNavigate={setActivePage}>
      <div className="app">
        <Header pageLabel={page.label} title={page.title} subtitle={page.subtitle} />
        {page.placeholder ? (
          <PageComponent onBack={() => setActivePage("dashboard")} />
        ) : (
          <PageComponent />
        )}
      </div>
    </Layout>
  );
}
