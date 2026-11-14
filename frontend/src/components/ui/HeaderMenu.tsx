"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check, ChevronDown, Globe2, Coins } from "lucide-react";

export type HeaderMenuOption = { value: string; label: string; hint?: string };

/** Glass pill dropdown matching the landing page (no native <select>, no flag emoji). */
export default function HeaderMenu({
  icon,
  value,
  options,
  onChange,
  display,
  ariaLabel,
  size = "md",
}: {
  icon: "globe" | "coins";
  value: string;
  options: HeaderMenuOption[];
  onChange: (v: string) => void;
  display: string;
  ariaLabel: string;
  size?: "md" | "sm";
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const Icon = icon === "globe" ? Globe2 : Coins;

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className={`glass flex items-center gap-1.5 rounded-full font-semibold ${size === "sm" ? "h-8 px-2.5 text-[11px]" : "h-10 px-3 text-xs sm:gap-2 sm:px-3.5"} text-[#e8edf7] transition hover:border-[#ffc36b]/40 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#ffc36b] ${
          open ? "border-[#ffc36b]/50" : ""
        }`}
      >
        <Icon className="h-4 w-4 text-[#ffc36b]" strokeWidth={1.8} />
        <span className={size === "sm" ? "" : "hidden sm:inline"}>{display}</span>
        <ChevronDown className={`h-3.5 w-3.5 text-[#8b95ab] transition-transform ${size === "sm" ? "" : "hidden sm:block"} ${open ? "rotate-180" : ""}`} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.ul
            role="listbox"
            initial={{ opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }}
            transition={{ duration: 0.16 }}
            className="absolute right-0 top-[calc(100%+8px)] z-50 max-h-72 min-w-[12rem] overflow-y-auto rounded-2xl border border-white/10 bg-[#0a1020]/95 p-1.5 shadow-[0_24px_60px_-12px_rgba(0,0,0,0.8)] backdrop-blur-2xl"
          >
            {options.map((o) => {
              const active = o.value === value;
              return (
                <li key={o.value} role="option" aria-selected={active}>
                  <button
                    type="button"
                    onClick={() => {
                      onChange(o.value);
                      setOpen(false);
                    }}
                    className={`flex w-full items-center justify-between gap-3 rounded-xl px-3 py-2 text-left text-xs transition ${
                      active ? "bg-[#ffc36b]/15 text-[#ffd89a]" : "text-[#cbd3e3] hover:bg-white/[0.06] hover:text-white"
                    }`}
                  >
                    <span className="font-semibold">{o.label}</span>
                    <span className="flex items-center gap-2 text-[#8b95ab]">
                      {o.hint}
                      {active && <Check className="h-3.5 w-3.5 text-[#ffc36b]" />}
                    </span>
                  </button>
                </li>
              );
            })}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
}
