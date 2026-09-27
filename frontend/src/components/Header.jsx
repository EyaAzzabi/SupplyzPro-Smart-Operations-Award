import { useEffect, useRef, useState } from "react";
import "./Header.css";

const PERIODS = ["Last 24 hours", "Last 7 days", "Last 30 days"];

function CalendarIcon() {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <rect x="3.5" y="5" width="17" height="16" rx="2.5" />
      <path d="M3.5 10h17M8 3v4M16 3v4" />
    </svg>
  );
}

function ChevronIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 9.5 12 15.5l6-6" />
    </svg>
  );
}

function ChevronRightIcon() {
  return (
    <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.5 5.5 16 12l-6.5 6.5" />
    </svg>
  );
}

export default function Header({ pageLabel = "Dashboard", title, subtitle }) {
  const [period, setPeriod] = useState(PERIODS[0]);
  const [periodOpen, setPeriodOpen] = useState(false);
  const actionsRef = useRef(null);

  useEffect(() => {
    if (!periodOpen) return undefined;

    const onPointerDown = (event) => {
      if (actionsRef.current && !actionsRef.current.contains(event.target)) {
        setPeriodOpen(false);
      }
    };
    const onKeyDown = (event) => {
      if (event.key === "Escape") setPeriodOpen(false);
    };

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [periodOpen]);

  return (
    <header className="page-header">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <ol>
          <li>Workspace</li>
          <li className="breadcrumb-sep" aria-hidden="true">
            <ChevronRightIcon />
          </li>
          <li aria-current="page">{pageLabel}</li>
        </ol>
      </nav>

      <div className="page-header-row">
        <div className="page-header-text">
          <h1 className="page-title">{title}</h1>
          <p className="page-subtitle">{subtitle}</p>
        </div>

        <div className="page-header-actions" ref={actionsRef}>
          <div className="header-menu">
            <button
              type="button"
              className="period-button"
              aria-haspopup="listbox"
              aria-expanded={periodOpen}
              onClick={() => setPeriodOpen((open) => !open)}
            >
              <CalendarIcon />
              <span>{period}</span>
              <ChevronIcon />
            </button>

            {periodOpen && (
              <ul className="header-menu-list" role="listbox" aria-label="Time period">
                {PERIODS.map((option) => (
                  <li key={option}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={option === period}
                      className={`header-menu-option${option === period ? " is-selected" : ""}`}
                      onClick={() => {
                        setPeriod(option);
                        setPeriodOpen(false);
                      }}
                    >
                      {option}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
