"use client";

export interface MapWaypoint {
  id: string;
  lat: number;
  lng: number;
  title?: string;
  location?: string;
}

interface VoyantaMapProps {
  waypoints: MapWaypoint[];
  mapImageUrl?: string;
}

export default function VoyantaMap({ waypoints, mapImageUrl }: VoyantaMapProps) {
  function openNavigation(waypoint: MapWaypoint) {
    const destination = encodeURIComponent(`${waypoint.lat},${waypoint.lng}`);
    window.open(
      `https://www.google.com/maps/dir/?api=1&destination=${destination}`,
      "_blank",
      "noopener,noreferrer"
    );
  }

  return (
    <div className="relative h-full w-full overflow-hidden rounded-[2rem] border border-white/[0.08] bg-[#0E1525]">
      {mapImageUrl ? (
        <img
          src={mapImageUrl}
          alt="TomTom map preview"
          className="absolute inset-0 h-full w-full object-cover"
        />
      ) : (
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f293d_1px,transparent_1px),linear-gradient(to_bottom,#1f293d_1px,transparent_1px)] bg-[size:4rem_4rem] opacity-40" />
      )}

      <div className="absolute inset-0 bg-gradient-to-t from-[#05070A] via-[#05070A]/25 to-transparent" />

      <div className="absolute inset-x-0 bottom-6 z-10 flex flex-col items-center gap-3 px-4">
        <div className="rounded-2xl border border-white/[0.10] bg-[#0A0D14]/85 px-5 py-4 text-center shadow-2xl backdrop-blur-xl">
          <p className="text-sm font-semibold text-white">TomTom Map Preview</p>
          <p className="mt-1 text-xs text-[#94A3B8]">
            Tap a stop below to open navigation.
          </p>
        </div>

        <div className="flex flex-wrap justify-center gap-3">
          {waypoints.map((waypoint, index) => (
            <button
              key={waypoint.id}
              type="button"
              onClick={() => openNavigation(waypoint)}
              className="flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.08] px-3 py-2 text-xs font-semibold text-white backdrop-blur-md transition hover:bg-white/[0.14]"
              title={`Navigate to ${waypoint.title ?? `stop ${index + 1}`}`}
            >
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white text-[11px] font-bold text-[#05070A]">
                {index + 1}
              </span>
              <span className="max-w-[10rem] truncate">
                {waypoint.title ?? `Stop ${index + 1}`}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
