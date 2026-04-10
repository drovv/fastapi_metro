from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from metro_service import (
    MetroDataLoadError,
    RouteNotFoundError,
    StationNotFoundError,
    find_route,
    search_stations,
)
from settings import (
    APP_DESCRIPTION,
    APP_TITLE,
    LOCAL_METRO_DATA_PATH,
    METRO_API_URL,
    SPECIAL_LINE_KEYWORDS,
    SPECIAL_TRANSFER_MINUTES,
    STATIC_DIR,
    TEMPLATES_DIR,
    TRAIN_SPEED_KMH,
    TRANSFER_DISTANCE_KM,
    TRANSFER_MINUTES,
)


app = FastAPI(title=APP_TITLE, description=APP_DESCRIPTION)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/ui", include_in_schema=False)
def read_ui() -> FileResponse:
    return FileResponse(TEMPLATES_DIR / "index.html")


@app.get("/")
def read_root() -> dict:
    return {
        "message": "FastAPI приложение для поиска кратчайшего пути по московскому метро",
        "metro_api_url": METRO_API_URL,
        "local_data_file": str(LOCAL_METRO_DATA_PATH),
        "constants": {
            "train_speed": TRAIN_SPEED_KMH,
            "transfer_minutes": TRANSFER_MINUTES,
            "special_transfer_minutes": SPECIAL_TRANSFER_MINUTES,
            "transfer_distance_km": TRANSFER_DISTANCE_KM,
            "special_lines": list(SPECIAL_LINE_KEYWORDS),
        },
        "endpoints": {
            "ui": "/ui",
            "stations": "/stations?q=киев",
            "route": "/route?from_station=Киевская&to_station=Белорусская",
        },
    }


@app.get("/stations")
def list_stations(
    q: str | None = Query(default=None, description="Часть названия станции")
) -> dict:
    try:
        return search_stations(q)
    except MetroDataLoadError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/route")
def get_route(
    from_station: str = Query(..., description="Начальная станция"),
    to_station: str = Query(..., description="Конечная станция"),
) -> dict:
    try:
        return find_route(from_station, to_station)
    except StationNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RouteNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except MetroDataLoadError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
