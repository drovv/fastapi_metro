from pathlib import Path


BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
LOCAL_METRO_DATA_PATH = BASE_DIR / "data" / "metro.json"

APP_TITLE = "Маршруты московского метро"
APP_DESCRIPTION = (
    "Приложение на FastAPI, которое ищет кратчайший путь алгоритмом Дейкстры."
)
METRO_API_URL = "https://api.hh.ru/metro/1"

TRAIN_SPEED_KMH = 60
STATION_STOP_MINUTES = 1
TRANSFER_MINUTES = 10
SPECIAL_TRANSFER_MINUTES = 15
TRANSFER_DISTANCE_KM = 0.35
SPECIAL_LINE_KEYWORDS = ("МЦК", "МЦД")
