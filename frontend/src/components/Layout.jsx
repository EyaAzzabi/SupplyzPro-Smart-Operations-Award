import { useEffect, useState } from "react";
import "./Layout.css";

function GridIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8">
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  );
}

function ClusterIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <circle cx="6" cy="6" r="2.4" />
      <circle cx="18" cy="6" r="2.4" />
      <circle cx="12" cy="18" r="2.4" />
      <path d="M8.2 7.6 10.6 15.6M15.8 7.6 13.4 15.6M8.4 6h7.2" />
    </svg>
  );
}

function ChartIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <path d="M5 19v-6M12 19V7M19 19v-9" />
      <path d="M3 21h18" />
    </svg>
  );
}

function FlaskIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.5 3v5.3L4.9 16a2.4 2.4 0 0 0 2 3.6h10.2a2.4 2.4 0 0 0 2-3.6l-4.6-7.7V3" />
      <path d="M8 3h8M7.6 14h8.8" />
    </svg>
  );
}

function DatabaseIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8">
      <ellipse cx="12" cy="6" rx="7" ry="3" />
      <path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6" />
      <path d="M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6" />
    </svg>
  );
}

function TrendIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 17.5 8.8 12l3.4 3.4L21 6.5" />
      <path d="M15.2 6.5H21v5.8" />
    </svg>
  );
}

const NAV_GROUPS = [
  {
    heading: "Analysis",
    items: [
      { page: "dashboard", label: "Dashboard", icon: GridIcon },
      { page: "failure-clusters", label: "Failure clusters", icon: ClusterIcon },
      { page: "trace-explorer", label: "Trace explorer", icon: ChartIcon },
      { page: "replay-lab", label: "Replay lab", icon: FlaskIcon },
    ],
  },
  {
    heading: "System",
    items: [
      { page: "datasets", label: "Datasets", icon: DatabaseIcon },
      { page: "evaluation", label: "Evaluation", icon: TrendIcon },
    ],
  },
];

export default function Layout({ children, activePage = "dashboard", onNavigate = () => {} }) {
  const [navOpen, setNavOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    if (!navOpen) return undefined;
    const onKeyDown = (event) => {
      if (event.key === "Escape") setNavOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [navOpen]);

  useEffect(() => {
    if (!navOpen) return undefined;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [navOpen]);

  return (
    <div className={`layout${navOpen ? " layout--nav-open" : ""}${sidebarCollapsed ? " layout--sidebar-collapsed" : ""}`}>
      <header className="layout-topbar">
        <span className="layout-topbar-brand">X-Ray</span>
        <button
          type="button"
          className="layout-burger"
          onClick={() => setNavOpen((open) => !open)}
          aria-label={navOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={navOpen}
          aria-controls="layout-sidebar"
        >
          <span className="layout-burger-bar" />
          <span className="layout-burger-bar" />
          <span className="layout-burger-bar" />
        </button>
      </header>

      <button
        type="button"
        className="layout-backdrop"
        onClick={() => setNavOpen(false)}
        tabIndex={-1}
        aria-hidden="true"
      />

      <button
        type="button"
        className="layout-sidebar-toggle"
        onClick={() => setSidebarCollapsed((collapsed) => !collapsed)}
        aria-label={sidebarCollapsed ? "Show sidebar" : "Hide sidebar"}
        title={sidebarCollapsed ? "Show sidebar" : "Hide sidebar"}
      >
        {sidebarCollapsed ? "▶" : ""}
      </button>

      <aside className="layout-sidebar" id="layout-sidebar">
        <button
          type="button"
          className="layout-close"
          onClick={() => setNavOpen(false)}
          aria-label="Close navigation"
        >
          <span aria-hidden="true">✕</span>
        </button>

        <button
          type="button"
          className="layout-brand"
          onClick={() => {
            onNavigate("dashboard");
            setNavOpen(false);
          }}
        >
          <img src="/logo.png" alt="X-Ray Logo" className="sidebar-logo" />
          <span className="layout-brand-text">
            <span className="layout-brand-name">X-Ray</span>
            <span className="layout-brand-tagline">Hidden-failure analysis for AI agents</span>
          </span>
        </button>

        <nav className="layout-nav" aria-label="Main navigation">
          {NAV_GROUPS.map((group) => (
            <div key={group.heading} className="layout-nav-group">
              <p className="layout-nav-heading">{group.heading}</p>
              {group.items.map((item) => {
                const Icon = item.icon;
                const isCurrent = item.page === activePage;
                return (
                  <button
                    key={item.page}
                    type="button"
                    className={`layout-nav-link${isCurrent ? " is-active" : ""}`}
                    aria-current={isCurrent ? "page" : undefined}
                    onClick={() => {
                      onNavigate(item.page);
                      setNavOpen(false);
                    }}
                  >
                    <span className="layout-nav-icon" aria-hidden="true">
                      <Icon />
                    </span>
                    {item.label}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
      </aside>

      <main className="layout-main" id="dashboard">
        {children}
      </main>
    </div>
  );
}