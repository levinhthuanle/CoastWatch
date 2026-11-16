"""
Tile proxy — forwards satellite/raster tile requests to upstream providers.
Avoids browser Tracking Prevention blocking third-party tile requests.
"""
import httpx
from fastapi import APIRouter, HTTPException, Response

router = APIRouter()

_client = httpx.AsyncClient(
    timeout=10,
    headers={
        "User-Agent": "CoastWatch/1.0 (research project)",
        "Referer": "http://localhost:5173",
    },
    follow_redirects=True,
)

PROVIDERS = {
    "esri": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    "osm":  "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
}


@router.get("/satellite/{z}/{x}/{y}")
async def satellite_tile(z: int, x: int, y: int) -> Response:
    url = PROVIDERS["esri"].format(z=z, x=x, y=y)
    try:
        r = await _client.get(url)
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail="Tile not found")
        return Response(
            content=r.content,
            media_type=r.headers.get("content-type", "image/jpeg"),
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Tile fetch failed: {e}")


@router.get("/osm/{z}/{x}/{y}")
async def osm_tile(z: int, x: int, y: int) -> Response:
    url = PROVIDERS["osm"].format(z=z, x=x, y=y)
    try:
        r = await _client.get(url)
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail="Tile not found")
        return Response(
            content=r.content,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Tile fetch failed: {e}")
