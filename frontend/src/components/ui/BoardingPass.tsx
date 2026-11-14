"use client";

import type { ReactNode } from "react";
import { Plane } from "lucide-react";
import TiltCard from "./TiltCard";

/**
 * Boarding-pass shell for the trip-planning form.
 * The glass background is a separate masked layer (side notches at the
 * perforation line) so dropdowns inside the content are never clipped.
 */
export default function BoardingPass({
  children,
  from = "HOME",
  to = "ANYWHERE",
}: {
  children: ReactNode;
  from?: string;
  to?: string;
}) {
  const notch =
    "radial-gradient(circle 13px at 0 56px, #0000 97%, #000), radial-gradient(circle 13px at 100% 56px, #0000 97%, #000)";

  return (
    <TiltCard max={5} lift={18} className="w-full max-w-[820px] rounded-[2rem]">
      {/* masked glass background */}
      <div
        aria-hidden
        className="glass absolute inset-0 rounded-[2rem]"
        style={{
          WebkitMask: notch,
          mask: notch,
          WebkitMaskComposite: "source-in",
          maskComposite: "intersect",
        }}
      />

      <div className="relative">
        {/* ticket header — exactly 56px so the notches line up */}
        <div className="flex h-14 items-center justify-between border-b border-dashed border-white/15 px-6 text-[10px] font-bold uppercase tracking-[0.28em] text-white/55">
          <span className="flex items-center gap-2 text-[#5eead4]">
            <Plane className="h-3.5 w-3.5 -rotate-45" />
            Voyanta Air
          </span>
          <span className="hidden items-center gap-3 sm:flex">
            <span>{from}</span>
            <span className="h-px w-10 bg-gradient-to-r from-[#5eead4] to-[#ff8a5c]" />
            <span className="text-white">{to}</span>
          </span>
          <span>Boarding pass</span>
        </div>

        <div className="px-4 py-6 sm:px-8 md:px-10 md:py-8">{children}</div>

        {/* stub */}
        <div className="flex items-center justify-between gap-4 border-t border-dashed border-white/15 px-6 py-3">
          <span className="text-[10px] font-semibold uppercase tracking-[0.24em] text-white/40">
            Seat ∞ · Gate Anywhere · Class Explorer
          </span>
          <span aria-hidden className="barcode h-6 w-28 opacity-70" />
        </div>
      </div>
    </TiltCard>
  );
}
