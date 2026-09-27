import { useState } from "react";
import Header from "./components/Header";
import Layout from "./components/Layout";
import DashboardPage from "./components/pages/DashboardPage";
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
    subtitle: "Analyze root causes, view evidence, and explore remediations for each cluster.",
  },
  "trace-explorer": {
    component: TraceExplorerPage,
    label: "Trace explorer",
    title: "Trace Explorer",
    subtitle: "Read every agent conversation turn by turn, with the failing tool calls highlighted.",
  },
  "replay-lab": {
    component: ReplayLabPage,
    label: "Replay lab",
    title: "Replay Lab",
    subtitle: "Test mitigations and verify fixes before deploying to production.",
  },
  evaluation: {
    component: EvaluationPage,
    label: "Evaluation",
    title: "Evaluation",
    subtitle: "Precision, recall, and real-world validation results for the detector.",
  },
};

export default function App() {
  const [activePage, setActivePage] = useState("dashboard");
  const [selectedClusterId, setSelectedClusterId] = useState(null);
  const page = PAGES[activePage] ?? PAGES.dashboard;
  const PageComponent = page.component;

  const openCluster = (clusterId) => {
    setSelectedClusterId(clusterId);
    setActivePage("failure-clusters");
  };

  const pageProps =
    activePage === "dashboard"
      ? { onSelectCluster: openCluster }
      : activePage === "failure-clusters"
        ? { selectedId: selectedClusterId, onSelect: setSelectedClusterId }
        : {};

  return (
    <Layout activePage={activePage} onNavigate={setActivePage}>
      <div className="app">
        <Header pageLabel={page.label} title={page.title} subtitle={page.subtitle} />
        <PageComponent {...pageProps} />
      </div>
    </Layout>
  );
}
