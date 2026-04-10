from pydantic import BaseModel


class RootConstantsResponse(BaseModel):
    train_speed: int
    transfer_minutes: int
    special_transfer_minutes: int
    transfer_distance_km: float
    special_lines: list[str]


class RootEndpointsResponse(BaseModel):
    ui: str
    stations: str
    route: str


class RootResponse(BaseModel):
    message: str
    metro_api_url: str
    local_data_file: str
    constants: RootConstantsResponse
    endpoints: RootEndpointsResponse


class StationInfoResponse(BaseModel):
    station_name: str
    lines: list[str]


class StationsResponse(BaseModel):
    count: int
    stations: list[StationInfoResponse]


class RouteStepResponse(BaseModel):
    station_id: str
    station_name: str
    line_id: str
    line_name: str
    line_color: str
    lat: float
    lng: float
    move_type: str
    minutes_from_previous: float


class RouteResponse(BaseModel):
    from_station: str
    to_station: str
    total_minutes: float
    stations_in_path: int
    transfers_count: int
    path: list[RouteStepResponse]
