/** Small inline stroke icons (currentColor), so toggle buttons read at a glance
 * instead of relying on their label text alone. */
const base = { width: 15, height: 15, viewBox: "0 0 24 24", fill: "none" };

export function SunIcon(props) {
  return (
    <svg {...base} stroke="currentColor" strokeWidth={2} strokeLinecap="round" {...props}>
      <circle cx="12" cy="12" r="4.5" />
      <path d="M12 2.5v2.5M12 19v2.5M4.6 4.6l1.8 1.8M17.6 17.6l1.8 1.8M2.5 12H5M19 12h2.5M4.6 19.4l1.8-1.8M17.6 6.4l1.8-1.8" />
    </svg>
  );
}

export function MoonIcon(props) {
  return (
    <svg {...base} stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z" />
    </svg>
  );
}

export function TableIcon(props) {
  return (
    <svg {...base} stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <rect x="3" y="4.5" width="18" height="15" rx="2" />
      <line x1="3" y1="10" x2="21" y2="10" />
      <line x1="9" y1="4.5" x2="9" y2="19.5" />
    </svg>
  );
}

export function ResetIcon(props) {
  return (
    <svg {...base} stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M3.5 12a8.5 8.5 0 1 1 2.6 6.1" />
      <path d="M3.5 18v-5h5" />
    </svg>
  );
}
