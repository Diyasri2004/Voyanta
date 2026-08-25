export interface CityPhotoResult {
  url: string;
  photographer: string;
  photographerUrl: string;
  pexelsUrl: string;
  fallback: boolean;
}

const FALLBACK: CityPhotoResult = {
  url: "",
  photographer: "",
  photographerUrl: "https://www.pexels.com",
  pexelsUrl: "https://www.pexels.com",
  fallback: true,
};

/**
 * Fetches a city/landmark photo from Pexels via the server-side Next.js API route.
 * The API key is never exposed to the browser.
 */
export async function getCityPhoto(cityName: string): Promise<CityPhotoResult> {
  if (!cityName.trim()) return FALLBACK;

  try {
    const res = await fetch(
      `/api/city-photo?city=${encodeURIComponent(cityName)}`,
      { cache: "force-cache" }
    );

    if (!res.ok) return FALLBACK;

    const data = await res.json();
    return {
      url: data.url ?? FALLBACK.url,
      photographer: data.photographer ?? "",
      photographerUrl: data.photographerUrl ?? "https://www.pexels.com",
      pexelsUrl: data.pexelsUrl ?? "https://www.pexels.com",
      fallback: data.fallback ?? false,
    };
  } catch {
    return FALLBACK;
  }
}
