"use client";

import { useState } from "react";
import { Copy, CheckCircle } from "lucide-react";

export default function StoryTab({ trip }: { trip: any }) {
  const [copied, setCopied] = useState(false);

  const itineraryText = trip?.itinerary?.map((stop: any) => 
    `Day ${stop.day} | ${stop.time}: ${stop.title} (${stop.location})`
  ).join("\n") || "No agenda found.";

  const storyContent = `🚀 Exploring ${trip?.destination || "Unknown"} with Voyanta!\n\n${itineraryText}\n\n#Voyanta #Travel`;

  const copyToClipboard = () => {
    navigator.clipboard.writeText(storyContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col gap-4 h-full">
      <div className="bg-[#ffc36b]/10 border border-[#ffc36b]/30 p-4 rounded-xl">
        <h3 className="text-[#ffc36b] font-syne font-bold text-lg">Share Your Story</h3>
        <p className="text-xs text-[#ffc36b]/80 mt-1">Export your itinerary to a clipboard-friendly text format for social media.</p>
      </div>

      <div className="flex-1 bg-black/40 border border-white/10 rounded-xl p-4 font-mono text-xs text-[#94A3B8] whitespace-pre-wrap overflow-y-auto">
        {storyContent}
      </div>

      <button 
        onClick={copyToClipboard}
        className={`flex items-center justify-center gap-2 p-3 rounded-xl font-bold transition-all ${
          copied 
            ? "bg-[#fcd34d] text-black shadow-[0_0_20px_rgba(252,211,77,0.5)]" 
            : "bg-white text-black hover:bg-gray-200"
        }`}
      >
        {copied ? (
          <>
            <CheckCircle className="h-5 w-5" /> Copied to Clipboard
          </>
        ) : (
          <>
            <Copy className="h-5 w-5" /> Copy Flex Text
          </>
        )}
      </button>
    </div>
  );
}
