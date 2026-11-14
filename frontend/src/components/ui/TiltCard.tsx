"use client";

import type { ReactNode } from "react";
import {
  motion,
  useMotionTemplate,
  useMotionValue,
  useReducedMotion,
  useSpring,
  useTransform,
} from "framer-motion";

interface TiltCardProps {
  children: ReactNode;
  className?: string;
  /** max tilt in degrees */
  max?: number;
  /** lift towards the viewer on hover (px) */
  lift?: number;
  glare?: boolean;
}

/**
 * Pointer-driven 3D tilt with a moving specular glare.
 * Children can use `translate-z-*` style transforms (via style) to pop out,
 * because the card uses preserve-3d.
 */
export default function TiltCard({ children, className = "", max = 7, lift = 14, glare = true }: TiltCardProps) {
  const reduce = useReducedMotion();
  const px = useMotionValue(0.5);
  const py = useMotionValue(0.5);
  const hover = useMotionValue(0);

  const spring = { stiffness: 170, damping: 18, mass: 0.6 };
  const sx = useSpring(px, spring);
  const sy = useSpring(py, spring);
  const sz = useSpring(hover, spring);

  const rotateY = useTransform(sx, [0, 1], [-max, max]);
  const rotateX = useTransform(sy, [0, 1], [max, -max]);
  const z = useTransform(sz, [0, 1], [0, lift]);

  const gx = useTransform(sx, [0, 1], [0, 100]);
  const gy = useTransform(sy, [0, 1], [0, 100]);
  const glareBg = useMotionTemplate`radial-gradient(520px circle at ${gx}% ${gy}%, rgba(255,255,255,0.13), transparent 45%)`;

  return (
    <motion.div
      className={`relative ${className}`}
      style={{
        transformPerspective: 1200,
        transformStyle: "preserve-3d",
        rotateX: reduce ? 0 : rotateX,
        rotateY: reduce ? 0 : rotateY,
        z: reduce ? 0 : z,
      }}
      onPointerMove={(e) => {
        if (reduce || e.pointerType === "touch") return;
        const r = e.currentTarget.getBoundingClientRect();
        px.set((e.clientX - r.left) / r.width);
        py.set((e.clientY - r.top) / r.height);
        hover.set(1);
      }}
      onPointerLeave={() => {
        px.set(0.5);
        py.set(0.5);
        hover.set(0);
      }}
    >
      {children}
      {glare && !reduce && (
        <motion.div
          aria-hidden
          className="pointer-events-none absolute inset-0 rounded-[inherit]"
          style={{ background: glareBg }}
        />
      )}
    </motion.div>
  );
}
