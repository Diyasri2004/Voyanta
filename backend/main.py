from fastapi import FastAPI, HTTPException, Depends
from typing import List
import asyncpg
import os
from models import EventFestival

app = FastAPI(title="Voyanta API")

# Database connection dependency (Simplified for scaffolding)
async def get_db_pool():
    # In a real scenario, this would use a connection string from env variables.
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/voyanta")
    pool = await asyncpg.create_pool(db_url)
    try:
        yield pool
    finally:
        await pool.close()

@app.get("/trips/{trip_id}/smart-suggestions", response_model=List[EventFestival])
async def get_smart_suggestions(trip_id: str, day_date: str, pool: asyncpg.Pool = Depends(get_db_pool)):
    """
    Finds events happening within a 5km radius of any scheduled itinerary waypoint 
    for that specific calendar day using PostGIS ST_DWithin.
    """
    query = """
        WITH trip_waypoints AS (
            SELECT location 
            FROM waypoints 
            WHERE trip_id = $1::uuid AND DATE(start_time) = $2::DATE
        )
        SELECT 
            e.id::text, e.title, e.event_type, e.start_time, e.end_time,
            ST_Y(e.location::geometry) as lat, ST_X(e.location::geometry) as lng,
            MIN(ST_DistanceSphere(e.location::geometry, w.location::geometry)) as distance_meters
        FROM events e
        CROSS JOIN trip_waypoints w
        WHERE DATE(e.start_time) = $2::DATE
          -- PostGIS spatial bounding query (5000 meters)
          AND ST_DWithin(e.location, w.location, 5000)
        GROUP BY e.id, e.title, e.event_type, e.start_time, e.end_time, e.location
        ORDER BY distance_meters ASC
        LIMIT 10;
    """
    
    async with pool.acquire() as conn:
        try:
            records = await conn.fetch(query, trip_id, day_date)
        except asyncpg.exceptions.InvalidTextRepresentationError:
            raise HTTPException(status_code=400, detail="Invalid UUID format for trip_id.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
    return [EventFestival(**dict(record)) for record in records]
