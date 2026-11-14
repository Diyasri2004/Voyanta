/**
 * Builds the Earth geometry from real Natural Earth data (public domain,
 * via the `world-atlas` package): land dots, city lights, country borders.
 * Everything is generated in the browser — no texture downloads.
 */
import * as THREE from "three";
import { feature, mesh } from "topojson-client";
import worldTopology from "world-atlas/countries-110m.json";

export const R = 2; // globe radius in scene units

/** lat/lng (degrees) → point on a sphere of radius r. */
export function latLng(lat: number, lng: number, r = R, out = new THREE.Vector3()) {
  const phi = ((90 - lat) * Math.PI) / 180;
  const theta = ((lng + 180) * Math.PI) / 180;
  return out.set(-r * Math.sin(phi) * Math.cos(theta), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(theta));
}

/* Major urban areas [lat, lng, weight 1–5] — drives where the night lights cluster. */
const CITIES: Array<[number, number, number]> = [
  // North & Central America
  [40.7, -74, 5], [34, -118.2, 5], [41.9, -87.6, 4], [29.8, -95.4, 3], [32.8, -96.8, 3], [25.8, -80.2, 3],
  [33.7, -84.4, 3], [38.9, -77, 3], [42.4, -71.1, 3], [37.8, -122.4, 3], [47.6, -122.3, 2], [39.7, -105, 2],
  [33.4, -112.1, 2], [43.7, -79.4, 3], [45.5, -73.6, 2], [49.3, -123.1, 2], [19.4, -99.1, 5], [20.7, -103.3, 2],
  [25.7, -100.3, 2], [23.1, -82.4, 2], [9, -79.5, 1],
  // South America
  [4.7, -74.1, 3], [-12, -77, 3], [-33.4, -70.7, 3], [-34.6, -58.4, 4], [-23.5, -46.6, 5], [-22.9, -43.2, 4],
  [-15.8, -47.9, 2], [-13, -38.5, 2], [10.5, -66.9, 2], [-0.2, -78.5, 1], [-3.7, -38.5, 2], [-3.1, -60, 1],
  // Europe
  [51.5, -0.1, 5], [48.9, 2.4, 5], [40.4, -3.7, 3], [41.4, 2.2, 3], [38.7, -9.1, 2], [41.9, 12.5, 3],
  [45.5, 9.2, 3], [52.5, 13.4, 3], [48.1, 11.6, 2], [52.4, 4.9, 3], [50.8, 4.4, 2], [48.2, 16.4, 2],
  [50.1, 14.4, 2], [52.2, 21, 3], [47.5, 19.1, 2], [59.3, 18.1, 2], [55.7, 12.6, 2], [59.9, 10.8, 1],
  [60.2, 24.9, 1], [38, 23.7, 2], [41, 29, 5], [55.8, 37.6, 5], [59.9, 30.3, 3], [50.5, 30.5, 3],
  [44.4, 26.1, 2], [53.3, -6.3, 1], [53.5, -2.2, 2], [50.1, 8.7, 2], [47.4, 8.5, 1],
  // Africa & Middle East
  [30, 31.2, 5], [6.5, 3.4, 5], [-4.3, 15.3, 3], [-26.2, 28, 4], [-33.9, 18.4, 2], [-1.3, 36.8, 3],
  [9, 38.7, 3], [33.6, -7.6, 3], [36.8, 3.1, 3], [36.8, 10.2, 2], [5.6, -0.2, 2], [14.7, -17.5, 2],
  [-6.8, 39.3, 2], [-8.8, 13.2, 2], [15.5, 32.5, 2], [24.7, 46.7, 4], [21.5, 39.2, 3], [25.2, 55.3, 4],
  [35.7, 51.4, 4], [33.3, 44.4, 3], [32.1, 34.8, 3], [25.3, 51.5, 2], [29.4, 48, 2],
  // Asia
  [28.6, 77.2, 5], [19.1, 72.9, 5], [22.6, 88.4, 4], [13.1, 80.3, 3], [13, 77.6, 4], [17.4, 78.5, 3],
  [23, 72.6, 3], [18.5, 73.9, 2], [26.8, 80.9, 2], [26.9, 75.8, 2], [24.9, 67, 4], [31.5, 74.3, 4],
  [23.8, 90.4, 5], [27.7, 85.3, 1], [6.9, 79.9, 2], [13.8, 100.5, 4], [21, 105.8, 3], [10.8, 106.7, 4],
  [-6.2, 106.8, 5], [-7.3, 112.7, 2], [14.6, 121, 4], [3.1, 101.7, 3], [1.35, 103.8, 3], [16.8, 96.2, 2],
  [39.9, 116.4, 5], [31.2, 121.5, 5], [23.1, 113.3, 4], [22.5, 114.1, 4], [30.7, 104.1, 3], [29.6, 106.5, 3],
  [30.6, 114.3, 3], [34.3, 108.9, 2], [22.3, 114.2, 3], [25, 121.5, 3], [37.6, 127, 5], [35.2, 129, 2],
  [35.7, 139.7, 5], [34.7, 135.5, 4], [35.2, 136.9, 3], [43.1, 141.4, 1], [41.3, 69.3, 2], [43.2, 76.9, 1],
  [55, 82.9, 1],
  // Oceania
  [-33.9, 151.2, 3], [-37.8, 145, 3], [-27.5, 153, 2], [-32, 115.9, 2], [-36.8, 174.8, 2],
];

export interface EarthData {
  landPositions: Float32Array;
  landSeeds: Float32Array;
  lightPositions: Float32Array;
  lightSeeds: Float32Array;
  borderPositions: Float32Array;
}

/** Seeded PRNG so the globe looks identical on every load. */
function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function buildLandMask() {
  const W = 2048;
  const H = 1024;
  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = "#fff";

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const topo = worldTopology as any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const land: any = feature(topo, topo.objects.land);
  const features = land.type === "FeatureCollection" ? land.features : [land];

  const x = (lng: number) => ((lng + 180) / 360) * W;
  const y = (lat: number) => ((90 - lat) / 180) * H;

  for (const f of features) {
    const g = f.geometry;
    const polys: number[][][][] = g.type === "Polygon" ? [g.coordinates] : g.coordinates;
    for (const poly of polys) {
      ctx.beginPath();
      for (const ring of poly) {
        ring.forEach(([lng, lat]: number[], i: number) => {
          if (i === 0) ctx.moveTo(x(lng), y(lat));
          else ctx.lineTo(x(lng), y(lat));
        });
        ctx.closePath();
      }
      ctx.fill("evenodd");
    }
  }

  const data = ctx.getImageData(0, 0, W, H).data;
  return (lat: number, lng: number) => {
    const px = Math.min(W - 1, Math.max(0, Math.floor(((lng + 180) / 360) * W)));
    const py = Math.min(H - 1, Math.max(0, Math.floor(((90 - lat) / 180) * H)));
    return data[(py * W + px) * 4] > 127;
  };
}

function buildBorders(): Float32Array {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const topo = worldTopology as any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const borders: any = mesh(topo, topo.objects.countries, (a: unknown, b: unknown) => a !== b);
  const lines: number[][][] = borders.type === "MultiLineString" ? borders.coordinates : [borders.coordinates];
  const out: number[] = [];
  const a = new THREE.Vector3();
  const b = new THREE.Vector3();
  const STEP = 1.2; // degrees — keeps segments hugging the curved surface

  for (const line of lines) {
    for (let i = 0; i < line.length - 1; i++) {
      const [lng1, lat1] = line[i];
      const [lng2, lat2] = line[i + 1];
      if (Math.abs(lng2 - lng1) > 180) continue; // skip antimeridian wraps
      if (lat1 < -60 && lat2 < -60) continue;
      const n = Math.max(1, Math.ceil(Math.max(Math.abs(lng2 - lng1), Math.abs(lat2 - lat1)) / STEP));
      for (let k = 0; k < n; k++) {
        latLng(lat1 + ((lat2 - lat1) * k) / n, lng1 + ((lng2 - lng1) * k) / n, R * 1.0015, a);
        latLng(lat1 + ((lat2 - lat1) * (k + 1)) / n, lng1 + ((lng2 - lng1) * (k + 1)) / n, R * 1.0015, b);
        out.push(a.x, a.y, a.z, b.x, b.y, b.z);
      }
    }
  }
  return new Float32Array(out);
}

export function buildEarth(): EarthData {
  const isLand = buildLandMask();
  const rand = mulberry32(1337);

  // 1 ─ land dots on a Fibonacci lattice, kept only where the mask says "land"
  const N = 52000;
  const golden = Math.PI * (3 - Math.sqrt(5));
  const land: number[] = [];
  const landSeeds: number[] = [];
  const v = new THREE.Vector3();
  for (let i = 0; i < N; i++) {
    const y = 1 - (i / (N - 1)) * 2;
    const lat = (Math.asin(y) * 180) / Math.PI;
    if (lat < -58) continue; // skip Antarctica clutter
    const th = golden * i;
    const rad = Math.sqrt(1 - y * y);
    const x = Math.cos(th) * rad;
    const z = Math.sin(th) * rad;
    // inverse of latLng(): recover longitude so the mask lines up with the globe
    const lng0 = (Math.atan2(z, -x) * 180) / Math.PI - 180;
    const lng = ((lng0 + 540) % 360) - 180;
    if (!isLand(lat, lng)) continue;
    v.set(x, y, z).multiplyScalar(R);
    land.push(v.x, v.y, v.z);
    landSeeds.push(rand());
  }

  // 2 ─ night lights: scatter points around real city centres, on land only
  const lights: number[] = [];
  const lightSeeds: number[] = [];
  for (const [clat, clng, w] of CITIES) {
    const count = 26 + w * 34;
    const sigma = 0.35 + w * 0.32; // degrees
    for (let k = 0; k < count; k++) {
      // Box–Muller gaussian scatter
      const u1 = Math.max(rand(), 1e-6);
      const g1 = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * rand());
      const g2 = Math.sqrt(-2 * Math.log(u1)) * Math.sin(2 * Math.PI * rand());
      const lat = clat + g1 * sigma;
      const lng = clng + (g2 * sigma) / Math.max(0.35, Math.cos((clat * Math.PI) / 180));
      if (!isLand(lat, lng)) continue;
      latLng(lat, lng, R * 1.002, v);
      lights.push(v.x, v.y, v.z);
      lightSeeds.push(rand());
    }
  }

  return {
    landPositions: new Float32Array(land),
    landSeeds: new Float32Array(landSeeds),
    lightPositions: new Float32Array(lights),
    lightSeeds: new Float32Array(lightSeeds),
    borderPositions: buildBorders(),
  };
}
