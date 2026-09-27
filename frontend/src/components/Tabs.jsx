import { useRef } from "react";
import Icon from "./Icon";
import "./Tabs.css";

export default function Tabs({ tabs, activeTab, onTabChange, ariaLabel = "Sections" }) {
  const listRef = useRef(null);

  const handleKeyDown = (event) => {
    const currentIndex = tabs.findIndex((tab) => tab.id === activeTab);
    if (currentIndex === -1) return;

    let nextIndex = null;
    if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % tabs.length;
    else if (event.key === "ArrowLeft") nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = tabs.length - 1;

    if (nextIndex === null) return;
    event.preventDefault();
    onTabChange(tabs[nextIndex].id);
    listRef.current?.querySelectorAll("button")[nextIndex]?.focus();
  };

  return (
    <div className="tabs" role="tablist" aria-label={ariaLabel} onKeyDown={handleKeyDown} ref={listRef}>
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            id={`tab-${tab.id}`}
            className={`tab${isActive ? " is-active" : ""}`}
            aria-selected={isActive}
            aria-controls={`tabpanel-${tab.id}`}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onTabChange(tab.id)}
          >
            {tab.icon && (
              <span className="tab-icon" aria-hidden="true">
                <Icon name={tab.icon} size={15} />
              </span>
            )}
            <span className="tab-label">{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}
