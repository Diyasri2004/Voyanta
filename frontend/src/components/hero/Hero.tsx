"use client";

import { forwardRef, useEffect, useMemo, useState } from "react";
import { ArrowDown } from "lucide-react";
import FlapBoard from "./FlapBoard";
import CommandBar from "./CommandBar";
import { DESTINATIONS, Destination, TOUR, findDestination, formatCoords, getDestination } from "@/lib/destinations";
import type { LandingProps } from "./types";

interface HeroProps extends LandingProps {
  /** Reports which destination the globe should be facing. */
  onDestination: (d: Destination | null) => void;
}

const FALLBACK_CHIPS = ["Kyoto", "Lisbon", "Marrakech", "Dubai", "Bali", "Cape Town"];

const Hero = forwardRef<HTMLElement, HeroProps>(function Hero(props, ref) {
  const { t, locationInput, onDestination } = props;
  const [hover, setHover] = useState<string | null>(null);
  const [tourIdx, setTourIdx] = useState(0);

  const typed = useMemo(() => findDestination(locationInput), [locationInput]);
  const typingUnknown = locationInput.trim().length >= 2 && !typed;
  const hovered = hover ? findDestination(hover) : null;
  const idle = !hover && !locationInput.trim();

  // With nothing hovered or typed, the globe tours the world on its own.
  useEffect(() => {
    if (!idle) return;
    const id = window.setInterval(() => setTourIdx((i) => (i + 1) % TOUR.length), 4600);
    return () => window.clearInterval(id);
  }, [idle]);

  const touring = getDestination(TOUR[tourIdx]) ?? DESTINATIONS[0];
  const active: Destination | null = hovered ?? typed ?? (typingUnknown ? null : touring);

  useEffect(() => {
    onDestination(active);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active?.name]);

  const boardText = hovered?.name ?? (locationInput.trim() ? (typed?.name ?? locationInput.trim()) : touring.name);

  const chips = props.trending.length ? props.trending.map((x) => x.name) : FALLBACK_CHIPS;

  return (
    <section ref={ref} className="relative z-10 flex min-h-[100svh] flex-col justify-center px-5 pb-16 pt-[27svh] sm:px-8 lg:px-14 lg:pt-28">
      <div className="mx-auto w-full max-w-[1500px]">
        <div className="max-w-[44rem]">
          <h1 className="font-display text-[clamp(2.7rem,6.4vw,5.9rem)] leading-[0.96] text-[#f3ecdc]">{t.heroTitle}</h1>

          <div className="mt-7 flex flex-col gap-3">
            <FlapBoard text={boardText} />
            <p className="min-h-[1.25rem] text-sm text-white/55" aria-live="polite">
              {active ? (
                <>
                  {active.country}
                  <span className="ml-3 tabular-nums text-white/35">{formatCoords(active.lat, active.lng)}</span>
                </>
              ) : typingUnknown ? (
                <span className="text-white/40">{locationInput.trim()}</span>
              ) : null}
            </p>
          </div>

          <div className="mt-8">
            <CommandBar {...props} />
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-2">
            {props.loadingTrending && !props.trending.length
              ? FALLBACK_CHIPS.slice(0, 5).map((n) => <span key={n} className="h-8 w-20 animate-pulse rounded-full bg-white/[0.06]" />)
              : chips.slice(0, 8).map((name) => (
                  <button
                    key={name}
                    type="button"
                    onMouseEnter={() => setHover(name)}
                    onMouseLeave={() => setHover(null)}
                    onFocus={() => setHover(name)}
                    onBlur={() => setHover(null)}
                    onClick={() => props.setLocationInput(name)}
                    className="rounded-full border border-white/10 bg-white/[0.04] px-4 py-1.5 text-sm font-medium text-white/75 outline-none transition hover:border-[#ffc36b]/50 hover:bg-[#ffc36b]/10 hover:text-white focus-visible:border-[#ffc36b]/60"
                  >
                    {name}
                  </button>
                ))}
          </div>

          <p className="mt-6 max-w-md text-sm leading-relaxed text-white/45">{t.heroSubtitle}</p>
        </div>
      </div>

      <a
        href="#how-it-works"
        className="absolute bottom-6 left-1/2 hidden -translate-x-1/2 items-center gap-2 text-xs text-white/40 transition hover:text-white/80 sm:flex"
      >
        How it works
        <ArrowDown className="h-3.5 w-3.5 animate-bounce" />
      </a>
    </section>
  );
});

export default Hero;
