import json
import os
import socket
import threading
import time

from datetime import timedelta

import psutil
import requests

from PySide6.QtCore import (
    QObject,
    QThread,
    QTimer,
    Signal,
)

from config import (
    DATA_DIR,
    OLLAMA_URL,
)


LOCATION_CACHE_FILE = (
    DATA_DIR
    / "location_cache.json"
)


WEATHER_CODES = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Freezing fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    56: "Light freezing drizzle",
    57: "Freezing drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Light showers",
    81: "Showers",
    82: "Heavy showers",
    85: "Light snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Severe thunderstorm with hail",
}


# =========================================================
# BACKGROUND INTERNET / WEATHER THREAD
# =========================================================

class EnvironmentThread(
    QThread
):

    health_updated = Signal(
        dict
    )

    weather_updated = Signal(
        dict
    )

    location_updated = Signal(
        dict
    )

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._stop_event = (
            threading.Event()
        )

        self._location_lock = (
            threading.Lock()
        )

        self._location = (
            self._load_cached_location()
        )

        self._last_health_check = 0.0
        self._last_weather_check = 0.0
        self._last_location_check = 0.0

        self._force_location = True
        self._force_weather = True

        self.session = (
            requests.Session()
        )

        self.session.headers.update(
            {
                "User-Agent":
                    "JARVIS/1.0"
            }
        )

    # =====================================================
    # STOP
    # =====================================================

    def request_stop(
        self,
    ):
        self._stop_event.set()

    # =====================================================
    # LOCATION CACHE
    # =====================================================

    def _load_cached_location(
        self,
    ):
        try:

            if not (
                LOCATION_CACHE_FILE.exists()
            ):
                return {}

            data = json.loads(
                LOCATION_CACHE_FILE
                .read_text(
                    encoding="utf-8"
                )
            )

            if isinstance(
                data,
                dict,
            ):
                return data

        except Exception:
            pass

        return {}

    def _save_location(
        self,
        location,
    ):
        try:

            DATA_DIR.mkdir(
                parents=True,
                exist_ok=True,
            )

            LOCATION_CACHE_FILE.write_text(
                json.dumps(
                    location,
                    indent=2,
                ),
                encoding="utf-8",
            )

        except Exception:
            pass

    def location(
        self,
    ):
        with self._location_lock:

            return dict(
                self._location
            )

    def _set_location(
        self,
        location,
    ):
        with self._location_lock:

            self._location = dict(
                location
            )

    # =====================================================
    # LOCATION PROVIDER 1
    # =====================================================

    def _location_ipwhois(
        self,
    ):
        response = (
            self.session.get(
                "https://ipwho.is/",
                timeout=(
                    3,
                    5,
                ),
            )
        )

        response.raise_for_status()

        data = (
            response.json()
        )

        if not data.get(
            "success",
            False,
        ):
            raise RuntimeError(
                data.get(
                    "message",
                    "IP location failed.",
                )
            )

        timezone_data = (
            data.get(
                "timezone",
                {},
            )
            or {}
        )

        return {
            "available":
                True,

            "city":
                str(
                    data.get(
                        "city",
                        "",
                    )
                ).strip(),

            "region":
                str(
                    data.get(
                        "region",
                        "",
                    )
                ).strip(),

            "country":
                str(
                    data.get(
                        "country",
                        "",
                    )
                ).strip(),

            "country_code":
                str(
                    data.get(
                        "country_code",
                        "",
                    )
                ).strip(),

            "timezone":
                str(
                    timezone_data.get(
                        "id",
                        "",
                    )
                ).strip(),

            "latitude":
                data.get(
                    "latitude"
                ),

            "longitude":
                data.get(
                    "longitude"
                ),

            "cached":
                False,

            "source":
                "ipwho.is",

            "detected_at":
                time.time(),
        }

    # =====================================================
    # LOCATION PROVIDER 2
    # =====================================================

    def _location_ipapi(
        self,
    ):
        response = (
            self.session.get(
                "https://ipapi.co/json/",
                timeout=(
                    3,
                    5,
                ),
            )
        )

        response.raise_for_status()

        data = (
            response.json()
        )

        if data.get(
            "error"
        ):
            raise RuntimeError(
                data.get(
                    "reason",
                    "IP location failed.",
                )
            )

        return {
            "available":
                True,

            "city":
                str(
                    data.get(
                        "city",
                        "",
                    )
                ).strip(),

            "region":
                str(
                    data.get(
                        "region",
                        "",
                    )
                ).strip(),

            "country":
                str(
                    data.get(
                        "country_name",
                        "",
                    )
                ).strip(),

            "country_code":
                str(
                    data.get(
                        "country_code",
                        "",
                    )
                ).strip(),

            "timezone":
                str(
                    data.get(
                        "timezone",
                        "",
                    )
                ).strip(),

            "latitude":
                data.get(
                    "latitude"
                ),

            "longitude":
                data.get(
                    "longitude"
                ),

            "cached":
                False,

            "source":
                "ipapi.co",

            "detected_at":
                time.time(),
        }

    # =====================================================
    # LOCATION NORMALISATION
    # =====================================================

    def _normalise_location(
        self,
        location,
    ):
        city = str(
            location.get(
                "city",
                "",
            )
        ).strip()

        country = str(
            location.get(
                "country",
                "",
            )
        ).strip()

        latitude = (
            location.get(
                "latitude"
            )
        )

        longitude = (
            location.get(
                "longitude"
            )
        )

        if not city:

            raise RuntimeError(
                "Location provider returned "
                "no city."
            )

        if (
            latitude is None
            or
            longitude is None
        ):

            raise RuntimeError(
                "Location provider returned "
                "no coordinates."
            )

        display = city

        if country:

            display += (
                f", {country}"
            )

        location[
            "display"
        ] = display

        return location

    def _detect_location(
        self,
    ):
        providers = (
            self._location_ipwhois,
            self._location_ipapi,
        )

        for provider in providers:

            try:

                location = provider()

                location = (
                    self._normalise_location(
                        location
                    )
                )

                self._save_location(
                    location
                )

                return location

            except Exception:
                continue

        cached = self.location()

        if cached.get(
            "available"
        ):
            cached[
                "cached"
            ] = True

            cached[
                "message"
            ] = (
                "Using cached location."
            )

            return cached

        return {
            "available": False,
            "city": "",
            "region": "",
            "country": "",
            "country_code": "",
            "timezone": "",
            "latitude": None,
            "longitude": None,
            "message":
                "Automatic location "
                "detection unavailable.",
        }

    # =====================================================
    # INTERNET
    # =====================================================

    def _check_internet(
        self,
    ):
        targets = (
            (
                "1.1.1.1",
                443,
            ),

            (
                "8.8.8.8",
                53,
            ),
        )

        for target in targets:

            try:

                connection = (
                    socket.create_connection(
                        target,
                        timeout=1.2,
                    )
                )

                connection.close()

                return True

            except OSError:
                continue

        return False

    # =====================================================
    # OLLAMA
    # =====================================================

    def _check_ollama(
        self,
    ):
        try:

            base_url = (
                OLLAMA_URL
                .split(
                    "/api/",
                    1,
                )[0]
                .rstrip("/")
            )

            response = requests.get(
                f"{base_url}/api/tags",
                timeout=1.5,
            )

            return (
                response.status_code
                == 200
            )

        except requests.RequestException:

            return False

    # =====================================================
    # WEATHER
    # =====================================================

    def _weather_description(
        self,
        code,
    ):
        try:

            code = int(
                code
            )

        except (
            TypeError,
            ValueError,
        ):
            return "Unknown"

        return (
            WEATHER_CODES.get(
                code,
                "Unknown",
            )
        )

    def _get_weather(
        self,
        location,
    ):
        if not location.get(
            "available"
        ):
            return {
                "available": False,
                "message":
                    "Location unavailable.",
            }

        latitude = (
            location.get(
                "latitude"
            )
        )

        longitude = (
            location.get(
                "longitude"
            )
        )

        if (
            latitude is None
            or
            longitude is None
        ):
            return {
                "available": False,
                "message":
                    "No coordinates available.",
            }

        params = {
            "latitude":
                latitude,

            "longitude":
                longitude,

            "current":
                (
                    "temperature_2m,"
                    "relative_humidity_2m,"
                    "apparent_temperature,"
                    "weather_code,"
                    "wind_speed_10m"
                ),

            "temperature_unit":
                "celsius",

            "wind_speed_unit":
                "kmh",

            "timezone":
                "auto",
        }

        try:

            response = (
                self.session.get(
                    (
                        "https://api.open-meteo.com/"
                        "v1/forecast"
                    ),

                    params=params,

                    timeout=(
                        3,
                        6,
                    ),
                )
            )

            response.raise_for_status()

            data = response.json()

            current = (
                data.get(
                    "current",
                    {},
                )
                or {}
            )

            if (
                "temperature_2m"
                not in current
            ):
                raise RuntimeError(
                    "Weather data missing."
                )

            return {
                "available":
                    True,

                "location":
                    location.get(
                        "display",
                        location.get(
                            "city",
                            "",
                        ),
                    ),

                "temperature":
                    current.get(
                        "temperature_2m",
                        "?",
                    ),

                "feels_like":
                    current.get(
                        "apparent_temperature",
                        "?",
                    ),

                "humidity":
                    current.get(
                        "relative_humidity_2m",
                        "?",
                    ),

                "wind":
                    current.get(
                        "wind_speed_10m",
                        "?",
                    ),

                "description":
                    self._weather_description(
                        current.get(
                            "weather_code"
                        )
                    ),

                "timezone":
                    data.get(
                        "timezone",
                        "",
                    ),
            }

        except Exception as exc:

            return {
                "available":
                    False,

                "location":
                    location.get(
                        "display",
                        "",
                    ),

                "message":
                    "Weather currently unavailable.",

                "details":
                    str(
                        exc
                    ),
            }

    # =====================================================
    # THREAD
    # =====================================================

    def run(
        self,
    ):
        cached = (
            self.location()
        )

        if cached.get(
            "available"
        ):
            cached_copy = dict(
                cached
            )

            cached_copy[
                "cached"
            ] = True

            self.location_updated.emit(
                cached_copy
            )

        while not (
            self._stop_event
            .is_set()
        ):
            now = (
                time.monotonic()
            )

            # Internet and local AI
            if (
                self._last_health_check == 0
                or
                now
                - self._last_health_check
                >= 10
            ):
                self.health_updated.emit(
                    {
                        "internet":
                            self._check_internet(),

                        "ollama":
                            self._check_ollama(),
                    }
                )

                self._last_health_check = (
                    now
                )

            # Location
            if (
                self._force_location
                or
                now
                - self._last_location_check
                >= 21600
            ):
                self._force_location = (
                    False
                )

                location = (
                    self._detect_location()
                )

                self._set_location(
                    location
                )

                self.location_updated.emit(
                    location
                )

                self._last_location_check = (
                    now
                )

                self._force_weather = True

            # Weather
            if (
                self._force_weather
                or
                now
                - self._last_weather_check
                >= 600
            ):
                self._force_weather = False

                self.weather_updated.emit(
                    self._get_weather(
                        self.location()
                    )
                )

                self._last_weather_check = (
                    now
                )

            self._stop_event.wait(
                1.0
            )


# =========================================================
# SYSTEM MONITOR
# =========================================================

class SystemMonitor(
    QObject
):

    metrics_updated = Signal(
        dict
    )

    weather_updated = Signal(
        dict
    )

    location_updated = Signal(
        dict
    )

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._running = False

        self._health = {
            "internet":
                False,

            "ollama":
                False,
        }

        self._last_network = (
            psutil.net_io_counters()
        )

        self._last_network_time = (
            time.monotonic()
        )

        # CPU temperature does not need
        # to be queried every second.
        self._cpu_temperature_cache = None
        self._last_cpu_temperature_check = 0.0

        self._environment = (
            EnvironmentThread(
                self
            )
        )

        self._environment.health_updated.connect(
            self._on_health_updated
        )

        self._environment.weather_updated.connect(
            self.weather_updated.emit
        )

        self._environment.location_updated.connect(
            self.location_updated.emit
        )

        self._telemetry_timer = QTimer(
            self
        )

        self._telemetry_timer.setInterval(
            1000
        )

        self._telemetry_timer.timeout.connect(
            self._poll_local_metrics
        )

        try:
            psutil.cpu_percent(
                interval=None
            )

        except Exception:
            pass

    # =====================================================
    # START
    # =====================================================

    def start(
        self,
    ):
        if self._running:
            return

        self._running = True

        self._poll_local_metrics()

        self._telemetry_timer.start()

        if not (
            self._environment
            .isRunning()
        ):
            self._environment.start()

    # =====================================================
    # STOP
    # =====================================================

    def request_stop(
        self,
    ):
        self._running = False

        self._telemetry_timer.stop()

        self._environment.request_stop()

    # =====================================================
    # WAIT
    # =====================================================

    def wait(
        self,
        milliseconds=3000,
    ):
        return (
            self._environment.wait(
                milliseconds
            )
        )

    # =====================================================
    # LOCATION
    # =====================================================

    def location(
        self,
    ):
        return (
            self._environment.location()
        )

    # =====================================================
    # NETWORK SPEED
    # =====================================================

    def _network_speed(
        self,
    ):
        try:

            current = (
                psutil.net_io_counters()
            )

            now = (
                time.monotonic()
            )

            elapsed = (
                now
                - self._last_network_time
            )

            if elapsed <= 0:
                return (
                    0.0,
                    0.0,
                )

            received = max(
                0,

                current.bytes_recv
                -
                self._last_network.bytes_recv,
            )

            sent = max(
                0,

                current.bytes_sent
                -
                self._last_network.bytes_sent,
            )

            self._last_network = (
                current
            )

            self._last_network_time = (
                now
            )

            return (
                float(
                    received
                    * 8
                    / elapsed
                    / 1_000_000
                ),

                float(
                    sent
                    * 8
                    / elapsed
                    / 1_000_000
                ),
            )

        except Exception:

            return (
                0.0,
                0.0,
            )

    # =====================================================
    # CPU
    # =====================================================

    def _cpu_percent(
        self,
    ):
        try:

            return float(
                psutil.cpu_percent(
                    interval=None
                )
            )

        except Exception:

            return 0.0

    # =====================================================
    # CPU TEMPERATURE
    # =====================================================

    def _cpu_temperature_psutil(
        self,
    ):
        """
        Works on platforms/drivers where psutil
        exposes temperature sensors.
        """

        try:

            temperature_function = getattr(
                psutil,
                "sensors_temperatures",
                None,
            )

            if temperature_function is None:
                return None

            sensors = temperature_function()

            if not sensors:
                return None

            preferred = []

            fallback = []

            for group_name, entries in sensors.items():

                group_lower = str(
                    group_name
                ).lower()

                for entry in entries:

                    value = getattr(
                        entry,
                        "current",
                        None,
                    )

                    if value is None:
                        continue

                    value = float(
                        value
                    )

                    if not (
                        -20.0
                        < value
                        < 150.0
                    ):
                        continue

                    label = str(
                        getattr(
                            entry,
                            "label",
                            "",
                        )
                    ).lower()

                    text = (
                        group_lower
                        + " "
                        + label
                    )

                    if any(
                        keyword in text
                        for keyword in (
                            "cpu",
                            "package",
                            "core",
                            "tctl",
                            "tdie",
                        )
                    ):
                        preferred.append(
                            value
                        )

                    else:
                        fallback.append(
                            value
                        )

            if preferred:
                return max(
                    preferred
                )

            if fallback:
                return max(
                    fallback
                )

        except Exception:
            pass

        return None

    def _wmi_service(
        self,
        namespace,
    ):
        try:

            import win32com.client

            locator = (
                win32com.client.Dispatch(
                    "WbemScripting.SWbemLocator"
                )
            )

            service = (
                locator.ConnectServer(
                    ".",
                    namespace,
                )
            )

            return service

        except Exception:

            return None

    def _cpu_temperature_hardware_monitor(
        self,
    ):
        """
        Supports LibreHardwareMonitor and
        OpenHardwareMonitor when either exposes
        its WMI provider.
        """

        namespaces = (
            r"root\LibreHardwareMonitor",
            r"root\OpenHardwareMonitor",
        )

        preferred_names = (
            "cpu package",
            "package",
            "cpu core",
            "core max",
            "cpu",
            "tctl",
            "tdie",
        )

        for namespace in namespaces:

            service = (
                self._wmi_service(
                    namespace
                )
            )

            if service is None:
                continue

            try:

                sensors = (
                    service.ExecQuery(
                        (
                            "SELECT Name, Value "
                            "FROM Sensor "
                            "WHERE SensorType="
                            "'Temperature'"
                        )
                    )
                )

                preferred = []
                fallback = []

                for sensor in sensors:

                    try:

                        name = str(
                            sensor.Name
                        ).lower()

                        value = float(
                            sensor.Value
                        )

                    except Exception:
                        continue

                    if not (
                        -20.0
                        < value
                        < 150.0
                    ):
                        continue

                    if any(
                        keyword in name
                        for keyword
                        in preferred_names
                    ):
                        preferred.append(
                            value
                        )

                    else:
                        fallback.append(
                            value
                        )

                if preferred:
                    return max(
                        preferred
                    )

                # Do NOT automatically use a GPU/
                # motherboard temperature as CPU temp.
                # Only use fallback if there is a single
                # plausible sensor exposed.
                if len(
                    fallback
                ) == 1:
                    return fallback[0]

            except Exception:
                continue

        return None

    def _cpu_temperature_acpi(
        self,
    ):
        """
        Last-resort Windows thermal zone reading.

        Important:
        ACPI thermal zones are not guaranteed
        to represent the physical CPU package,
        so this is only used when better sensor
        sources are unavailable.
        """

        service = (
            self._wmi_service(
                r"root\wmi"
            )
        )

        if service is None:
            return None

        try:

            sensors = (
                service.ExecQuery(
                    (
                        "SELECT "
                        "CurrentTemperature "
                        "FROM "
                        "MSAcpi_ThermalZoneTemperature"
                    )
                )
            )

            values = []

            for sensor in sensors:

                try:

                    raw = float(
                        sensor.CurrentTemperature
                    )

                    # Value is tenths of Kelvin.
                    value = (
                        raw / 10.0
                        - 273.15
                    )

                except Exception:
                    continue

                if (
                    0.0
                    < value
                    < 130.0
                ):
                    values.append(
                        value
                    )

            if values:

                return max(
                    values
                )

        except Exception:
            pass

        return None

    def _read_cpu_temperature(
        self,
    ):
        """
        Try the most accurate/local methods first.
        """

        providers = (
            self._cpu_temperature_psutil,
            self._cpu_temperature_hardware_monitor,
            self._cpu_temperature_acpi,
        )

        for provider in providers:

            try:

                value = provider()

                if value is not None:

                    return round(
                        float(
                            value
                        ),
                        1,
                    )

            except Exception:
                continue

        return None

    def _cpu_temperature(
        self,
    ):
        now = (
            time.monotonic()
        )

        # Temperature doesn't need 1 Hz WMI queries.
        # Refresh every five seconds.
        if (
            now
            - self._last_cpu_temperature_check
            >= 5
        ):
            self._cpu_temperature_cache = (
                self._read_cpu_temperature()
            )

            self._last_cpu_temperature_check = (
                now
            )

        return (
            self._cpu_temperature_cache
        )

    # =====================================================
    # RAM
    # =====================================================

    def _ram_percent(
        self,
    ):
        try:

            return float(
                psutil
                .virtual_memory()
                .percent
            )

        except Exception:

            return 0.0

    # =====================================================
    # DISK
    # =====================================================

    def _disk_percent(
        self,
    ):
        try:

            drive = (
                os.environ.get(
                    "SystemDrive",
                    "C:",
                )
                + "\\"
            )

            return float(
                psutil
                .disk_usage(
                    drive
                )
                .percent
            )

        except Exception:

            return 0.0

    # =====================================================
    # BATTERY
    # =====================================================

    def _battery_info(
        self,
    ):
        try:

            battery = (
                psutil.sensors_battery()
            )

            if battery is None:

                return (
                    None,
                    None,
                )

            return (
                float(
                    battery.percent
                ),

                bool(
                    battery.power_plugged
                ),
            )

        except Exception:

            return (
                None,
                None,
            )

    # =====================================================
    # UPTIME
    # =====================================================

    def _uptime(
        self,
    ):
        try:

            seconds = max(
                0,

                int(
                    time.time()
                    -
                    psutil.boot_time()
                ),
            )

            return str(
                timedelta(
                    seconds=seconds
                )
            ).split(
                ".",
                1,
            )[0]

        except Exception:

            return "—"

    # =====================================================
    # PROCESS COUNT
    # =====================================================

    def _process_count(
        self,
    ):
        try:

            return len(
                psutil.pids()
            )

        except Exception:

            return 0

    # =====================================================
    # POLL SYSTEM
    # =====================================================

    def _poll_local_metrics(
        self,
    ):
        if not self._running:
            return

        (
            download,
            upload,
        ) = self._network_speed()

        (
            battery,
            plugged,
        ) = self._battery_info()

        metrics = {
            "cpu":
                self._cpu_percent(),

            "cpu_temp":
                self._cpu_temperature(),

            "ram":
                self._ram_percent(),

            "disk":
                self._disk_percent(),

            "battery":
                battery,

            "plugged":
                plugged,

            "download":
                download,

            "upload":
                upload,

            "uptime":
                self._uptime(),

            "processes":
                self._process_count(),

            "internet":
                self._health.get(
                    "internet",
                    False,
                ),

            "ollama":
                self._health.get(
                    "ollama",
                    False,
                ),
        }

        self.metrics_updated.emit(
            metrics
        )

    # =====================================================
    # HEALTH UPDATE
    # =====================================================

    def _on_health_updated(
        self,
        health,
    ):
        self._health.update(
            health
        )

        self._poll_local_metrics()