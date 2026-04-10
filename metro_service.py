import heapq
import json
import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional, Set, Tuple
from urllib.request import urlopen

from settings import (
    LOCAL_METRO_DATA_PATH,
    METRO_API_URL,
    SPECIAL_LINE_KEYWORDS,
    SPECIAL_TRANSFER_MINUTES,
    STATION_STOP_MINUTES,
    TRAIN_SPEED_KMH,
    TRANSFER_DISTANCE_KM,
    TRANSFER_MINUTES,
)


@dataclass(frozen=True)
class Station:
    id: str
    name: str
    line_id: str
    line_name: str
    line_color: str
    lat: float
    lng: float
    order: int


@dataclass(frozen=True)
class Edge:
    to_station_id: str
    minutes: float
    kind: str  # train or transfer


@dataclass(frozen=True)
class MetroMap:
    stations: Dict[str, Station]
    graph: Dict[str, List[Edge]]
    stations_by_name: Dict[str, List[str]]


class MetroError(Exception):
    pass


class MetroDataLoadError(MetroError):
    pass


class StationNotFoundError(MetroError):
    pass


class RouteNotFoundError(MetroError):
    pass


def normalize_station_name(name: str) -> str:
    return (
        name.lower()
        .replace("ё", "е")
        .replace("-", " ")
        .replace("(", " ")
        .replace(")", " ")
        .replace(".", " ")
        .strip()
    )


def is_special_line(line_name: str) -> bool:
    upper_name = line_name.upper()
    return any(keyword in upper_name for keyword in SPECIAL_LINE_KEYWORDS)


def haversine_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    earth_radius_km = 6371

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_km * c


def train_minutes_between(left_station: Station, right_station: Station) -> float:
    distance_km = haversine_distance_km(
        left_station.lat,
        left_station.lng,
        right_station.lat,
        right_station.lng,
    )
    return (distance_km / (TRAIN_SPEED_KMH / 60)) + STATION_STOP_MINUTES


def transfer_minutes_between(left_station: Station, right_station: Station) -> int:
    if is_special_line(left_station.line_name) or is_special_line(
        right_station.line_name
    ):
        return SPECIAL_TRANSFER_MINUTES
    return TRANSFER_MINUTES


def should_create_transfer(left_station: Station, right_station: Station) -> bool:
    if left_station.line_id == right_station.line_id:
        return False

    # Одинаковые названия считаем готовой пересадкой даже без проверки расстояния.
    if normalize_station_name(left_station.name) == normalize_station_name(
        right_station.name
    ):
        return True

    distance_km = haversine_distance_km(
        left_station.lat,
        left_station.lng,
        right_station.lat,
        right_station.lng,
    )
    return distance_km <= TRANSFER_DISTANCE_KM


def load_metro_data() -> dict:
    try:
        if LOCAL_METRO_DATA_PATH.exists():
            with LOCAL_METRO_DATA_PATH.open("r", encoding="utf-8-sig") as file:
                return json.load(file)

        with urlopen(METRO_API_URL, timeout=30) as response:
            return json.load(response)
    except Exception as error:
        raise MetroDataLoadError(
            f"Не удалось загрузить схему метро: {error}"
        ) from error


def add_edge(
    graph: Dict[str, List[Edge]],
    from_station_id: str,
    to_station_id: str,
    minutes: float,
    kind: str,
) -> None:
    graph[from_station_id].append(
        Edge(
            to_station_id=to_station_id,
            minutes=round(minutes, 2),
            kind=kind,
        )
    )


@lru_cache(maxsize=1)
def get_metro_map() -> MetroMap:
    # Схема метро строится один раз и дальше переиспользуется всеми запросами.
    raw_metro = load_metro_data()

    stations: Dict[str, Station] = {}
    graph: Dict[str, List[Edge]] = {}
    stations_by_name: Dict[str, List[str]] = {}

    for line in raw_metro["lines"]:
        sorted_stations = sorted(line["stations"], key=lambda station: station["order"])

        for raw_station in sorted_stations:
            station = Station(
                id=raw_station["id"],
                name=raw_station["name"],
                line_id=line["id"],
                line_name=line["name"],
                line_color=line["hex_color"],
                lat=raw_station["lat"],
                lng=raw_station["lng"],
                order=raw_station["order"],
            )

            stations[station.id] = station
            graph[station.id] = []

            normalized_name = normalize_station_name(station.name)
            stations_by_name.setdefault(normalized_name, []).append(station.id)

        # Создаем рёбра между соседними станциями на одной линии
        # На одной линии соединяем только соседние станции по порядку.
        for left_raw_station, right_raw_station in zip(
            sorted_stations, sorted_stations[1:]
        ):
            left_station = stations[left_raw_station["id"]]
            right_station = stations[right_raw_station["id"]]
            minutes = train_minutes_between(left_station, right_station)

            add_edge(graph, left_station.id, right_station.id, minutes, "train")
            add_edge(graph, right_station.id, left_station.id, minutes, "train")

    station_list = list(stations.values())

    # Создаем рёбра между станциями для пересадок
    # Отдельно добавляем пересадки между разными линиями.
    for index, left_station in enumerate(station_list):
        for right_station in station_list[index + 1 :]:
            if not should_create_transfer(left_station, right_station):
                continue

            minutes = transfer_minutes_between(left_station, right_station)
            add_edge(graph, left_station.id, right_station.id, minutes, "transfer")
            add_edge(graph, right_station.id, left_station.id, minutes, "transfer")

    return MetroMap(stations=stations, graph=graph, stations_by_name=stations_by_name)


def find_station_ids_by_name(metro_map: MetroMap, station_name: str) -> List[str]:
    normalized_name = normalize_station_name(station_name)
    return metro_map.stations_by_name.get(normalized_name, [])


# Вспомогательная функция для быстрого поиска рёбер между станциями при восстановлении пути
# Нужен для быстрого получения ребра при сборке готового маршрута.
def build_edge_lookup(graph: Dict[str, List[Edge]]) -> Dict[Tuple[str, str], Edge]:
    edge_lookup: Dict[Tuple[str, str], Edge] = {}

    for from_station_id, edges in graph.items():
        for edge in edges:
            edge_lookup[(from_station_id, edge.to_station_id)] = edge

    return edge_lookup


# Восстанавливает путь от начальной станции до конечной по словарю предыдущих станций, который был построен алгоритмом Дейкстры
# Идём от финиша назад по previous и затем разворачиваем путь.
def restore_path(
    previous: Dict[str, Optional[str]], finish_station_id: str
) -> List[str]:
    path: List[str] = []
    current_station_id: Optional[str] = finish_station_id

    while current_station_id is not None:
        path.append(current_station_id)
        current_station_id = previous.get(current_station_id)

    path.reverse()
    return path


def search_stations(query: Optional[str] = None) -> dict:
    metro_map = get_metro_map()
    stations_info: Dict[str, Set[str]] = {}
    normalized_query = normalize_station_name(query) if query else None

    for station in metro_map.stations.values():
        normalized_name = normalize_station_name(station.name)

        if normalized_query and normalized_query not in normalized_name:
            continue

        stations_info.setdefault(station.name, set()).add(station.line_name)

    items = [
        {
            "station_name": station_name,
            "lines": sorted(line_names),
        }
        for station_name, line_names in stations_info.items()
    ]
    items.sort(key=lambda item: item["station_name"])

    return {
        "count": len(items),
        "stations": items,
    }


def find_route(from_station_name: str, to_station_name: str) -> dict:
    metro_map = get_metro_map()

    start_station_ids = find_station_ids_by_name(metro_map, from_station_name)
    finish_station_ids = set(find_station_ids_by_name(metro_map, to_station_name))

    if not start_station_ids:
        raise StationNotFoundError(f"Станция '{from_station_name}' не найдена")

    if not finish_station_ids:
        raise StationNotFoundError(f"Станция '{to_station_name}' не найдена")

    distances: Dict[str, float] = {
        station_id: math.inf for station_id in metro_map.stations
    }
    previous: Dict[str, Optional[str]] = {}
    priority_queue: List[Tuple[float, str]] = []

    # Если название встречается на нескольких линиях, стартуем сразу из всех вариантов.
    for station_id in start_station_ids:
        distances[station_id] = 0
        previous[station_id] = None
        heapq.heappush(priority_queue, (0, station_id))

    found_finish_station_id: Optional[str] = None

    while priority_queue:
        current_distance, current_station_id = heapq.heappop(priority_queue)

        # В очереди могут остаться старые, уже невыгодные варианты той же станции.
        if current_distance > distances[current_station_id]:
            continue

        # Первая извлечённая конечная станция уже имеет минимальное время.
        if current_station_id in finish_station_ids:
            found_finish_station_id = current_station_id
            break

        for edge in metro_map.graph[current_station_id]:
            new_distance = current_distance + edge.minutes

            if new_distance >= distances[edge.to_station_id]:
                continue

            # Запоминаем более выгодный путь до соседней станции.
            distances[edge.to_station_id] = new_distance
            previous[edge.to_station_id] = current_station_id
            heapq.heappush(priority_queue, (new_distance, edge.to_station_id))

    if found_finish_station_id is None:
        raise RouteNotFoundError("Маршрут между станциями не найден")

    edge_lookup = build_edge_lookup(metro_map.graph)
    path_station_ids = restore_path(previous, found_finish_station_id)

    path: List[dict] = []
    transfers_count = 0

    for index, station_id in enumerate(path_station_ids):
        station = metro_map.stations[station_id]
        item = {
            "station_id": station.id,
            "station_name": station.name,
            "line_id": station.line_id,
            "line_name": station.line_name,
            "line_color": station.line_color,
            "lat": station.lat,
            "lng": station.lng,
        }

        if index == 0:
            item["move_type"] = "start"
            item["minutes_from_previous"] = 0
        else:
            previous_station_id = path_station_ids[index - 1]
            edge = edge_lookup[(previous_station_id, station_id)]
            item["move_type"] = edge.kind
            item["minutes_from_previous"] = edge.minutes

            if edge.kind == "transfer":
                transfers_count += 1

        path.append(item)

    return {
        "from_station": from_station_name,
        "to_station": to_station_name,
        "total_minutes": round(distances[found_finish_station_id], 2),
        "stations_in_path": len(path_station_ids),
        "transfers_count": transfers_count,
        "path": path,
    }
