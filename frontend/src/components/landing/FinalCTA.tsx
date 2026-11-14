"use client";

import { ArrowUp } from "lucide-react";
import MagneticButton from "@/components/ui/MagneticButton";

export default function FinalCTA({ onStart }: { onStart: () => void }) {
  return (
    <section className="relative z-10 flex min-h-[90svh] flex-col items-center justify-center px-5 pb-10 pt-24 text-center sm:px-8">
      <h2 className="max-w-4xl font-display text-[clamp(2.8rem,7.4vw,6.6rem)] leading-[0.96] text-[#f3ecdc]">
        Pick a place.
        <br />
        We&apos;ll plan the days.
      </h2>
      <div className="mt-12">
        <MagneticButton strength={0.3}>
          <button
            type="button"
            onClick={onStart}
            className="btn-glow inline-flex items-center gap-2.5 rounded-full px-9 py-4 text-base font-bold"
          >
            <ArrowUp className="h-4 w-4" />
            Start planning
          </button>
        </MagneticButton>
      </div>

      <footer className="absolute inset-x-0 bottom-0 flex flex-col items-center justify-between gap-2 px-5 py-6 text-xs text-white/35 sm:flex-row sm:px-8 sm:pr-28 lg:px-14 lg:pr-28">
        <span className="font-display text-base tracking-wide text-white/55">Voyanta</span>
        <span>Map data from Natural Earth.</span>
      </footer>
    </section>
  );
}
