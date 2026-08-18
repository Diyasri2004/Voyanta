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
    }, 50);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [value]);

  return (
    <div className={`relative ${className}`}>
      <Search className="pointer-events-none absolute left-[18px] top-1/2 h-[17px] w-[17px] -translate-y-1/2 text-[#475569]" />
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
        className="w-full rounded-full border border-white/[0.09] bg-[#111827]/60 py-[14px] pl-12 pr-5 text-[0.95rem] text-white placeholder-[#475569] outline-none transition-all focus:border-[#00f0ff]/50 focus:bg-[#111827]/90 focus:shadow-[0_0_15px_rgba(0,240,255,0.2)]"
      />

      {isOpen && value.trim().length > 0 && suggestions.length > 0 && (
        <div className="absolute top-full mt-2 w-full bg-[#03050a]/95 backdrop-blur-xl border border-[#00f0ff]/40 rounded-2xl overflow-hidden z-50 shadow-[0_10px_30px_rgba(0,240,255,0.2)] transition-all max-h-60 overflow-y-auto">
          {suggestions.map((item, idx) => (
            <button
              key={idx}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                onChange(item.label);
                setIsOpen(false);
              }}
              className="w-full text-left px-5 py-3.5 hover:bg-[#00f0ff]/15 text-white text-sm border-b border-white/5 last:border-0 transition-colors flex items-center gap-2 font-medium"
            >
              <MapPin className="h-4 w-4 text-[#00f0ff] shrink-0" />
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default DestinationInput;
