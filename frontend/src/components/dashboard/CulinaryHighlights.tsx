"use client";

import CulinaryCard, { CulinaryHighlightProps } from "./CulinaryCard";

export default function CulinaryHighlights({
  highlights = [],
  destination,
}: {
  highlights: CulinaryHighlightProps[];
  destination: string;
}) {
  if (!highlights || highlights.length === 0) return null;

  return (
    <section className="mt-8 pt-8 border-t border-white/10 shrink-0">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <p className="text-[11px] uppercase tracking-[0.28em] text-[#ff007f] font-bold">
            Local Flavour
          </p>
          <h2 className="mt-1 text-2xl font-syne font-bold tracking-tight text-white">
            Must-Try Culinary Highlights
          </h2>
        </div>
      </div>
      <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-4 pb-12">
        {highlights.map((highlight: any, idx: number) => (
          <CulinaryCard key={idx} highlight={highlight} destination={destination} />
        ))}
      </div>
    </section>
  );
}
