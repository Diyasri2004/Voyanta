"use client";

import { useRef } from 'react';
import Map, { Source, Layer, Marker } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;

export interface MapWaypoint {
  id: string;
  lat: number;
  lng: number;
}

export default function VoyantaMap({ 
  waypoints, 
  routeGeoJSON 
}: { 
  waypoints: MapWaypoint[], 
  routeGeoJSON?: any 
}) {
  const mapRef = useRef(null);
  
  // Line layer styling for the generated route
  const routeLayer = {
    id: 'route',
    type: 'line' as const,
    source: 'route',
    layout: {
      'line-join': 'round' as const,
      'line-cap': 'round' as const
    },
    paint: {
      'line-color': '#FF4A5A',
      'line-width': 4,
      'line-dasharray': [0, 2, 2] // Dashed walking path effect
    }
  };

  return (
    <Map
      ref={mapRef}
      initialViewState={{
        longitude: 135.7681, // e.g., Kyoto
        latitude: 35.0116,
        zoom: 13,
        pitch: 45 // 3D perspective
      }}
      mapStyle="mapbox://styles/mapbox/dark-v11"
      mapboxAccessToken={MAPBOX_TOKEN}
      interactiveLayerIds={['route']}
      style={{ width: '100%', height: '100%' }}
    >
      {waypoints.map((wp, i) => (
        <Marker key={wp.id} longitude={wp.lng} latitude={wp.lat} anchor="bottom">
          <div className="bg-brand-accent text-white w-8 h-8 rounded-full flex items-center justify-center font-bold border-2 border-brand-dark shadow-lg">
            {i + 1}
          </div>
        </Marker>
      ))}

      {routeGeoJSON && (
        <Source id="route" type="geojson" data={routeGeoJSON}>
          <Layer {...routeLayer} />
        </Source>
      )}
    </Map>
  );
}
