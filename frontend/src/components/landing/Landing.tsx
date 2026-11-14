"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, useInView, useMotionValue, useSpring } from "framer-motion";
import Hero from "@/components/hero/Hero";
import Itinerary from "./Itinerary";
import Pillars from "./Pillars";
import Capabilities from "./Capabilities";
import FinalCTA from "./FinalCTA";
import type { LandingProps } from "@/components/hero/types";
import { Destination, getDestination } from "@/lib/destinations";
import { sceneStore, setGhost } from "@/lib/sceneStore";

/** Soft amber light that follows the cursor — a quiet sense of place, not a effect to notice. */
function CursorGlow() {
  const x = useMotionValue(-400);
  const y = useMotionValue(-400);
  const sx = useSpring(x, { stiffness: 90, damping: 22 });
  const sy = useSpring(y, { stiffness: 90, damping: 22 });
  useEffect(() => {
    const move = (e: PointerEvent) => {
      if (e.pointerType === "touch") return;
      x.set(e.clientX - 260);
      y.set(e.clientY - 260);
    };
    window.addEventListener("pointermove", move, { passive: true });
    return () => window.removeEventListener("pointermove", move);
  }, [x, y]);
  return (
    <motion.div
      aria-hidden
      className="pointer-events-none fixed left-0 top-0 z-[5] h-[520px] w-[520px] rounded-full opacity-[0.07] mix-blend-screen"
      style={{ x: sx, y: sy, background: "radial-gradient(circle, #ffc36b 0%, transparent 62%)" }}
    />
  );
}

/**
 * The whole marketing page. It owns the link between the DOM and the 3D globe:
 * which city the globe faces, and how far through the page we are.
 */
export default function Landing(props: LandingProps) {
  const heroRef = useRef<HTMLElement>(null);
  const heroVisible = useInView(heroRef, { amount: 0.3 });
  const [itineraryVisible, setItineraryVisible] = useState(false);
  const [heroDest, setHeroDest] = useState<Destination | null>(null);

  // Which city should the globe face right now?
  useEffect(() => {
    const kyoto = getDestination("Kyoto");
    const d = itineraryVisible ? kyoto : heroVisible ? heroDest : null;
    sceneStore.focus = d ? { lat: d.lat, lng: d.lng } : null;
  }, [itineraryVisible, heroVisible, heroDest]);

  // Scroll progress drives the globe's choreography.
  useEffect(() => {
    let raf = 0;
    const update = () => {
      raf = 0;
      const max = document.documentElement.scrollHeight - window.innerHeight;
      sceneStore.scroll = max > 0 ? window.scrollY / max : 0;
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (raf) cancelAnimationFrame(raf);
      sceneStore.scroll = 0;
    };
  }, []);

  const [pillarsVisible, setPillarsVisible] = useState(false);
  const onItinerary = useCallback((v: boolean) => setItineraryVisible(v), []);
  const onPillars = useCallback((v: boolean) => setPillarsVisible(v), []);
  // text-heavy sections: the globe steps back (on phones that includes the itinerary)
  useEffect(() => {
    const narrow = window.innerWidth <= 980;
    setGhost(pillarsVisible || (narrow && itineraryVisible));
  }, [pillarsVisible, itineraryVisible]);
  useEffect(() => () => setGhost(false), []);

  const startPlanning = useCallback(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
    window.setTimeout(() => {
      document.querySelector<HTMLInputElement>('form[aria-label="Plan a trip"] input[type="text"]')?.focus();
    }, 700);
  }, []);

  return (
    <div className="relative z-10">
      <CursorGlow />
      <Hero ref={heroRef} {...props} onDestination={setHeroDest} />
      <Itinerary onVisible={onItinerary} />
      <Pillars t={props.t} onVisible={onPillars} />
      <Capabilities />
      <FinalCTA onStart={startPlanning} />
    </div>
  );
}
