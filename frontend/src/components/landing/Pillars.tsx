"use client";

import { useEffect, useRef } from "react";
import { useInView } from "framer-motion";
import { ArrowUpRight } from "lucide-react";
import type { TranslationDictionary } from "@/lib/i18n";

const PILLARS: Array<{ key: keyof TranslationDictionary; line: string }> = [
  { key: "attractions", line: "Landmarks and sights worth the ticket." },
  { key: "events", line: "Concerts and shows on your actual dates." },
  { key: "culinaryPillar", line: "From street stalls to tasting menus." },
  { key: "barsPubs", line: "Where the locals go after dark." },
  { key: "wellnessPillar", line: "Spas, yoga and quiet rooms." },
  { key: "secretSpots", line: "The places guidebooks skip." },
  { key: "essentialsPillar", line: "Safety, transit and emergency numbers." },
  { key: "shoppingPillar", line: "Markets, makers and malls." },
  { key: "adventuresPillar", line: "Hikes, dives and day trips." },
  { key: "themeParksPillar", line: "Rides for every age." },
  { key: "sacredTemples", line: "Sacred sites, and how to visit them well." },
];

export default function Pillars({ t, onVisible }: { t: TranslationDictionary; onVisible: (v: boolean) => void }) {
  const ref = useRef<HTMLElement>(null);
  const inView = useInView(ref, { amount: 0.3 });
  useEffect(() => onVisible(inView), [inView, onVisible]);

  return (
    <section ref={ref} className="relative z-10 px-5 py-24 sm:px-8 lg:px-14 lg:py-36">
      <div className="mx-auto w-full max-w-[1500px]">
        <h2 className="max-w-3xl font-display text-[clamp(1.8rem,3.61vw,3.28rem)] leading-[1.02] text-[#f3ecdc]">
          Eleven kinds of places, searched for you.
        </h2>

        <ul className="mt-14 border-b border-white/10">
          {PILLARS.map(({ key, line }) => (
            <li key={key} className="group relative border-t border-white/10">
              <span
                aria-hidden
                className="absolute inset-0 -z-10 origin-left scale-x-0 bg-gradient-to-r from-[#ffc36b]/[0.10] via-[#ffc36b]/[0.03] to-transparent transition-transform duration-500 ease-out group-hover:scale-x-100"
              />
              <div className="flex items-center justify-between gap-6 py-5 transition-transform duration-500 ease-out group-hover:translate-x-3 sm:py-6">
                <span className="font-display text-[clamp(1.56rem,3.77vw,3.44rem)] leading-none text-[#f3ecdc]/80 transition-colors duration-300 group-hover:text-[#ffd89a]">
                  {t[key] as string}
                </span>
                <span className="hidden max-w-xs text-right text-sm leading-snug text-white/45 transition-colors group-hover:text-white/75 md:block">{line}</span>
                <ArrowUpRight className="h-6 w-6 shrink-0 text-white/25 transition-all duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-[#ffc36b]" />
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
