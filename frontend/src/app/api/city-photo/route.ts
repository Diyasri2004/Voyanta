import { NextRequest, NextResponse } from "next/server";

const PEXELS_API_KEY = process.env.PEXELS_API_KEY ?? "";

const FALLBACK_IMAGE = "";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const city = searchParams.get("city")?.trim();

  if (!city) {
    return NextResponse.json(
      { url: FALLBACK_IMAGE, photographer: "", photographerUrl: "" },
      { status: 200 }
    );
  }

  if (!PEXELS_API_KEY) {
    console.error("PEXELS_API_KEY is not set.");
    return NextResponse.json(
      { url: FALLBACK_IMAGE, photographer: "", photographerUrl: "", fallback: true },
      { status: 200 }
    );
  }

  try {
    const query = encodeURIComponent(`${city} city landmark`);
    const pexelsRes = await fetch(
      `https://api.pexels.com/v1/search?query=${query}&per_page=1&orientation=landscape`,
      {
        headers: { Authorization: PEXELS_API_KEY },
        next: { revalidate: 3600 }, // cache 1 hour per city
      }
    );

    if (!pexelsRes.ok) {
      console.error(`Pexels API error: ${pexelsRes.status}`);
      return NextResponse.json(
        { url: FALLBACK_IMAGE, photographer: "", photographerUrl: "", fallback: true },
        { status: 200 }
      );
    }

    const data = await pexelsRes.json();
    const photo = data?.photos?.[0];

    if (!photo) {
      return NextResponse.json(
        { url: FALLBACK_IMAGE, photographer: "", photographerUrl: "", fallback: true },
        { status: 200 }
      );
    }

    return NextResponse.json(
      {
        url: photo.src?.landscape ?? photo.src?.large ?? FALLBACK_IMAGE,
        photographer: photo.photographer ?? "",
        photographerUrl: photo.photographer_url ?? "https://www.pexels.com",
        pexelsUrl: photo.url ?? "https://www.pexels.com",
        fallback: false,
      },
      { status: 200 }
    );
  } catch (err) {
    console.error("Failed to fetch from Pexels:", err);
    return NextResponse.json(
      { url: FALLBACK_IMAGE, photographer: "", photographerUrl: "", fallback: true },
      { status: 200 }
    );
  }
}
