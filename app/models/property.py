from pydantic import BaseModel
from typing import Optional

class Property(BaseModel):
    id: int
    synthetic_stateid: str
    county_name: Optional[str] = None
    geom: Optional[str] = None

    class Config:
        from_attributes = True
