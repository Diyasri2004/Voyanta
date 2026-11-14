"use client";

import { useEffect, useSyncExternalStore } from "react";
import dynamic from "next/dynamic";
import { getGhost, sceneStore, subscribeGhost } from "@/lib/sceneStore";

// WebGL only exists in the browser, so the scene is loaded client-side only.
const TravelScene = dynamic(() => import("./TravelScene"), {
  ssr: false,
  loading: () => null,
});

/**
 * Fixed, full-screen 3D world behind the whole app.
 * `recede` pushes it back while the dashboard is on screen.
 */
export default function TravelBackdrop({ recede = false, dive = false }: { recede?: boolean; dive?: boolean }) {
  const ghost = useSyncExternalStore(subscribeGhost, getGhost, () => false);
  useEffect(() => {
    sceneStore.recede = recede ? 1 : 0;
  }, [recede]);

  // dev-only handle so the scene can be steered from the console / tests
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") {
      (window as unknown as { __scene?: typeof sceneStore }).__scene = sceneStore;
    }
  }, []);

  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden bg-[#050912] transition-opacity duration-[1200ms]"
      style={{ opacity: recede ? 0.28 : ghost ? 0.34 : 1 }}
    >
      <TravelScene />
      {/* keep headline side legible over the globe */}
      <div
        className="absolute inset-0 bg-[linear-gradient(90deg,rgba(5,9,18,0.92)_0%,rgba(5,9,18,0.55)_38%,transparent_70%)] transition-opacity duration-1000 max-lg:bg-[linear-gradient(180deg,rgba(5,9,18,0)_0%,rgba(5,9,18,0.15)_24%,rgba(5,9,18,0.9)_46%)]"
        style={{ opacity: dive ? 0.12 : 1 }}
      />
      <div className="absolute inset-0 shadow-[inset_0_0_200px_70px_rgba(3,5,12,0.9)]" />
    </div>
  );
}
