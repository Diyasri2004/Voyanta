"use client";

/**
 * Night flight — the Voyanta hero world.
 *
 * Real-geography Earth seen at night: dark ocean, dotted continents that
 * glow only where the sun touches them, amber city lights on the dark side,
 * a blue atmospheric limb, and a few flight paths. The globe is steered from
 * outside through `sceneStore` (hover → fly to a city, scroll → choreography,
 * planning → dive in).
 */

import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Line, Stars } from "@react-three/drei";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import * as THREE from "three";
import { buildEarth, latLng, R } from "./earthData";
import { sceneStore } from "@/lib/sceneStore";

/* Sun sits to the right and slightly behind the globe's centre, so the
   middle of the disc is night (lights visible) and a day crescent hugs the right limb. */
const SUN = new THREE.Vector3(1, 0.24, -0.32).normalize();

/* ── shaders ─────────────────────────────────────────────────── */

const pointsVertex = /* glsl */ `
  attribute float aSeed;
  uniform vec3 uSun;
  uniform float uSize;
  uniform float uScale;
  varying float vLit;
  varying float vSeed;
  void main() {
    vec3 wn = normalize(mat3(modelMatrix) * position);
    vLit = dot(wn, normalize(uSun));
    vSeed = aSeed;
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = uSize * uScale * (0.7 + 0.6 * aSeed) / -mv.z;
    gl_Position = projectionMatrix * mv;
  }
`;

const landFragment = /* glsl */ `
  varying float vLit;
  varying float vSeed;
  void main() {
    vec2 c = gl_PointCoord - 0.5;
    float d = length(c);
    if (d > 0.5) discard;
    float day = smoothstep(-0.10, 0.38, vLit);
    vec3 night = vec3(0.16, 0.25, 0.44);
    vec3 dayCol = mix(vec3(0.55, 0.80, 1.0), vec3(0.85, 0.95, 1.0), vSeed);
    vec3 col = mix(night, dayCol, day);
    float a = smoothstep(0.5, 0.15, d) * mix(0.42, 0.95, day);
    gl_FragColor = vec4(col, a);
  }
`;

const lightsFragment = /* glsl */ `
  uniform float uTime;
  varying float vLit;
  varying float vSeed;
  void main() {
    vec2 c = gl_PointCoord - 0.5;
    float d = length(c) * 2.0;
    if (d > 1.0) discard;
    float night = 1.0 - smoothstep(-0.02, 0.30, vLit);
    float tw = 0.78 + 0.22 * sin(uTime * (1.2 + vSeed * 2.0) + vSeed * 50.0);
    float glow = pow(1.0 - d, 2.8);
    vec3 col = mix(vec3(1.0, 0.58, 0.20), vec3(1.0, 0.88, 0.62), vSeed);
    gl_FragColor = vec4(col * 1.05, glow * night * tw);
  }
`;

const borderVertex = /* glsl */ `
  uniform vec3 uSun;
  varying float vLit;
  void main() {
    vLit = dot(normalize(mat3(modelMatrix) * position), normalize(uSun));
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;
const borderFragment = /* glsl */ `
  varying float vLit;
  void main() {
    float day = smoothstep(-0.10, 0.4, vLit);
    vec3 col = mix(vec3(0.20, 0.30, 0.55), vec3(0.65, 0.85, 1.0), day);
    gl_FragColor = vec4(col, mix(0.10, 0.28, day));
  }
`;

const oceanVertex = /* glsl */ `
  varying vec3 vWN;
  varying vec3 vVN;
  void main() {
    vWN = normalize(mat3(modelMatrix) * normal);
    vVN = normalize(normalMatrix * normal);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;
const oceanFragment = /* glsl */ `
  uniform vec3 uSun;
  varying vec3 vWN;
  varying vec3 vVN;
  void main() {
    float sunDot = dot(normalize(vWN), normalize(uSun));
    float day = smoothstep(-0.18, 0.5, sunDot);
    vec3 night = vec3(0.012, 0.024, 0.052);
    vec3 dayCol = vec3(0.025, 0.12, 0.26);
    vec3 col = mix(night, dayCol, day);
    float fres = pow(1.0 - max(dot(normalize(vVN), vec3(0.0, 0.0, 1.0)), 0.0), 2.6);
    col += vec3(0.10, 0.32, 0.62) * fres * (0.18 + 0.82 * day);
    gl_FragColor = vec4(col, 1.0);
  }
`;

const atmoFragment = /* glsl */ `
  uniform vec3 uSun;
  varying vec3 vWN;
  varying vec3 vVN;
  void main() {
    float i = pow(max(0.74 - dot(normalize(vVN), vec3(0.0, 0.0, 1.0)), 0.0), 3.0);
    float sunSide = smoothstep(-0.5, 0.7, dot(normalize(vWN), normalize(uSun)));
    vec3 col = mix(vec3(0.10, 0.26, 0.80), vec3(0.45, 0.85, 1.0), sunSide);
    gl_FragColor = vec4(col, 1.0) * i * (0.35 + 0.95 * sunSide);
  }
`;

/* ── Earth ───────────────────────────────────────────────────── */

function Earth() {
  const data = useMemo(() => buildEarth(), []);

  const landGeo = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(data.landPositions, 3));
    g.setAttribute("aSeed", new THREE.BufferAttribute(data.landSeeds, 1));
    return g;
  }, [data]);
  const lightGeo = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(data.lightPositions, 3));
    g.setAttribute("aSeed", new THREE.BufferAttribute(data.lightSeeds, 1));
    return g;
  }, [data]);
  const borderGeo = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(data.borderPositions, 3));
    return g;
  }, [data]);

  const shared = useMemo(
    () => ({ uSun: { value: SUN }, uScale: { value: 400 }, uTime: { value: 0 } }),
    []
  );

  const landMat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: pointsVertex,
        fragmentShader: landFragment,
        uniforms: { ...shared, uSize: { value: 0.042 } },
        transparent: true,
        depthWrite: false,
      }),
    [shared]
  );
  const lightMat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: pointsVertex,
        fragmentShader: lightsFragment,
        uniforms: { ...shared, uSize: { value: 0.07 } },
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      }),
    [shared]
  );
  const borderMat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: borderVertex,
        fragmentShader: borderFragment,
        uniforms: { uSun: shared.uSun },
        transparent: true,
        depthWrite: false,
      }),
    [shared]
  );
  const oceanMat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: oceanVertex,
        fragmentShader: oceanFragment,
        uniforms: { uSun: shared.uSun },
      }),
    [shared]
  );
  const atmoMat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: oceanVertex,
        fragmentShader: atmoFragment,
        uniforms: { uSun: shared.uSun },
        side: THREE.BackSide,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      }),
    [shared]
  );

  useFrame((state) => {
    shared.uTime.value = state.clock.elapsedTime;
    shared.uScale.value = (state.size.height * state.viewport.dpr) / 2;
  });

  return (
    <group>
      <mesh material={oceanMat}>
        <sphereGeometry args={[R * 0.99, 96, 96]} />
      </mesh>
      <lineSegments geometry={borderGeo} material={borderMat} />
      <points geometry={landGeo} material={landMat} />
      <points geometry={lightGeo} material={lightMat} />
      <mesh material={atmoMat} scale={1.17}>
        <sphereGeometry args={[R, 96, 96]} />
      </mesh>
    </group>
  );
}

/* ── Destination pin: amber core, two sonar rings and a light beam ── */

function FocusPin() {
  const root = useRef<THREE.Group>(null);
  const ringA = useRef<THREE.Mesh>(null);
  const ringB = useRef<THREE.Mesh>(null);
  const scale = useRef(0);
  const pos = useMemo(() => new THREE.Vector3(), []);
  const out = useMemo(() => new THREE.Vector3(), []);

  useFrame((state, dt) => {
    const g = root.current;
    if (!g) return;
    const f = sceneStore.focus;
    scale.current += ((f ? 1 : 0) - scale.current) * Math.min(1, dt * 5);
    g.visible = scale.current > 0.02;
    if (!g.visible) return;
    if (f) {
      latLng(f.lat, f.lng, R * 1.004, pos);
      g.position.copy(pos);
      out.copy(pos).multiplyScalar(2);
      g.lookAt(out);
    }
    g.scale.setScalar(scale.current);
    const t = state.clock.elapsedTime;
    [ringA.current, ringB.current].forEach((m, i) => {
      if (!m) return;
      const p = (t * 0.55 + i * 0.5) % 1;
      m.scale.setScalar(0.5 + p * 3.2);
      (m.material as THREE.MeshBasicMaterial).opacity = (1 - p) * 0.75;
    });
  });

  return (
    <group ref={root} visible={false}>
      <mesh>
        <sphereGeometry args={[0.03, 20, 20]} />
        <meshBasicMaterial color="#ffd89a" toneMapped={false} />
      </mesh>
      <mesh ref={ringA}>
        <ringGeometry args={[0.05, 0.062, 48]} />
        <meshBasicMaterial color="#ffc36b" transparent depthWrite={false} side={THREE.DoubleSide} toneMapped={false} />
      </mesh>
      <mesh ref={ringB}>
        <ringGeometry args={[0.05, 0.062, 48]} />
        <meshBasicMaterial color="#ffc36b" transparent depthWrite={false} side={THREE.DoubleSide} toneMapped={false} />
      </mesh>
      {/* beam along the surface normal (group's +Z after lookAt) */}
      <mesh position={[0, 0, 0.5]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.004, 0.022, 1, 14, 1, true]} />
        <meshBasicMaterial color="#ffc36b" transparent opacity={0.4} depthWrite={false} blending={THREE.AdditiveBlending} toneMapped={false} />
      </mesh>
    </group>
  );
}

/* ── Ambient flights ─────────────────────────────────────────── */

const FLIGHTS: Array<[[number, number], [number, number]]> = [
  [[28.6, 77.2], [51.5, -0.1]], // Delhi → London
  [[40.7, -74], [48.9, 2.4]], // New York → Paris
  [[25.2, 55.3], [-33.9, 18.4]], // Dubai → Cape Town
  [[35.7, 139.7], [37.8, -122.4]], // Tokyo → San Francisco
  [[1.35, 103.8], [-33.9, 151.2]], // Singapore → Sydney
  [[-23.5, -46.6], [38.7, -9.1]], // São Paulo → Lisbon
];

const TRAIL = 28;

function Flight({ from, to, offset, speed }: { from: [number, number]; to: [number, number]; offset: number; speed: number }) {
  const curve = useMemo(() => {
    const a = latLng(from[0], from[1], R * 1.004);
    const b = latLng(to[0], to[1], R * 1.004);
    const dist = a.distanceTo(b);
    const ctrl = a.clone().add(b).multiplyScalar(0.5).normalize().multiplyScalar(R + 0.2 + dist * 0.4);
    return new THREE.QuadraticBezierCurve3(a, ctrl, b);
  }, [from, to]);
  const arc = useMemo(() => curve.getPoints(80), [curve]);
  const plane = useRef<THREE.Mesh>(null);
  const tmp = useMemo(() => new THREE.Vector3(), []);

  const trail = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(TRAIL * 3), 3));
    const col = new Float32Array(TRAIL * 3);
    const hot = new THREE.Color("#ffd89a");
    for (let i = 0; i < TRAIL; i++) {
      const k = 1 - i / (TRAIL - 1);
      col.set([hot.r * k, hot.g * k, hot.b * k], i * 3);
    }
    geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
    return new THREE.Line(
      geo,
      new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false })
    );
  }, []);

  useFrame(({ clock }) => {
    const t = (clock.elapsedTime * speed + offset) % 1;
    if (plane.current) plane.current.position.copy(curve.getPoint(t));
    const attr = trail.geometry.getAttribute("position") as THREE.BufferAttribute;
    for (let i = 0; i < TRAIL; i++) {
      curve.getPoint(Math.max(0, t - i * 0.006), tmp);
      attr.setXYZ(i, tmp.x, tmp.y, tmp.z);
    }
    attr.needsUpdate = true;
  });

  return (
    <group>
      <Line points={arc} color="#ffc36b" lineWidth={0.8} transparent opacity={0.16} />
      <primitive object={trail} />
      <mesh ref={plane}>
        <sphereGeometry args={[0.018, 10, 10]} />
        <meshBasicMaterial color="#fff2d6" toneMapped={false} />
      </mesh>
    </group>
  );
}

/* ── Choreography ────────────────────────────────────────────── */

type Key = [p: number, x: number, y: number, s: number];

// Where the globe lives while the landing page scrolls (wide screens)
const WIDE: Key[] = [
  [0.0, 2.35, -0.05, 0.9],
  [0.2, 3.95, 0.15, 0.7],
  [0.5, 3.8, -0.7, 0.78],
  [0.78, 3.2, -0.3, 0.95],
  [1.0, 0.0, -1.4, 1.55],
];
// … and on phones, where it sits behind the content
const NARROW: Key[] = [
  [0.0, 0.0, 2.35, 0.64],
  [0.3, 0.0, 2.9, 0.5],
  [0.7, 0.0, 2.9, 0.5],
  [1.0, 0.0, -0.4, 1.0],
];

function sample(keys: Key[], p: number): [number, number, number] {
  const c = Math.min(1, Math.max(0, p));
  for (let i = 0; i < keys.length - 1; i++) {
    const [p0, x0, y0, s0] = keys[i];
    const [p1, x1, y1, s1] = keys[i + 1];
    if (c <= p1) {
      const t = (c - p0) / (p1 - p0);
      const e = t * t * (3 - 2 * t);
      return [x0 + (x1 - x0) * e, y0 + (y1 - y0) * e, s0 + (s1 - s0) * e];
    }
  }
  const last = keys[keys.length - 1];
  return [last[1], last[2], last[3]];
}

function World({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const pointer = useRef({ x: 0, y: 0 });
  const yaw = useRef(0.9);
  const hadFocus = useRef(false);
  const eul = useMemo(() => new THREE.Euler(0, 0, 0, "XYZ"), []);
  const targetQ = useMemo(() => new THREE.Quaternion(), []);
  const faceQ = useMemo(() => new THREE.Quaternion(), []);
  const toCam = useMemo(() => new THREE.Vector3(), []);
  const Z = useMemo(() => new THREE.Vector3(0, 0, 1), []);
  const flights = useMemo(
    () => FLIGHTS.map(([from, to], i) => ({ from, to, offset: (i * 0.19) % 1, speed: 0.04 + (i % 3) * 0.012 })),
    []
  );

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      pointer.current.x = (e.clientX / window.innerWidth) * 2 - 1;
      pointer.current.y = (e.clientY / window.innerHeight) * 2 - 1;
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, []);

  useFrame((state, dt) => {
    const g = group.current;
    if (!g) return;
    const s = sceneStore;
    const wide = state.size.width > 980;
    const k = (rate: number) => 1 - Math.exp(-dt * rate);

    // placement: scroll choreography, then pulled to centre & enlarged when "warping"
    const [bx, by, bs] = sample(wide ? WIDE : NARROW, s.scroll);
    const tx = bx * (1 - s.warp) + pointer.current.x * 0.14;
    const ty = by * (1 - s.warp) - pointer.current.y * 0.1 + s.recede * 0.4;
    const ts = bs + s.warp * 0.9 - s.recede * 0.25;
    g.position.x += (tx - g.position.x) * k(2.4);
    g.position.y += (ty - g.position.y) * k(2.4);
    g.scale.setScalar(g.scale.x + (ts - g.scale.x) * k(2.4));
    state.camera.position.z += (7.4 - s.warp * 2.4 - state.camera.position.z) * k(1.6);

    // orientation: face the focused city, otherwise drift slowly
    if (s.focus) {
      const v = latLng(s.focus.lat, s.focus.lng, 1);
      const alpha = Math.atan2(-v.x, v.z);
      const beta = Math.atan2(v.y, Math.hypot(v.x, v.z));
      eul.set(beta * 0.92, alpha, 0, "XYZ");
      hadFocus.current = true;
    } else {
      if (hadFocus.current) {
        yaw.current = new THREE.Euler().setFromQuaternion(g.quaternion, "XYZ").y;
        hadFocus.current = false;
      }
      if (!reduced) yaw.current += dt * 0.045;
      eul.set(0.32, yaw.current, 0, "XYZ");
    }
    targetQ.setFromEuler(eul);
    if (s.focus) {
      toCam.copy(state.camera.position).sub(g.position).normalize();
      faceQ.setFromUnitVectors(Z, toCam);
      targetQ.premultiply(faceQ);
    }
    g.quaternion.slerp(targetQ, k(s.focus ? 2.0 : 1.2));
  });

  return (
    <group ref={group} position={[2.35, -0.05, 0]} scale={0.6}>
      <Earth />
      <FocusPin />
      {flights.map((f, i) => (
        <Flight key={i} {...f} />
      ))}
    </group>
  );
}

/* ── Canvas ──────────────────────────────────────────────────── */

export default function TravelScene() {
  const reduced = useMemo(
    () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    []
  );

  return (
    <Canvas
      className="!absolute inset-0"
      camera={{ position: [0, 0, 7.4], fov: 45 }}
      dpr={[1, 1.6]}
      gl={{ antialias: false, powerPreference: "high-performance" }}
      style={{ pointerEvents: "none" }}
    >
      <color attach="background" args={["#050912"]} />
      <Stars radius={90} depth={60} count={2600} factor={3} saturation={0} fade speed={reduced ? 0 : 0.4} />
      <World reduced={reduced} />
      <EffectComposer multisampling={0}>
        <Bloom mipmapBlur intensity={0.7} luminanceThreshold={0.4} luminanceSmoothing={0.25} />
      </EffectComposer>
    </Canvas>
  );
}
