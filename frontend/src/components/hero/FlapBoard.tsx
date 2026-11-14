"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";

const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const CELLS = 12;

function Flap({ char, index }: { char: string; index: number }) {
  const reduce = useReducedMotion();
  const [shown, setShown] = useState(" ");
  const current = useRef(" ");

  useEffect(() => {
    if (reduce) {
      current.current = char;
      setShown(char);
      return;
    }
    if (current.current === char) return;
    // Spin through a few random letters, then settle — later cells spin longer,
    // so the word resolves left to right like a real departures board.
    let steps = 4 + index * 1.6 + Math.random() * 3;
    const id = window.setInterval(() => {
      steps -= 1;
      const next = steps <= 0 ? char : ALPHABET[Math.floor(Math.random() * ALPHABET.length)];
      current.current = next;
      setShown(next);
      if (steps <= 0) window.clearInterval(id);
    }, 52);
    return () => window.clearInterval(id);
  }, [char, index, reduce]);

  return (
    <span
      className="flap relative inline-flex h-[clamp(2.2rem,4.6vw,4.1rem)] w-[clamp(1.45rem,3.1vw,2.8rem)] items-center justify-center overflow-hidden rounded-[0.28rem] text-[clamp(1.02rem,2.21vw,2.05rem)] font-extrabold leading-none text-[#ffc36b]"
      style={{ perspective: 400 }}
    >
      <motion.span
        key={shown}
        initial={reduce ? false : { rotateX: -70, opacity: 0.35 }}
        animate={{ rotateX: 0, opacity: 1 }}
        transition={{ duration: 0.08, ease: "easeOut" }}
        style={{ transformOrigin: "50% 0%", display: "inline-block", textShadow: "0 0 18px rgba(255,195,107,0.55)" }}
      >
        {shown === " " ? " " : shown}
      </motion.span>
    </span>
  );
}

/** Split-flap departures board that spells a destination. */
export default function FlapBoard({ text }: { text: string }) {
  const clean = text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toUpperCase()
    .replace(/[^A-Z ]/g, "")
    .slice(0, CELLS);
  const padded = clean.padEnd(CELLS, " ");

  return (
    <div role="img" aria-label={text || "Destination"} className="inline-flex gap-[clamp(0.2rem,0.45vw,0.4rem)]">
      {padded.split("").map((c, i) => (
        <Flap key={i} char={c} index={i} />
      ))}
    </div>
  );
}
