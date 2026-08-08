"use client";

import { useState } from "react";
import { X, Trash2, Calendar, Clock, Download, Share2, MapPin, Navigation, Sparkles } from "lucide-react";
import { PillarItemData } from "./PillarTab";

export interface SavedPlanItem extends PillarItemData {
  timeSlot?: string;
  dayNumber?: number;
}

export default function PlanBuilderDrawer({
  isOpen,
  onClose,
  items,
  onRemoveItem,
  onClearAll,
  destination,
}: {
  isOpen: boolean;
  onClose: () => void;
  items: SavedPlanItem[];
  onRemoveItem: (index: number) => void;
  onClearAll: () => void;
  destination: string;
}) {
  const [activeDay, setActiveDay] = useState<number>(1);

  if (!isOpen) return null;

  const exportItinerary = () => {
    const lines = [`# VOYANTA Itinerary Plan — ${destination.toUpperCase()}`, ""];
    items.forEach((item, idx) => {
      lines.push(`${idx + 1}. ${item.title} [${item.category}]`);
      if (item.address) lines.push(`   Address: ${item.address}`);
      if (item.maps_url) lines.push(`   Maps: ${item.maps_url}`);
      lines.push("");
    });
    const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Voyanta_Itinerary_${destination.replace(/\s+/g, "_")}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/70 backdrop-blur-sm animate-fade-in flex justify-end">
      <div className="relative w-full max-w-lg bg-[#050810] border-l border-white/10 text-white flex flex-col h-full shadow-2xl">
        {/* Drawer Header */}
        <div className="p-6 border-b border-white/10 flex items-center justify-between bg-[#080c16]">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
              <Calendar className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                Itinerary Plan <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-mono border border-emerald-500/30">{items.length} items</span>
              </h2>
              <p className="text-xs text-gray-400 mt-0.5">Customized spots for {destination}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 text-gray-400 hover:text-white transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Action Controls */}
        {items.length > 0 && (
          <div className="px-6 py-3 border-b border-white/10 bg-[#080c16]/50 flex items-center justify-between">
            <button
              onClick={exportItinerary}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 text-black font-semibold text-xs hover:bg-emerald-400 transition-all shadow-md"
            >
              <Download className="w-3.5 h-3.5" />
              Export Plan
            </button>
            <button
              onClick={onClearAll}
              className="flex items-center gap-1 text-xs text-red-400 hover:text-red-300 transition-all"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Clear All
            </button>
          </div>
        )}

        {/* Item List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {items.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 text-gray-500">
              <div className="w-16 h-16 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mb-4 text-emerald-400">
                <Sparkles className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-semibold text-white">Your Plan is Empty</h3>
              <p className="text-xs mt-1 max-w-xs text-gray-400">
                Click the <span className="text-emerald-400 font-bold">+</span> button on any venue card to add it to your custom itinerary.
              </p>
            </div>
          ) : (
            items.map((item, idx) => (
              <div
                key={idx}
                className="group relative flex gap-4 p-4 rounded-2xl bg-white/[0.03] border border-white/10 hover:border-emerald-500/40 transition-all"
              >
                {item.image_url || item.image ? (
                  <img
                    src={item.image_url || item.image}
                    alt={item.title}
                    className="w-20 h-20 rounded-xl object-cover border border-white/10"
                  />
                ) : (
                  <div className="w-20 h-20 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-gray-500">
                    <MapPin className="w-6 h-6" />
                  </div>
                )}
                <div className="flex-1 min-w-0 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-emerald-400">
                        {item.category}
                      </span>
                      <button
                        onClick={() => onRemoveItem(idx)}
                        className="text-gray-500 hover:text-red-400 transition-all p-1"
                        title="Remove"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <h4 className="text-sm font-bold text-white truncate mt-0.5">{item.title}</h4>
                    {item.description && (
                      <p className="text-xs text-gray-400 line-clamp-1 mt-1">{item.description}</p>
                    )}
                  </div>
                  {item.maps_url && (
                    <a
                      href={item.maps_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] text-emerald-400 hover:underline mt-2 font-mono"
                    >
                      <Navigation className="w-3 h-3" />
                      Navigate
                    </a>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
