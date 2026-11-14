"use client";

import type { ReactNode } from "react";
import TiltCard from "./TiltCard";

/**
 * Glass card with real parallax depth. The glass is a separate background
 * layer (backdrop-filter would flatten the 3D context), so children can lift
 * off the surface with `style={{ transform: "translateZ(40px)" }}`.
 */
export default function DepthCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <TiltCard max={5} lift={14} className={`rounded-[1.6rem] ${className}`}>
      <div aria-hidden className="glass absolute inset-0 rounded-[inherit]" />
      <div className="relative h-full" style={{ transformStyle: "preserve-3d" }}>
        {children}
      </div>
    </TiltCard>
  );
}
