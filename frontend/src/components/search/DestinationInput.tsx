"use client";

import React, { useState, useEffect } from "react";
import { Search, MapPin } from "lucide-react";

interface DestinationInputProps {
  value: string;
  onChange: (val: string) => void;
  placeholder?: string;
  className?: string;
}

export function DestinationInput({
  value,
  onChange,
  placeholder = "Where do you want to explore?",
  className = "",
}: DestinationInputProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<Array<{ label: string; value: string }>>([]);

  useEffect(() => {
    const query = value.trim();
    if (!query) {
      setSuggestions([]);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      fetch(`/api/autocomplete?q=${encodeURIComponent(query)}`, { signal: controller.signal })
        .then((res) => res.json())
        .then((data) => {
          if (data && Array.isArray(data.suggestions)) {
            setSuggestions(data.suggestions);
          }
        })
        .catch(() => {});
    }, 300);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [value]);

  return (
    <div className={`relative ${className}`}>
      <Search className="pointer-events-none absolute left-4 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-[#ffc36b]" />
      <input
        type="text"
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setIsOpen(true);
        }}
        onFocus={() => setIsOpen(true)}
        onBlur={() => setTimeout(() => setIsOpen(false), 200)}
        placeholder={placeholder}
        autoComplete="off"
        className="w-full min-h-[3.6rem] rounded-2xl border border-white/10 bg-white/[0.05] pl-12 pr-5 text-base text-white placeholder-white/35 outline-none transition-all hover:border-white/25 focus:border-[#ffc36b]/60 focus:bg-white/[0.07] focus:shadow-[0_0_0_4px_rgba(255,195,107,0.10)]"
      />

      {isOpen && value.trim().length > 0 && suggestions.length > 0 && (
        <div className="absolute top-full mt-2 w-full bg-[#080d19]/95 backdrop-blur-xl border border-white/12 rounded-2xl overflow-hidden z-50 shadow-[0_24px_70px_-10px_rgba(0,0,0,0.9)] transition-all max-h-60 overflow-y-auto">
          {suggestions.map((item, idx) => (
            <button
              key={idx}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                onChange(item.label);
                setIsOpen(false);
              }}
              className="w-full text-left px-5 py-3.5 hover:bg-[#ffc36b]/12 text-white text-sm border-b border-white/5 last:border-0 transition-colors flex items-center gap-2 font-medium"
            >
              <MapPin className="h-4 w-4 text-[#ffc36b] shrink-0" />
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default DestinationInput;
