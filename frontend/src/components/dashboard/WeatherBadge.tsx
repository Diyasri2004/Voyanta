"use client";

import { useEffect, useState } from "react";

interface WeatherData {
  temp_c: number;
  feels_like_c?: number;
  condition: string;
  emoji: string;
  humidity?: number;
  daily?: Array<{ date: string; max_c: number; min_c: number; condition: string; emoji: string }>;
}

interface WeatherBadgeProps {
  destination: string;
  startDate?: string;
  endDate?: string;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export default function WeatherBadge({ destination, startDate, endDate }: WeatherBadgeProps) {
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [showTooltip, setShowTooltip] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!destination) return;
    const controller = new AbortController();
    setLoading(true);
    const params = new URLSearchParams({ destination });
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);

    fetch(`${BACKEND_URL}/api/weather?${params.toString()}`, { signal: controller.signal })
      .then((r) => r.json())
      .then((d) => { setWeather(d); setLoading(false); })
      .catch((e) => { if (e.name !== "AbortError") setLoading(false); });

    return () => controller.abort();
  }, [destination, startDate, endDate]);

  if (!destination || loading) {
    return (
      <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs font-mono text-gray-500 animate-pulse">
        <span>🌡️</span>
        <span>Weather...</span>
      </div>
    );
  }

  if (!weather) return null;

  const hasDailyBreakdown = weather.daily && weather.daily.length > 0;

  return (
    <div className="relative">
      <button
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-sky-500/10 border border-sky-500/30 text-xs font-mono text-sky-300 hover:bg-sky-500/20 transition-all shadow-sm cursor-default select-none"
        title={`${weather.emoji} ${weather.temp_c}°C — ${weather.condition}`}
      >
        <span className="text-sm">{weather.emoji}</span>
        <span className="font-bold text-white">{weather.temp_c}°C</span>
        <span className="text-sky-400 hidden sm:block">{weather.condition}</span>
      </button>

      {/* Hover Tooltip */}
      {showTooltip && (
        <div className="absolute right-0 top-10 z-50 w-64 rounded-2xl border border-white/10 bg-[#080c16] shadow-2xl p-4 text-xs space-y-2 animate-fade-in">
          <div className="flex items-center justify-between border-b border-white/10 pb-2">
            <span className="font-bold text-white">{destination}</span>
            <span className="text-sky-400">{weather.emoji} {weather.temp_c}°C</span>
          </div>
          {weather.feels_like_c !== undefined && (
            <div className="flex justify-between text-gray-400">
              <span>Feels Like</span>
              <span className="text-white">{weather.feels_like_c}°C</span>
            </div>
          )}
          {weather.humidity !== undefined && (
            <div className="flex justify-between text-gray-400">
              <span>Humidity</span>
              <span className="text-white">{weather.humidity}%</span>
            </div>
          )}
          {hasDailyBreakdown && (
            <>
              <div className="border-t border-white/10 pt-2 font-semibold text-gray-300">Daily Forecast</div>
              {weather.daily!.map((day) => (
                <div key={day.date} className="flex items-center justify-between text-gray-400">
                  <span className="text-white">
                    {new Date(day.date).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                  </span>
                  <span>{day.emoji}</span>
                  <span className="text-sky-400">{day.min_c}° – {day.max_c}°C</span>
                </div>
              ))}
            </>
          )}
          <div className="text-[10px] text-gray-600 pt-1">Powered by Open-Meteo · Free</div>
        </div>
      )}
    </div>
  );
}
