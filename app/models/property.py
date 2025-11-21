from pydantic import BaseModel
from typing import Optional
from datetime import date
from decimal import Decimal

class Property(BaseModel):
    id: int
    synthetic_stateid: Optional[str] = None
    STATEID: Optional[str] = None
    PARCELID: Optional[str] = None
    TAXPARCELID: Optional[str] = None
    PARCELDATE: Optional[date] = None
    TAXROLLYEAR: Optional[Decimal] = None
    OWNERNME1: Optional[str] = None
    OWNERNME2: Optional[str] = None
    PSTLADRESS: Optional[str] = None
    SITEADRESS: Optional[str] = None
    ADDNUMPREFIX: Optional[str] = None
    ADDNUM: Optional[str] = None
    ADDNUMSUFFIX: Optional[str] = None
    PREFIX: Optional[str] = None
    STREETNAME: Optional[str] = None
    STREETTYPE: Optional[str] = None
    SUFFIX: Optional[str] = None
    LANDMARKNAME: Optional[str] = None
    UNITTYPE: Optional[str] = None
    UNITID: Optional[str] = None
    PLACENAME: Optional[str] = None
    ZIPCODE: Optional[str] = None
    ZIP4: Optional[str] = None
    STATE: Optional[str] = None
    SCHOOLDIST: Optional[str] = None
    SCHOOLDISTNO: Optional[str] = None
    CNTASSDVALUE: Optional[Decimal] = None
    LNDVALUE: Optional[Decimal] = None
    IMPVALUE: Optional[Decimal] = None
    MFLVALUE: Optional[Decimal] = None
    ESTFMKVALUE: Optional[Decimal] = None
    NETPRPTA: Optional[Decimal] = None
    GRSPRPTA: Optional[Decimal] = None
    PROPCLASS: Optional[str] = None
    AUXCLASS: Optional[str] = None
    ASSDACRES: Optional[float] = None
    DEEDACRES: Optional[float] = None
    GISACRES: Optional[float] = None
    CONAME: Optional[str] = None
    LOADDATE: Optional[date] = None
    PARCELFIPS: Optional[str] = None
    PARCELSRC: Optional[str] = None
    LONGITUDE: Optional[float] = None
    LATITUDE: Optional[float] = None
    Shape_Length: Optional[float] = None
    Shape_Area: Optional[float] = None
    geom: Optional[str] = None

    class Config:
        from_attributes = True