"use client";

import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// Fix standard Leaflet icon paths in Next.js
const customIcon = new L.Icon({
  iconUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41]
});

export default function LeafletMap({ trip }: { trip: any }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return <div className="h-full w-full bg-cyber-dark"></div>;

  const center: [number, number] = trip?.coordinates ? [trip.coordinates.lat, trip.coordinates.lng] : [20, 0];
  const stops = trip?.itinerary || [];
  const coords: [number, number][] = stops.map((s: any) => [s.lat, s.lng]);

  return (
    <MapContainer center={center} zoom={12} className="h-full w-full bg-[#0a0a0a]" zoomControl={false}>
      {/* Dark theme tile layer */}
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://carto.com/">CARTO</a>'
      />
      
      {stops.map((stop: any, idx: number) => (
        <Marker key={idx} position={[stop.lat, stop.lng]} icon={customIcon}>
          <Popup className="font-plus-jakarta bg-[#03050a] text-[#00f0ff] border border-[#00f0ff]">
            <strong className="text-[#39ff14]">{stop.title}</strong><br />
            {stop.time} - {stop.location}
          </Popup>
        </Marker>
      ))}

      {coords.length > 1 && (
        <Polyline positions={coords} color="#ff007f" weight={3} dashArray="5, 10" />
      )}
    </MapContainer>
  );
}
