"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useInView, useMotionValueEvent, useScroll, useSpring } from "framer-motion";

const STOPS = [
  { time: "07:30", name: "Fushimi Inari Taisha", note: "Walk the torii gates early, before the tour groups arrive.", length: "2 h", leg: "" },
  { time: "10:30", name: "Arashiyama Bamboo Grove", note: "A short train ride west. Stroll the grove, then the river path.", length: "1.5 h", leg: "35 min by train" },
  { time: "13:00", name: "Nishiki Market", note: "Lunch standing up: pickles, tamagoyaki, grilled skewers.", length: "1 h", leg: "25 min by train" },
  { time: "15:30", name: "Kinkaku-ji", note: "The golden pavilion, best in the softer afternoon light.", length: "1 h", leg: "20 min by bus" },
  { time: "19:00", name: "Gion at dusk", note: "Lantern-lit lanes and teahouses. Dinner nearby.", length: "2 h", leg: "25 min by bus" },
];

export default function Itinerary({ onVisible }: { onVisible: (v: boolean) => void }) {
  const section = useRef<HTMLElement>(null);
  const list = useRef<HTMLOListElement>(null);
  const inView = useInView(section, { amount: 0.4 });
  const [active, setActive] = useState(0);

  useEffect(() => onVisible(inView), [inView, onVisible]);

  const { scrollYProgress } = useScroll({ target: list, offset: ["start 62%", "end 58%"] });
  const fill = useSpring(scrollYProgress, { stiffness: 110, damping: 24, mass: 0.4 });
  useMotionValueEvent(fill, "change", (v) => setActive(Math.min(STOPS.length - 1, Math.max(0, Math.floor(v * (STOPS.length - 1) + 0.15)))));

  return (
    <section ref={section} id="how-it-works" className="relative z-10 px-5 py-28 sm:px-8 lg:px-14 lg:py-40">
      <div className="mx-auto grid w-full max-w-[1500px] gap-14 lg:grid-cols-[minmax(0,27rem)_minmax(0,1fr)] lg:gap-24">
        <div className="lg:sticky lg:top-32 lg:self-start">
          <h2 className="font-display text-[clamp(1.8rem,3.61vw,3.28rem)] leading-[1.02] text-[#f3ecdc]">Your trip, laid out day by day.</h2>
          <p className="mt-6 max-w-md text-base leading-relaxed text-white/60">
            Choose a place and your dates. Voyanta builds each day with stops, distances and travel time, then adds food, events and a budget.
          </p>
          <p className="mt-6 text-sm text-white/40">A sample: day one of three in Kyoto.</p>
        </div>

        <div className="relative max-w-[28rem]">
          <div aria-hidden className="absolute bottom-3 left-[11px] top-3 w-[2px] rounded-full bg-white/10" />
          <motion.div
            aria-hidden
            style={{ scaleY: fill, transformOrigin: "top" }}
            className="absolute bottom-3 left-[11px] top-3 w-[2px] rounded-full bg-gradient-to-b from-[#ffe2ae] via-[#ffc36b] to-[#ff9d5c] shadow-[0_0_14px_rgba(255,176,80,0.8)]"
          />

          <ol ref={list} className="flex flex-col gap-10 pl-12 sm:gap-12">
            {STOPS.map((s, i) => {
              const reached = i <= active;
              return (
                <li key={s.name} className="relative">
                  <span
                    aria-hidden
                    className={`absolute -left-12 top-1.5 flex h-6 w-6 items-center justify-center rounded-full border transition-all duration-500 ${
                      reached ? "border-[#ffc36b] bg-[#ffc36b] shadow-[0_0_22px_rgba(255,195,107,0.9)]" : "border-white/20 bg-[#050912]"
                    }`}
                  >
                    <span className={`h-1.5 w-1.5 rounded-full ${reached ? "bg-[#1b1206]" : "bg-white/30"}`} />
                  </span>

                  {s.leg && <p className="mb-3 -mt-5 text-xs text-white/35">{s.leg}</p>}

                  <div className={`flex flex-col gap-1 transition-opacity duration-500 sm:flex-row sm:items-baseline sm:gap-6 ${reached ? "opacity-100" : "opacity-45"}`}>
                    <span className="w-14 shrink-0 text-sm font-semibold tabular-nums text-[#ffc36b]">{s.time}</span>
                    <div className="min-w-0 flex-1">
                      <h3 className="font-display text-[clamp(1.23rem,2.13vw,1.8rem)] leading-tight text-[#f3ecdc]">{s.name}</h3>
                      <p className="mt-1.5 text-sm leading-relaxed text-white/55">{s.note}</p>
                      <p className="mt-1 text-xs text-white/35">{s.length}</p>
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      </div>
    </section>
  );
}
