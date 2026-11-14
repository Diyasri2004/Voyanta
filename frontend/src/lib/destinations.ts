/**
 * Well-known destinations the hero globe can fly to.
 * Used only for the hero's visual fly-to; trip planning itself is unaffected.
 */
export interface Destination {
  name: string;
  country: string;
  lat: number;
  lng: number;
}

export const DESTINATIONS: Destination[] = [
  { name: "Kyoto", country: "Japan", lat: 35.01, lng: 135.77 },
  { name: "Tokyo", country: "Japan", lat: 35.68, lng: 139.69 },
  { name: "Osaka", country: "Japan", lat: 34.69, lng: 135.5 },
  { name: "Lisbon", country: "Portugal", lat: 38.72, lng: -9.14 },
  { name: "Paris", country: "France", lat: 48.85, lng: 2.35 },
  { name: "London", country: "United Kingdom", lat: 51.51, lng: -0.13 },
  { name: "Rome", country: "Italy", lat: 41.9, lng: 12.5 },
  { name: "Venice", country: "Italy", lat: 45.44, lng: 12.33 },
  { name: "Barcelona", country: "Spain", lat: 41.39, lng: 2.17 },
  { name: "Madrid", country: "Spain", lat: 40.42, lng: -3.7 },
  { name: "Amsterdam", country: "Netherlands", lat: 52.37, lng: 4.9 },
  { name: "Prague", country: "Czechia", lat: 50.08, lng: 14.44 },
  { name: "Vienna", country: "Austria", lat: 48.21, lng: 16.37 },
  { name: "Istanbul", country: "Türkiye", lat: 41.01, lng: 28.98 },
  { name: "Athens", country: "Greece", lat: 37.98, lng: 23.73 },
  { name: "Santorini", country: "Greece", lat: 36.39, lng: 25.46 },
  { name: "Reykjavik", country: "Iceland", lat: 64.15, lng: -21.94 },
  { name: "Dubai", country: "United Arab Emirates", lat: 25.2, lng: 55.27 },
  { name: "Abu Dhabi", country: "United Arab Emirates", lat: 24.45, lng: 54.38 },
  { name: "Marrakech", country: "Morocco", lat: 31.63, lng: -8.0 },
  { name: "Cairo", country: "Egypt", lat: 30.04, lng: 31.24 },
  { name: "Cape Town", country: "South Africa", lat: -33.92, lng: 18.42 },
  { name: "Nairobi", country: "Kenya", lat: -1.29, lng: 36.82 },
  { name: "Zanzibar", country: "Tanzania", lat: -6.16, lng: 39.2 },
  { name: "Delhi", country: "India", lat: 28.61, lng: 77.21 },
  { name: "Mumbai", country: "India", lat: 19.08, lng: 72.88 },
  { name: "Goa", country: "India", lat: 15.5, lng: 73.83 },
  { name: "Jaipur", country: "India", lat: 26.91, lng: 75.79 },
  { name: "Lucknow", country: "India", lat: 26.85, lng: 80.95 },
  { name: "Varanasi", country: "India", lat: 25.32, lng: 82.97 },
  { name: "Chennai", country: "India", lat: 13.08, lng: 80.27 },
  { name: "Bengaluru", country: "India", lat: 12.97, lng: 77.59 },
  { name: "Kolkata", country: "India", lat: 22.57, lng: 88.36 },
  { name: "Kathmandu", country: "Nepal", lat: 27.72, lng: 85.32 },
  { name: "Maldives", country: "Maldives", lat: 4.18, lng: 73.51 },
  { name: "Colombo", country: "Sri Lanka", lat: 6.93, lng: 79.86 },
  { name: "Bangkok", country: "Thailand", lat: 13.76, lng: 100.5 },
  { name: "Phuket", country: "Thailand", lat: 7.88, lng: 98.39 },
  { name: "Singapore", country: "Singapore", lat: 1.35, lng: 103.82 },
  { name: "Bali", country: "Indonesia", lat: -8.41, lng: 115.19 },
  { name: "Hanoi", country: "Vietnam", lat: 21.03, lng: 105.85 },
  { name: "Seoul", country: "South Korea", lat: 37.57, lng: 126.98 },
  { name: "Hong Kong", country: "China", lat: 22.32, lng: 114.17 },
  { name: "Sydney", country: "Australia", lat: -33.87, lng: 151.21 },
  { name: "Queenstown", country: "New Zealand", lat: -45.03, lng: 168.66 },
  { name: "New York", country: "United States", lat: 40.71, lng: -74.0 },
  { name: "San Francisco", country: "United States", lat: 37.77, lng: -122.42 },
  { name: "Los Angeles", country: "United States", lat: 34.05, lng: -118.24 },
  { name: "Mexico City", country: "Mexico", lat: 19.43, lng: -99.13 },
  { name: "Havana", country: "Cuba", lat: 23.11, lng: -82.37 },
  { name: "Rio de Janeiro", country: "Brazil", lat: -22.91, lng: -43.17 },
  { name: "Buenos Aires", country: "Argentina", lat: -34.6, lng: -58.38 },
  { name: "Cusco", country: "Peru", lat: -13.53, lng: -71.97 },
  { name: "Vancouver", country: "Canada", lat: 49.28, lng: -123.12 },
];

/** Curated order for the hero's idle world tour. */
export const TOUR: string[] = [
  "Kyoto",
  "Lisbon",
  "Marrakech",
  "Reykjavik",
  "Cape Town",
  "Dubai",
  "Bali",
  "Rio de Janeiro",
  "New York",
  "Sydney",
];

const norm = (s: string) =>
  s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .trim();

/** Match free text ("Kyoto, Japan", "kyo") to a known destination. */
export function findDestination(query: string): Destination | null {
  const q = norm(query.split(",")[0] ?? "");
  if (q.length < 2) return null;
  const exact = DESTINATIONS.find((d) => norm(d.name) === q);
  if (exact) return exact;
  const starts = DESTINATIONS.find((d) => norm(d.name).startsWith(q));
  if (starts) return starts;
  return null;
}

export function getDestination(name: string): Destination | undefined {
  return DESTINATIONS.find((d) => d.name === name);
}

export function formatCoords(lat: number, lng: number) {
  const ns = lat >= 0 ? "N" : "S";
  const ew = lng >= 0 ? "E" : "W";
  return `${Math.abs(lat).toFixed(2)}°${ns}  ${Math.abs(lng).toFixed(2)}°${ew}`;
}
