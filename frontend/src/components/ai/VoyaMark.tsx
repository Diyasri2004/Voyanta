/** Voya's emblem: a four-point compass star with a small plane orbiting it. */
export default function VoyaMark({ size = 28, orbit = true }: { size?: number; orbit?: boolean }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-hidden>
      <defs>
        <linearGradient id="voya-g" x1="8" y1="6" x2="40" y2="42" gradientUnits="userSpaceOnUse">
          <stop stopColor="#fff1d0" />
          <stop offset="0.55" stopColor="#ffc36b" />
          <stop offset="1" stopColor="#ff9d5c" />
        </linearGradient>
      </defs>
      <circle cx="24" cy="24" r="19" stroke="currentColor" strokeOpacity="0.35" strokeWidth="1.2" strokeDasharray="2 4" />
      <path
        d="M24 5c1.6 8.6 4.4 14.4 19 19-14.6 4.6-17.4 10.4-19 19-1.6-8.6-4.4-14.4-19-19C19.6 19.4 22.4 13.6 24 5Z"
        fill="url(#voya-g)"
      />
      <circle cx="24" cy="24" r="2.4" fill="#1b1206" />
      {orbit && (
        <g>
          <animateTransform attributeName="transform" type="rotate" from="0 24 24" to="360 24 24" dur="9s" repeatCount="indefinite" />
          <circle cx="24" cy="5" r="2.6" fill="#7fd6ff" />
        </g>
      )}
    </svg>
  );
}
