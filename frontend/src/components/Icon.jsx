const PATHS = {
  observed_event: (
    <>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="2.4" fill="currentColor" stroke="none" />
    </>
  ),
  immediate_failure: (
    <>
      <path d="M13 3 5.5 13.5H11l-1 7.5 7.5-10.5H12z" />
    </>
  ),
  contributing_factor: (
    <>
      <path d="M12 5.5v13M5.5 12h13" />
    </>
  ),
  likely_root_cause: (
    <>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="3.4" />
    </>
  ),
  preventive_control: (
    <>
      <path d="M12 3.2 5 6v5.4c0 4.2 2.9 7.6 7 9.4 4.1-1.8 7-5.2 7-9.4V6z" />
      <path d="m9 12 2.2 2.2L15.4 10" />
    </>
  ),
  tool: (
    <>
      <path d="M14.8 6.2a3.6 3.6 0 0 0 4.6 4.6l-8 8a2.3 2.3 0 0 1-3.3-3.3z" />
      <path d="m6.5 6.5 3 3" />
    </>
  ),
  agent: (
    <>
      <rect x="4.5" y="7.5" width="15" height="11" rx="3" />
      <path d="M12 3.5v4M9 13h.01M15 13h.01M9.5 16h5" />
    </>
  ),
  prompt: (
    <>
      <path d="M20.5 12.5c0 3.6-3.8 6.5-8.5 6.5-1 0-2-.15-2.9-.43L4.5 20.5l1.2-3.6C4.3 15.5 3.5 14.1 3.5 12.5c0-3.6 3.8-6.5 8.5-6.5s8.5 2.9 8.5 6.5Z" />
    </>
  ),
  data: (
    <>
      <ellipse cx="12" cy="6.5" rx="7" ry="2.8" />
      <path d="M5 6.5v11c0 1.55 3.13 2.8 7 2.8s7-1.25 7-2.8v-11M5 12c0 1.55 3.13 2.8 7 2.8s7-1.25 7-2.8" />
    </>
  ),
  observability: (
    <>
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
      <circle cx="12" cy="12" r="2.6" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4.5 4.5" />
    </>
  ),
  brain: (
    <>
      <path d="M12 6.2v11.6" />
      <path d="M12 6.4a3 3 0 0 0-5.6-1.2A2.8 2.8 0 0 0 4 9.3a3 3 0 0 0 .4 4.5A3 3 0 0 0 8 19.4a3 3 0 0 0 4-1.9" />
      <path d="M12 6.4a3 3 0 0 1 5.6-1.2A2.8 2.8 0 0 1 20 9.3a3 3 0 0 1-.4 4.5A3 3 0 0 1 16 19.4a3 3 0 0 1-4-1.9" />
    </>
  ),
  play: (
    <>
      <path d="M8.5 5.6 18.4 12 8.5 18.4z" />
    </>
  ),
};

export default function Icon({ name, size = 16, className = "" }) {
  const path = PATHS[name];
  if (!path) return null;
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {path}
    </svg>
  );
}
