import { NextRequest, NextResponse } from "next/server";

function unique(values: Array<string | undefined>) {
  return [...new Set(values.filter((value): value is string => Boolean(value)))];
}

const backendCandidates = unique([
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, ""),
  process.env.VOYANTA_BACKEND_URL?.replace(/\/$/, ""),
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, ""),
  "http://127.0.0.1:8000",
  "http://localhost:8000",
]);

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q") || "";
  const query = q.trim().toLowerCase();

  if (!query) {
    return NextResponse.json({ suggestions: [] });
  }

  // 1. Try FastAPI backend first
  for (const backendBaseUrl of backendCandidates) {
    try {
      const response = await fetch(`${backendBaseUrl}/api/autocomplete?q=${encodeURIComponent(query)}`, {
        cache: "no-store",
      });
      if (response.ok) {
        const data = await response.json();
        return NextResponse.json(data);
      }
    } catch {
      // Continue to fallback
    }
  }

  // 2. Direct Fallback via TomTom & Nominatim if backend is unreachable
  const suggestions: Array<{ label: string; value: string }> = [];
  const seen = new Set<string>();
  const tomtomKey = process.env.TOMTOM_API_KEY || process.env.NEXT_PUBLIC_TOMTOM_API_KEY;

  if (tomtomKey) {
    try {
      const url = `https://api.tomtom.com/search/2/search/${encodeURIComponent(query)}.json?key=${tomtomKey}&typehead=true&limit=20&idxSet=Geo,PAD,Addr`;
      const res = await fetch(url, { next: { revalidate: 3600 } });
      if (res.ok) {
        const data = await res.json();
        for (const result of data.results || []) {
          const address = result.address || {};
          const city = address.municipality || address.freeformAddress || result.poi?.name;
          const country = address.country;
          if (city && country) {
            const cleanCity = city.trim();
            if (cleanCity.toLowerCase().startsWith(query)) {
              const label = `${cleanCity}, ${country.trim()}`;
              if (!seen.has(label.toLowerCase())) {
                suggestions.push({ label, value: label });
                seen.add(label.toLowerCase());
              }
            }
          }
        }
      }
    } catch (e) {
      console.warn("Frontend TomTom fallback failed:", e);
    }
  }

  if (suggestions.length < 6) {
    try {
      const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&addressdetails=1&limit=20`;
      const res = await fetch(url, {
        headers: { "User-Agent": "VoyantaTravelEngine/1.0" },
      });
      if (res.ok) {
        const data = await res.json();
        for (const item of data) {
          const displayName = item.display_name || "";
          const parts = displayName.split(",").map((p: string) => p.trim());
          const mainPlace = parts[0];
          if (mainPlace.toLowerCase().startsWith(query)) {
            const country = parts.length > 1 ? parts[parts.length - 1] : "";
            const label = country ? `${mainPlace}, ${country}` : mainPlace;
            if (!seen.has(label.toLowerCase())) {
              suggestions.push({ label, value: label });
              seen.add(label.toLowerCase());
            }
          }
        }
      }
    } catch (e) {
      console.error("Frontend Nominatim fallback failed:", e);
    }
  }

  return NextResponse.json({ suggestions: suggestions.slice(0, 6) });
}
