"use client";

import dynamic from "next/dynamic";

// WebGL only exists in the browser, so the scene is loaded client-side only.
const TravelScene = dynamic(() => import("./TravelScene"), {
  ssr: false,
  loading: () => null,
});

/**
 * Fixed, full-screen 3D world that sits behind the whole app.
 * `dim` fades it back when the user is deep inside the dashboard.
 */
export default function TravelBackdrop({ dim = false }: { dim?: boolean }) {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden transition-opacity duration-1000"
      style={{ opacity: dim ? 0.32 : 1 }}
    >
      {/* night-sky gradient + aurora haze */}
      <div className="absolute inset-0 bg-[radial-gradient(120%_80%_at_75%_10%,rgba(94,234,212,0.10),transparent_55%),radial-gradient(90%_70%_at_5%_95%,rgba(255,138,92,0.09),transparent_60%),linear-gradient(180deg,#060a16_0%,#04060d_100%)]" />
      <TravelScene />
      {/* readability vignette: keeps left-side content crisp over the globe */}
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(4,6,13,0.88)_0%,rgba(4,6,13,0.35)_45%,transparent_75%)] max-lg:bg-[linear-gradient(180deg,rgba(4,6,13,0.2)_0%,rgba(4,6,13,0.8)_70%)]" />
      <div className="absolute inset-0 shadow-[inset_0_0_180px_60px_rgba(0,0,0,0.75)]" />
    </div>
  );
}
