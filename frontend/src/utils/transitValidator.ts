const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;

export interface Waypoint {
  id: string;
  startTime: Date;
  endTime: Date;
  lat: number;
  lng: number;
}

export interface TransitConflict {
  from: string;
  to: string;
  requiredSec: number;
  availableSec: number;
  message: string;
}

export async function validateTransit(waypoints: Waypoint[]): Promise<TransitConflict[]> {
  const conflicts: TransitConflict[] = [];
  
  if (!MAPBOX_TOKEN) {
    console.warn("Mapbox token not found, skipping transit validation.");
    return conflicts;
  }

  for (let i = 0; i < waypoints.length - 1; i++) {
    const current = waypoints[i];
    const next = waypoints[i+1];
    
    try {
      // Call Mapbox Directions API
      const response = await fetch(
        `https://api.mapbox.com/directions/v5/mapbox/walking/${current.lng},${current.lat};${next.lng},${next.lat}?access_token=${MAPBOX_TOKEN}`
      );
      const data = await response.json();
      
      if (data.routes && data.routes.length > 0) {
        const travelDurationSeconds = data.routes[0].duration;
        const timeGapSeconds = (next.startTime.getTime() - current.endTime.getTime()) / 1000;
        
        if (travelDurationSeconds > timeGapSeconds) {
          conflicts.push({
            from: current.id,
            to: next.id,
            requiredSec: travelDurationSeconds,
            availableSec: timeGapSeconds,
            message: `Needs ${Math.round(travelDurationSeconds/60)}m to travel, but only ${Math.round(timeGapSeconds/60)}m available.`
          });
        }
      }
    } catch (error) {
      console.error("Failed to validate transit:", error);
    }
  }
  return conflicts;
}
