"use client";

import { useEffect, useState } from "react";
import { getCityPhoto, CityPhotoResult } from "@/utils/getCityPhoto";

interface CityHeroImageProps {
  city: string;
  className?: string;
}

const FALLBACK_URL =
  "https://images.pexels.com/photos/1483769/pexels-photo-1483769.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2";

export default function CityHeroImage({ city, className = "" }: CityHeroImageProps) {
  const [photo, setPhoto] = useState<CityPhotoResult | null>(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    if (!city) return;

    let cancelled = false;
    setFetching(true);
    setImageLoaded(false);
    setPhoto(null);

    getCityPhoto(city).then((result) => {
      if (!cancelled) {
        setPhoto(result);
        setFetching(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [city]);

  const showSkeleton = fetching || !imageLoaded;

  return (
    <div className={`relative overflow-hidden ${className}`}>
      {/* Skeleton shimmer */}
      {showSkeleton && (
        <div
          className="absolute inset-0 z-10"
          style={{
            background:
              "linear-gradient(110deg, #0d1117 30%, #1a2030 50%, #0d1117 70%)",
            backgroundSize: "200% 100%",
            animation: "shimmer 1.6s infinite linear",
          }}
        >
          <style>{`
            @keyframes shimmer {
              0%   { background-position: 200% 0; }
              100% { background-position: -200% 0; }
            }
          `}</style>
          {/* Subtle destination icon in skeleton */}
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 opacity-30">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="40"
              height="40"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-slate-400"
            >
              <path d="M12 22s-8-4.5-8-11.8A8 8 0 0 1 12 2a8 8 0 0 1 8 8.2c0 7.3-8 11.8-8 11.8z" />
              <circle cx="12" cy="10" r="3" />
            </svg>
            <span className="text-xs text-slate-400 tracking-[0.2em] uppercase font-semibold">
              Loading photo…
            </span>
          </div>
        </div>
      )}

      {/* Actual photo */}
      {photo && (
        <>
          <img
            src={photo.url}
            alt={`${city} landmark`}
            onLoad={() => setImageLoaded(true)}
            onError={() => {
              setPhoto({ ...photo, url: FALLBACK_URL });
              setImageLoaded(true);
            }}
            className="h-full w-full object-cover transition-opacity duration-700"
            style={{ opacity: imageLoaded ? 1 : 0 }}
          />

          {/* Gradient overlay */}
          <div className="absolute inset-0 bg-gradient-to-t from-[#07090E]/80 via-[#07090E]/20 to-transparent pointer-events-none" />

          {/* Pexels attribution – required by their API guidelines */}
          {imageLoaded && !photo.fallback && photo.photographer && (
            <a
              href={photo.pexelsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="absolute bottom-3 right-3 z-20 flex items-center gap-1.5 rounded-full bg-black/40 px-3 py-1.5 backdrop-blur-md transition hover:bg-black/60"
              title={`Photo by ${photo.photographer} on Pexels`}
            >
              {/* Pexels logo mark */}
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 32 32"
                fill="white"
                aria-label="Pexels"
              >
                <path d="M2 0h28a2 2 0 0 1 2 2v28a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2zm10.676 6.9H8v18.2h4.371v-5.837h3.274c3.676 0 6.197-2.46 6.197-6.18C21.842 9.36 19.32 6.9 15.644 6.9h-2.968zm.204 3.674h2.383c1.707 0 2.783 1.015 2.783 2.603 0 1.588-1.076 2.603-2.783 2.603h-2.383V10.574z" />
              </svg>
              <span className="text-[10px] font-semibold text-white/90 tracking-wide">
                {photo.photographer}
              </span>
            </a>
          )}
        </>
      )}
    </div>
  );
}
