"use client";

/**
 * TravelScene — the Voyanta hero world.
 * A stylised dotted globe, glowing flight arcs, planes with comet trails,
 * pulsing city beacons, orbit rings and a starfield. Pure Three.js via
 * react-three-fiber; no texture downloads required.
 */

import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Line, Stars } from "@react-three/drei";
import * as THREE from "three";

const R = 2; // globe radius

/* ── geo helpers ─────────────────────────────────────────────── */

function latLng(lat: number, lng: number, r = R) {
  const phi = ((90 - lat) * Math.PI) / 180;
  const theta = ((lng + 180) * Math.PI) / 180;
  return new THREE.Vector3(
    -r * Math.sin(phi) * Math.cos(theta),
    r * Math.cos(phi),
    r * Math.sin(phi) * Math.sin(theta)
  );
}

type City = { name: string; lat: number; lng: number };

const CITIES: Record<string, City> = {
  lko: { name: "Lucknow", lat: 26.85, lng: 80.95 },
  tyo: { name: "Tokyo", lat: 35.68, lng: 139.69 },
  par: { name: "Paris", lat: 48.85, lng: 2.35 },
  nyc: { name: "New York", lat: 40.71, lng: -74.0 },
  dxb: { name: "Dubai", lat: 25.2, lng: 55.27 },
  syd: { name: "Sydney", lat: -33.87, lng: 151.2 },
  cpt: { name: "Cape Town", lat: -33.92, lng: 18.42 },
  rio: { name: "Rio", lat: -22.9, lng: -43.17 },
  sin: { name: "Singapore", lat: 1.35, lng: 103.82 },
  sfo: { name: "San Francisco", lat: 37.77, lng: -122.42 },
};

const ROUTES: Array<[keyof typeof CITIES, keyof typeof CITIES]> = [
  ["lko", "par"],
  ["lko", "tyo"],
  ["nyc", "par"],
  ["dxb", "sin"],
  ["sin", "syd"],
  ["sfo", "tyo"],
  ["rio", "cpt"],
  ["nyc", "rio"],
  ["dxb", "cpt"],
  ["lko", "dxb"],
];

/* Rough continent blobs (centre lat/lng, half-extent lat/lng) */
const LAND: Array<[number, number, number, number]> = [
  [47, -100, 24, 42], // North America
  [-14, -60, 28, 17], // South America
  [51, 15, 11, 26], // Europe
  [6, 20, 33, 23], // Africa
  [46, 90, 26, 58], // Asia
  [22, 79, 10, 9], // India
  [10, 108, 12, 11], // SE Asia
  [-25, 134, 12, 20], // Australia
  [72, -40, 10, 18], // Greenland
  [36, 138, 7, 6], // Japan
];

function isLand(lat: number, lng: number) {
  // cheap deterministic roughness so edges aren't perfect ellipses
  const n =
    Math.sin(lat * 0.35) * Math.cos(lng * 0.27) +
    Math.sin(lat * 0.9 + lng * 0.4) * 0.5;
  for (const [clat, clng, rlat, rlng] of LAND) {
    let dl = Math.abs(lng - clng);
    if (dl > 180) dl = 360 - dl;
    const d = ((lat - clat) / rlat) ** 2 + (dl / rlng) ** 2;
    if (d < 1 + 0.32 * n) return true;
  }
  return false;
}

function dotTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d")!;
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, "rgba(255,255,255,1)");
  grad.addColorStop(0.45, "rgba(255,255,255,0.9)");
  grad.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 64);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

/* ── Globe (land dots + ocean dots + occluder + atmosphere) ──── */

function Globe({ sprite }: { sprite: THREE.Texture }) {
  const { land, ocean } = useMemo(() => {
    const N = 26000;
    const landPos: number[] = [];
    const landCol: number[] = [];
    const oceanPos: number[] = [];
    const golden = Math.PI * (3 - Math.sqrt(5));
    const a = new THREE.Color("#5eead4");
    const b = new THREE.Color("#818cf8");
    const c = new THREE.Color();
    for (let i = 0; i < N; i++) {
      const y = 1 - (i / (N - 1)) * 2;
      const rad = Math.sqrt(1 - y * y);
      const th = golden * i;
      const x = Math.cos(th) * rad;
      const z = Math.sin(th) * rad;
      const lat = (Math.asin(y) * 180) / Math.PI;
      // invert latLng() so land mask lines up with city placement
      const lng = (Math.atan2(z, -x) * 180) / Math.PI - 180;
      const lngN = ((lng + 540) % 360) - 180;
      const p = [x * R, y * R, z * R];
      if (isLand(lat, lngN)) {
        landPos.push(...p);
        c.copy(a).lerp(b, (Math.sin(lat * 0.05) + 1) / 2);
        landCol.push(c.r, c.g, c.b);
      } else if (i % 6 === 0) {
        oceanPos.push(...p);
      }
    }
    const landGeo = new THREE.BufferGeometry();
    landGeo.setAttribute("position", new THREE.Float32BufferAttribute(landPos, 3));
    landGeo.setAttribute("color", new THREE.Float32BufferAttribute(landCol, 3));
    const oceanGeo = new THREE.BufferGeometry();
    oceanGeo.setAttribute("position", new THREE.Float32BufferAttribute(oceanPos, 3));
    return { land: landGeo, ocean: oceanGeo };
  }, []);

  const atmosphere = useMemo(
    () =>
      new THREE.ShaderMaterial({
        transparent: true,
        side: THREE.BackSide,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        vertexShader: /* glsl */ `
          varying vec3 vN;
          void main() {
            vN = normalize(normalMatrix * normal);
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }`,
        fragmentShader: /* glsl */ `
          varying vec3 vN;
          void main() {
            float i = pow(0.68 - dot(vN, vec3(0.0, 0.0, 1.0)), 3.2);
            gl_FragColor = vec4(0.37, 0.92, 0.83, 1.0) * i * 0.65;
          }`,
      }),
    []
  );

  return (
    <group>
      {/* dark core hides the far-side dots */}
      <mesh>
        <sphereGeometry args={[R * 0.985, 64, 64]} />
        <meshBasicMaterial color="#050914" />
      </mesh>
      <points geometry={ocean}>
        <pointsMaterial
          map={sprite}
          size={0.016}
          color="#3b4a7a"
          transparent
          opacity={0.55}
          depthWrite={false}
          sizeAttenuation
        />
      </points>
      <points geometry={land}>
        <pointsMaterial
          map={sprite}
          size={0.04}
          vertexColors
          transparent
          opacity={0.95}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          sizeAttenuation
        />
      </points>
      <mesh scale={1.16} material={atmosphere}>
        <sphereGeometry args={[R, 64, 64]} />
      </mesh>
    </group>
  );
}

/* ── City beacon ─────────────────────────────────────────────── */

function Beacon({ city, phase }: { city: City; phase: number }) {
  const pos = useMemo(() => latLng(city.lat, city.lng, R * 1.004), [city]);
  const ring = useRef<THREE.Mesh>(null);

  useEffect(() => {
    ring.current?.lookAt(pos.clone().multiplyScalar(2));
  }, [pos]);

  useFrame(({ clock }) => {
    if (!ring.current) return;
    const t = (clock.elapsedTime * 0.6 + phase) % 1;
    ring.current.scale.setScalar(0.4 + t * 2.4);
    (ring.current.material as THREE.MeshBasicMaterial).opacity = (1 - t) * 0.8;
  });

  return (
    <group position={pos}>
      <mesh>
        <sphereGeometry args={[0.028, 16, 16]} />
        <meshBasicMaterial color="#fcd34d" />
      </mesh>
      <mesh ref={ring}>
        <ringGeometry args={[0.04, 0.052, 40]} />
        <meshBasicMaterial color="#fcd34d" transparent opacity={0.8} depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

/* ── Flight arc + plane with comet trail ─────────────────────── */

const TRAIL = 26;

function Flight({ from, to, offset, speed }: { from: City; to: City; offset: number; speed: number }) {
  const curve = useMemo(() => {
    const a = latLng(from.lat, from.lng, R * 1.004);
    const b = latLng(to.lat, to.lng, R * 1.004);
    const dist = a.distanceTo(b);
    const ctrl = a.clone().add(b).multiplyScalar(0.5).normalize().multiplyScalar(R + 0.25 + dist * 0.42);
    return new THREE.QuadraticBezierCurve3(a, ctrl, b);
  }, [from, to]);

  const arcPoints = useMemo(() => curve.getPoints(72), [curve]);

  const plane = useRef<THREE.Group>(null);
  const trail = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(TRAIL * 3), 3));
    const colors = new Float32Array(TRAIL * 3);
    const hot = new THREE.Color("#fcd34d");
    for (let i = 0; i < TRAIL; i++) {
      const k = 1 - i / (TRAIL - 1);
      colors[i * 3] = hot.r * k;
      colors[i * 3 + 1] = hot.g * k;
      colors[i * 3 + 2] = hot.b * k;
    }
    geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    const mat = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    return new THREE.Line(geo, mat);
  }, []);

  const tmp = useMemo(() => new THREE.Vector3(), []);
  const look = useMemo(() => new THREE.Vector3(), []);

  useFrame(({ clock }) => {
    const t = (clock.elapsedTime * speed + offset) % 1;
    const p = curve.getPoint(t);
    if (plane.current) {
      plane.current.position.copy(p);
      look.copy(p).add(curve.getTangent(t));
      plane.current.lookAt(look);
    }
    const attr = trail.geometry.getAttribute("position") as THREE.BufferAttribute;
    for (let i = 0; i < TRAIL; i++) {
      const tt = Math.max(0, t - i * 0.006);
      curve.getPoint(tt, tmp);
      attr.setXYZ(i, tmp.x, tmp.y, tmp.z);
    }
    attr.needsUpdate = true;
  });

  return (
    <group>
      <Line points={arcPoints} color="#5eead4" lineWidth={1} transparent opacity={0.28} />
      <primitive object={trail} />
      <group ref={plane}>
        {/* paper-plane: flattened 3-sided cone pointing along +Z */}
        <mesh rotation={[Math.PI / 2, 0, 0]} scale={[1.5, 1, 0.35]}>
          <coneGeometry args={[0.03, 0.12, 3]} />
          <meshBasicMaterial color="#fff7d6" />
        </mesh>
      </group>
    </group>
  );
}

/* ── Orbit rings ─────────────────────────────────────────────── */

function Rings() {
  const a = useRef<THREE.Mesh>(null);
  const b = useRef<THREE.Mesh>(null);
  useFrame((_, dt) => {
    if (a.current) a.current.rotation.z += dt * 0.08;
    if (b.current) b.current.rotation.z -= dt * 0.05;
  });
  return (
    <>
      <mesh ref={a} rotation={[Math.PI / 2.35, 0.25, 0]}>
        <torusGeometry args={[R * 1.42, 0.0045, 8, 220]} />
        <meshBasicMaterial color="#5eead4" transparent opacity={0.35} />
      </mesh>
      <mesh ref={b} rotation={[Math.PI / 2.9, -0.45, 0.3]}>
        <torusGeometry args={[R * 1.7, 0.003, 8, 220]} />
        <meshBasicMaterial color="#ff8a5c" transparent opacity={0.22} />
      </mesh>
    </>
  );
}

/* ── World group: rotation, parallax, responsive placement ───── */

function World({ sprite, reduced }: { sprite: THREE.Texture; reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const pointer = useRef({ x: 0, y: 0 });
  const { size } = useThree();

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      pointer.current.x = (e.clientX / window.innerWidth) * 2 - 1;
      pointer.current.y = (e.clientY / window.innerHeight) * 2 - 1;
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, []);

  useFrame((_, dt) => {
    const g = group.current;
    if (!g) return;
    const wide = size.width > 980;
    const targetX = wide ? 2.7 : 0;
    const targetY = wide ? -0.1 : 2.0;
    const targetS = wide ? 0.8 : 0.5;
    g.position.x += (targetX - g.position.x) * Math.min(1, dt * 2);
    g.position.y += (targetY - g.position.y) * Math.min(1, dt * 2);
    g.scale.setScalar(g.scale.x + (targetS - g.scale.x) * Math.min(1, dt * 2));

    if (!reduced) g.rotation.y += dt * 0.07;
    const rx = 0.32 + pointer.current.y * 0.14;
    g.rotation.x += (rx - g.rotation.x) * Math.min(1, dt * 2);
    g.rotation.z += (pointer.current.x * -0.06 - g.rotation.z) * Math.min(1, dt * 2);
  });

  const flights = useMemo(
    () =>
      ROUTES.map(([a, b], i) => ({
        from: CITIES[a],
        to: CITIES[b],
        offset: (i * 0.173) % 1,
        speed: 0.045 + (i % 4) * 0.012,
      })),
    []
  );
  const beacons = useMemo(() => Object.values(CITIES), []);

  return (
    <group ref={group} position={[2.7, -0.1, 0]} scale={0.8}>
      <Globe sprite={sprite} />
      <Rings />
      {flights.map((f, i) => (
        <Flight key={i} {...f} />
      ))}
      {beacons.map((c, i) => (
        <Beacon key={c.name} city={c} phase={i * 0.13} />
      ))}
    </group>
  );
}

/* ── Canvas ──────────────────────────────────────────────────── */

export default function TravelScene() {
  const sprite = useMemo(() => dotTexture(), []);
  const reduced = useMemo(
    () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    []
  );

  return (
    <Canvas
      className="!absolute inset-0"
      camera={{ position: [0, 0, 7.4], fov: 45 }}
      dpr={[1, 1.6]}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      style={{ pointerEvents: "none" }}
    >
      <Stars radius={90} depth={60} count={3600} factor={3.2} saturation={0} fade speed={reduced ? 0 : 0.6} />
      <World sprite={sprite} reduced={reduced} />
    </Canvas>
  );
}
