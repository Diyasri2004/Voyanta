import { NextRequest, NextResponse } from "next/server";

function unique(values: Array<string | undefined>) {
  return [...new Set(values.filter((value): value is string => Boolean(value)))];
}

const backendCandidates = unique([
  process.env.VOYANTA_BACKEND_URL?.replace(/\/$/, ""),
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, ""),
  "http://127.0.0.1:8005",
  "http://127.0.0.1:8004",
  "http://127.0.0.1:8003",
  "http://127.0.0.1:8002",
  "http://127.0.0.1:8001",
  "http://127.0.0.1:8000",
]);

export async function POST(request: NextRequest) {
  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid request body." }, { status: 400 });
  }

  let lastStatus = 503;
  let lastDetail =
    "Voyanta backend is unreachable. Start the FastAPI server or set VOYANTA_BACKEND_URL.";

  for (const backendBaseUrl of backendCandidates) {
    try {
      const response = await fetch(`${backendBaseUrl}/trip-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        cache: "no-store",
      });

      const text = await response.text();
      let payload: unknown = null;

      if (text) {
        try {
          payload = JSON.parse(text);
        } catch {
          payload = { detail: text };
        }
      }

      const detail =
        payload && typeof payload === "object" && "detail" in payload
          ? String(payload.detail)
          : null;

      if (response.status === 404) {
        lastStatus = response.status;
        lastDetail = detail ?? `Trip endpoint was not found on ${backendBaseUrl}.`;
        continue;
      }

      if (!response.ok) {
        return NextResponse.json(
          {
            detail:
              detail ?? `Backend request failed with status ${response.status}.`,
          },
          { status: response.status }
        );
      }

      return NextResponse.json(payload, { status: 200 });
    } catch {
      lastStatus = 503;
      lastDetail = `Could not reach backend at ${backendBaseUrl}.`;
    }
  }

  return NextResponse.json({ detail: lastDetail }, { status: lastStatus });
}
