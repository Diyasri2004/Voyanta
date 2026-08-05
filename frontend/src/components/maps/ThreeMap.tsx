"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls, Sphere, MeshDistortMaterial } from "@react-three/drei";
import { Suspense } from "react";

export default function ThreeMap({ trip }: { trip: any }) {
  // A simplistic abstract 3D Holo-globe representation
  return (
    <div className="h-full w-full bg-[#03050a] flex flex-col items-center justify-center">
      <Canvas camera={{ position: [0, 0, 5] }}>
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 10]} intensity={1} color="#00f0ff" />
        <directionalLight position={[-10, -10, -10]} intensity={1} color="#ff007f" />
        
        <Suspense fallback={null}>
          <Sphere args={[1.5, 64, 64]} position={[0, 0, 0]}>
            <MeshDistortMaterial
              color="#03050a"
              envMapIntensity={1}
              clearcoat={1}
              clearcoatRoughness={0.1}
              metalness={0.9}
              roughness={0.2}
              distort={0.2}
              speed={2}
              wireframe
            />
          </Sphere>
          
          {/* Laser arcs placeholder - in a full implementation we'd map coordinates to 3D sphere surface */}
          {trip?.itinerary?.map((stop: any, idx: number) => (
            <mesh key={idx} position={[(Math.random() - 0.5) * 3, (Math.random() - 0.5) * 3, 1.6]}>
              <boxGeometry args={[0.05, 0.05, 0.2]} />
              <meshStandardMaterial color="#39ff14" emissive="#39ff14" emissiveIntensity={2} />
            </mesh>
          ))}
        </Suspense>
        
        <OrbitControls enableZoom={true} autoRotate autoRotateSpeed={0.5} />
      </Canvas>
      <div className="absolute bottom-6 bg-[#03050a]/80 border border-[#39ff14]/30 px-4 py-2 rounded-full text-xs text-[#39ff14] font-mono">
        3D Holo-Globe Active • {trip?.itinerary?.length || 0} Waypoints Mapped
      </div>
    </div>
  );
}
