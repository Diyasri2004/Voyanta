"use client";

import { MapPin, Navigation } from "lucide-react";
import { getTranslation, LanguageName } from "@/lib/i18n";

export interface PillarItemData {
  id?: string;
  title: string;
  category: string;
  description: string;
  address?: string;
  maps_url?: string;
  serving_style?: string;
  event_time?: string;
  price_range?: string;
}

export default function PillarTab({
  items,
  destination,
  selectedLanguage = "English",
}: {
  items: PillarItemData[];
  destination: string;
  selectedLanguage?: LanguageName;
}) {
  const t = getTranslation(selectedLanguage);

  if (!items || items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center bg-white/5 rounded-2xl border border-white/10 my-4">
        <Navigation className="h-8 w-8 text-[#00f0ff] mb-2 animate-pulse" />
        <p className="text-sm text-white font-bold mb-1">Discovering Local Spots</p>
        <p className="text-xs text-[#94A3B8]">Curating top verified locations in {destination}...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {items.map((item, idx) => {
        const mapsUrl =
          item.maps_url ||
          `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
            `${item.title}, ${destination}`
          )}`;

        return (
          <div
            key={item.id || idx}
            className="bg-white/5 border border-white/10 rounded-2xl p-4 flex flex-col gap-2 relative group hover:border-[#00f0ff]/40 transition-all shadow-[0_4px_20px_rgba(0,0,0,0.3)]"
          >
            <div className="flex justify-between items-start gap-2">
              <div>
                <div className="flex flex-wrap items-center gap-2 mb-1.5">
                  <span className="text-[10px] font-bold text-[#00f0ff] uppercase tracking-wider bg-[#00f0ff]/10 px-2.5 py-0.5 rounded-full border border-[#00f0ff]/20">
                    {item.category}
                  </span>
                  {item.serving_style && (
                    <span className="text-[10px] font-bold text-[#39ff14] bg-[#39ff14]/10 px-2 py-0.5 rounded-full border border-[#39ff14]/20">
                      🍽️ {item.serving_style}
                    </span>
                  )}
                  {item.event_time && (
                    <span className="text-[10px] font-bold text-[#ff007f] bg-[#ff007f]/10 px-2 py-0.5 rounded-full border border-[#ff007f]/20">
                      ⏰ {item.event_time}
                    </span>
                  )}
                </div>
                <h3 className="font-syne font-bold text-base text-white group-hover:text-[#00f0ff] transition-colors">
                  {item.title}
                </h3>
                {item.address && (
                  <p className="text-xs text-[#94A3B8] flex items-center gap-1 mt-0.5">
                    <MapPin className="h-3 w-3 text-[#64748B] shrink-0" />
                    {item.address}
                  </p>
                )}
              </div>
              {item.price_range && (
                <span className="text-xs font-bold text-[#ff007f] bg-[#ff007f]/10 px-2.5 py-1 rounded-lg border border-[#ff007f]/30 shrink-0">
                  {item.price_range}
                </span>
              )}
            </div>

            <p className="text-xs text-[#CBD5E1] leading-relaxed mt-1">{item.description}</p>

            <div className="pt-2 border-t border-white/5 flex items-center justify-between mt-1">
              <a
                href={mapsUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#39ff14]/10 text-[#39ff14] border border-[#39ff14]/30 rounded-lg font-mono text-xs font-bold hover:bg-[#39ff14]/20 transition-all shadow-[0_0_10px_rgba(57,255,20,0.2)]"
              >
                📍 {t.navigateInMaps}
              </a>
            </div>
          </div>
        );
      })}
    </div>
  );
}
