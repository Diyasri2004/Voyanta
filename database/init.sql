-- Enable PostGIS for geospatial queries
CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. Users Profile
CREATE TABLE profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    style_preference TEXT CHECK (style_preference IN ('foodie', 'culture_explorer', 'techie')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Trips
CREATE TABLE trips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    budget_total DECIMAL(10,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Waypoints (Itinerary Items)
CREATE TABLE waypoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID REFERENCES trips(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    sequence_order INT NOT NULL,
    location geography(POINT, 4326) NOT NULL, -- PostGIS Geography type
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Spatial index for blazing fast geo-lookups
CREATE INDEX waypoints_location_idx ON waypoints USING GIST (location);
CREATE INDEX waypoints_trip_time_idx ON waypoints(trip_id, start_time);

-- 4. Events & Festivals (The Discovery Engine Database)
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    event_type TEXT NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    location geography(POINT, 4326) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Spatial index for events
CREATE INDEX events_location_idx ON events USING GIST (location);
CREATE INDEX events_time_idx ON events(start_time, end_time);
