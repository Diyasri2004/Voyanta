"use client";

import { useEffect, useState } from "react";
import { useReducedMotion } from "framer-motion";
import DepthCard from "@/components/ui/DepthCard";

const LANGS = ["English", "हिन्दी", "Español", "Français", "Deutsch", "العربية", "中文", "日本語"];
const CHAT_LANGS = ["Hinglish", "Tanglish", "Teluglish", "Kanglish", "Manglish", "Banglish", "Arabizi", "Pinyin"];
const CURRENCIES: Array<[string, string]> = [
  ["$", "USD"], ["€", "EUR"], ["£", "GBP"],
  ["₹", "INR"], ["¥", "JPY"], ["A$", "AUD"],
  ["C$", "CAD"], ["د.إ", "AED"], ["S$", "SGD"],
];
const REPLY = "Try Shisen-dō. It's a small hillside retreat in northern Kyoto, far quieter than the big temples.";

function Marquee({ items, reverse = false, className = "" }: { items: string[]; reverse?: boolean; className?: string }) {
  const row = [...items, ...items];
  return (
    <div className="overflow-hidden [mask-image:linear-gradient(90deg,transparent,#000_12%,#000_88%,transparent)]">
      <div
        className={`flex w-max gap-10 whitespace-nowrap ${className}`}
        style={{ animation: `${reverse ? "marquee-right" : "marquee-left"} ${reverse ? 46 : 38}s linear infinite` }}
      >
        {row.map((w, i) => (
          <span key={i}>{w}</span>
        ))}
      </div>
    </div>
  );
}

function Languages() {
  return (
    <DepthCard className="lg:col-span-4">
      <div className="flex h-full flex-col justify-between gap-10 p-7 sm:p-9">
        <div style={{ transform: "translateZ(30px)" }}>
          <h3 className="font-display text-[clamp(1.7rem,2.6vw,2.4rem)] leading-tight text-[#f3ecdc]">In your language, the way you type it.</h3>
          <p className="mt-3 max-w-lg text-sm leading-relaxed text-white/55">
            Switch the whole app between eight languages. The guide also replies in the mixed styles people really use in chat.
          </p>
        </div>
        <div className="flex flex-col gap-4" style={{ transform: "translateZ(60px)" }}>
          <Marquee items={LANGS} className="font-display text-[clamp(2rem,4vw,3.4rem)] leading-none text-[#f3ecdc]/85" />
          <Marquee items={CHAT_LANGS} reverse className="text-lg font-semibold text-[#ffc36b]/70" />
        </div>
      </div>
    </DepthCard>
  );
}

function Currencies() {
  const reduce = useReducedMotion();
  const [on, setOn] = useState(3);
  useEffect(() => {
    if (reduce) return;
    const id = window.setInterval(() => setOn((i) => (i + 1) % CURRENCIES.length), 1300);
    return () => window.clearInterval(id);
  }, [reduce]);

  return (
    <DepthCard className="lg:col-span-2">
      <div className="flex h-full flex-col justify-between gap-8 p-7 sm:p-9">
        <div style={{ transform: "translateZ(30px)" }}>
          <h3 className="font-display text-[clamp(1.7rem,2.6vw,2.4rem)] leading-tight text-[#f3ecdc]">Budgets in your currency.</h3>
          <p className="mt-3 text-sm leading-relaxed text-white/55">Nine currencies, from rupees to dirhams.</p>
        </div>
        <div className="grid grid-cols-3 gap-2" style={{ transform: "translateZ(55px)" }}>
          {CURRENCIES.map(([sym, code], i) => (
            <div
              key={code}
              className={`flex aspect-[4/3] flex-col items-center justify-center rounded-xl border transition-all duration-500 ${
                i === on ? "border-[#ffc36b]/70 bg-[#ffc36b]/15 shadow-[0_0_26px_-4px_rgba(255,195,107,0.7)]" : "border-white/8 bg-white/[0.03]"
              }`}
            >
              <span className={`text-xl font-bold transition-colors ${i === on ? "text-[#ffd89a]" : "text-white/70"}`}>{sym}</span>
              <span className="text-[10px] text-white/40">{code}</span>
            </div>
          ))}
        </div>
      </div>
    </DepthCard>
  );
}

function Guide() {
  const reduce = useReducedMotion();
  const [n, setN] = useState(reduce ? REPLY.length : 0);

  useEffect(() => {
    if (reduce) return;
    let i = 0;
    let hold = 0;
    const id = window.setInterval(() => {
      if (i < REPLY.length) {
        i += 1;
        setN(i);
      } else if (hold < 60) {
        hold += 1; // pause on the finished answer
      } else {
        i = 0;
        hold = 0;
        setN(0);
      }
    }, 38);
    return () => window.clearInterval(id);
  }, [reduce]);

  return (
    <DepthCard className="lg:col-span-3">
      <div className="flex h-full flex-col justify-between gap-8 p-7 sm:p-9">
        <div style={{ transform: "translateZ(30px)" }}>
          <h3 className="font-display text-[clamp(1.7rem,2.6vw,2.4rem)] leading-tight text-[#f3ecdc]">A local guide, one message away.</h3>
          <p className="mt-3 max-w-md text-sm leading-relaxed text-white/55">
            Swap a stop for a hidden gem, ask for food and budget, get transit tips or a backup plan for rain.
          </p>
        </div>
        <div className="flex flex-col gap-3" style={{ transform: "translateZ(55px)" }}>
          <div className="ml-auto max-w-[85%] rounded-2xl rounded-br-md border border-[#ffc36b]/25 bg-[#ffc36b]/12 px-4 py-2.5 text-sm text-[#ffe9c4]">
            Swap the temple for a hidden gem.
          </div>
          <div className="min-h-[5.2rem] max-w-[92%] rounded-2xl rounded-bl-md border border-white/10 bg-white/[0.05] px-4 py-3 text-sm leading-relaxed text-white/85">
            {REPLY.slice(0, n)}
            <span className="ml-0.5 inline-block h-[1em] w-[2px] translate-y-[2px] bg-[#ffc36b]" style={{ animation: "caret 1s steps(1) infinite" }} />
          </div>
        </div>
      </div>
    </DepthCard>
  );
}

function Routes() {
  const pins: Array<[number, number]> = [[40, 190], [120, 110], [215, 150], [300, 60]];
  return (
    <DepthCard className="lg:col-span-3">
      <div className="flex h-full flex-col justify-between gap-8 p-7 sm:p-9">
        <div style={{ transform: "translateZ(30px)" }}>
          <h3 className="font-display text-[clamp(1.7rem,2.6vw,2.4rem)] leading-tight text-[#f3ecdc]">Every stop opens in your maps app.</h3>
          <p className="mt-3 max-w-md text-sm leading-relaxed text-white/55">Tap a marker for turn-by-turn directions. Routes show distance and travel time for each day.</p>
        </div>
        <div style={{ transform: "translateZ(55px)" }}>
          <svg viewBox="0 0 340 230" className="h-auto w-full" role="img" aria-label="A route connecting four stops">
            <defs>
              <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">
                <path d="M28 0H0V28" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
              </pattern>
            </defs>
            <rect width="340" height="230" rx="16" fill="rgba(255,255,255,0.025)" />
            <rect width="340" height="230" rx="16" fill="url(#grid)" />
            <path d="M40 190 C 70 120, 90 100, 120 110 S 190 190, 215 150 S 280 70, 300 60" fill="none" stroke="rgba(255,195,107,0.25)" strokeWidth="6" strokeLinecap="round" />
            <path
              d="M40 190 C 70 120, 90 100, 120 110 S 190 190, 215 150 S 280 70, 300 60"
              fill="none"
              stroke="#ffc36b"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeDasharray="6 8"
              style={{ animation: "route-flow 1.4s linear infinite" }}
            />
            {pins.map(([x, y], i) => (
              <g key={i}>
                <circle cx={x} cy={y} r="11" fill="rgba(255,195,107,0.15)" />
                <circle cx={x} cy={y} r="5" fill="#ffc36b" />
              </g>
            ))}
          </svg>
        </div>
      </div>
    </DepthCard>
  );
}

export default function Capabilities() {
  return (
    <section className="relative z-10 px-5 py-24 sm:px-8 lg:px-14 lg:py-36">
      <div className="mx-auto w-full max-w-[1500px]">
        <h2 className="max-w-3xl font-display text-[clamp(2.2rem,4.4vw,4rem)] leading-[1.02] text-[#f3ecdc]">
          Made for how you actually travel.
        </h2>
        <div className="mt-14 grid gap-5 lg:grid-cols-6">
          <Languages />
          <Currencies />
          <Guide />
          <Routes />
        </div>
      </div>
    </section>
  );
}
