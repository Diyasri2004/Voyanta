from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class UserStyle(str, Enum):
    FOODIE = 'foodie'
    CULTURE = 'culture_explorer'
    TECHIE = 'techie'

class UserProfile(BaseModel):
    id: str
    username: str
    style_preference: UserStyle

class Waypoint(BaseModel):
    id: str
    trip_id: str
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    lat: float
    lng: float
    sequence_order: int

class EventFestival(BaseModel):
    id: str
    title: str
    event_type: str
    start_time: datetime
    end_time: datetime
    lat: float
    lng: float
    distance_meters: Optional[float] = None
