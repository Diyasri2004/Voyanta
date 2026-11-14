/**
 * Tiny mutable bridge between the DOM (hero, scroll, planning) and the WebGL
 * globe. It is read every frame inside the render loop, so it deliberately
 * is not React state — writing to it never re-renders anything.
 */
export interface SceneState {
  /** Destination the globe should rotate to face, or null to free-spin. */
  focus: { lat: number; lng: number } | null;
  /** 0–1 progress through the landing page scroll. */
  scroll: number;
  /** 0 = relaxed, 1 = diving into the destination (while a trip is planned). */
  warp: number;
  /** 0 = full presence, 1 = receded behind the dashboard. */
  recede: number;
  /** True while a text-heavy section is on screen: the globe fades back. */
  ghost: boolean;
}

export const sceneStore: SceneState = {
  focus: null,
  scroll: 0,
  warp: 0,
  recede: 0,
  ghost: false,
};

const listeners = new Set<() => void>();
export function setGhost(v: boolean) {
  if (sceneStore.ghost === v) return;
  sceneStore.ghost = v;
  listeners.forEach((l) => l());
}
export function subscribeGhost(cb: () => void) {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}
export const getGhost = () => sceneStore.ghost;
