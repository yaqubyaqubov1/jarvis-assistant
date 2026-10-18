import html
from datetime import datetime
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QKeySequence,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.core_widget import JarvisCoreWidget
from ui.system_monitor import SystemMonitor
from ui.worker import JarvisWorker


STYLE = """
QMainWindow,
QWidget {
    background: #071014;
    color: #D8F7FF;
    font-family: Segoe UI;
}

QFrame#panel {
    background: #0B171C;
    border: 1px solid #17313A;
    border-radius: 12px;
}

QFrame#metricCard {
    background: #091419;
    border: 1px solid #1A414B;
    border-radius: 8px;
}

QLabel#title {
    color: #8EEBFF;
    font-size: 25px;
    font-weight: 600;
    letter-spacing: 4px;
}

QLabel#subtitle {
    color: #668B95;
    font-size: 11px;
    letter-spacing: 2px;
}

QLabel#status {
    color: #A8F4FF;
    font-size: 19px;
    font-weight: 600;
}

QLabel#detail {
    color: #7198A2;
    font-size: 12px;
}

QLabel#section {
    color: #62D9F2;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 2px;
}

QLabel#metricName {
    color: #6B98A3;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 1px;
}

QLabel#metricValue {
    color: #D8F9FF;
    font-size: 16px;
    font-weight: 600;
}

QLabel#weatherTitle {
    color: #75DBF0;
    font-size: 14px;
    font-weight: 600;
}

QLabel#weatherValue {
    color: #E0FBFF;
    font-size: 18px;
    font-weight: 600;
}

QLabel#locationValue {
    color: #C7F6FF;
    font-size: 15px;
    font-weight: 600;
}

QPushButton {
    background: #0E2026;
    color: #BCEFF8;
    border: 1px solid #22505C;
    border-radius: 8px;
    min-height: 36px;
    padding: 0 14px;
}

QPushButton:hover {
    background: #15313A;
    border: 1px solid #49BBD3;
}

QPushButton:pressed {
    background: #0A171B;
}

QPushButton[active="true"] {
    background: #123A43;
    border: 1px solid #67D9ED;
    color: #E8FCFF;
}

QPushButton#stopButton {
    background: #241013;
    color: #FFD4D7;
    border: 1px solid #8A323A;
    min-height: 42px;
    font-weight: 600;
    letter-spacing: 1px;
}

QPushButton#stopButton:hover {
    background: #45171D;
    border: 1px solid #FF6472;
    color: #FFFFFF;
}

QPushButton#stopButton:disabled {
    background: #1A1113;
    color: #77575B;
    border: 1px solid #4A2A2E;
}

QLineEdit {
    background: #071115;
    border: 1px solid #24444C;
    border-radius: 9px;
    color: #E3FAFF;
    padding: 9px 11px;
    font-size: 13px;
}

QLineEdit:focus {
    border: 1px solid #65D5E9;
}

QTextEdit {
    background: #071115;
    border: 1px solid #17343C;
    border-radius: 9px;
    color: #C6EDF5;
    padding: 10px;
}

QScrollArea {
    background: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background: transparent;
}

QScrollBar:vertical {
    background: #071115;
    width: 9px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: #1D4853;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #286273;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    height: 0px;
}
"""


class MetricCard(QFrame):
    def __init__(self, name, value="—", parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setMinimumHeight(62)
        self.setMaximumHeight(72)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(11, 7, 11, 8)
        layout.setSpacing(2)

        self.name_label = QLabel(name.upper())
        self.name_label.setObjectName("metricName")
        self.name_label.setMinimumHeight(15)

        self.value_label = QLabel(value)
        self.value_label.setObjectName("metricValue")
        self.value_label.setMinimumHeight(24)
        self.value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        layout.addWidget(self.name_label)
        layout.addWidget(self.value_label)

    def set_value(self, value):
        value = str(value)
        self.value_label.setText(value)
        self.setToolTip(f"{self.name_label.text()}: {value}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._detected_timezone = None
        self._detected_city = "LOCAL"
        self._shutting_down = False

        self.setWindowTitle("J.A.R.V.I.S. // Control Interface")
        self.resize(1220, 820)
        self.setMinimumSize(950, 650)
        self.setStyleSheet(STYLE)

        self.worker = JarvisWorker(self)
        self.monitor = SystemMonitor(self)

        self._build_ui()
        self._build_tray()
        self._connect_worker()
        self._connect_monitor()

        # Escape is a fast local interrupt. It does not close JARVIS.
        self.interrupt_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.interrupt_shortcut.activated.connect(self._interrupt_task)

        self.worker.start()
        self.monitor.start()

    # =====================================================
    # BUILD UI
    # =====================================================

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(14)

        # Header
        header = QHBoxLayout()
        brand = QVBoxLayout()
        brand.setSpacing(2)

        title = QLabel("J.A.R.V.I.S.")
        title.setObjectName("title")

        subtitle = QLabel("LOCAL INTELLIGENCE // DESKTOP CONTROL SYSTEM")
        subtitle.setObjectName("subtitle")

        brand.addWidget(title)
        brand.addWidget(subtitle)
        header.addLayout(brand)
        header.addStretch(1)

        self.clock = QLabel("LOCAL • --:--:--")
        self.clock.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.clock.setObjectName("detail")
        header.addWidget(self.clock)

        outer.addLayout(header)

        # Body
        body = QHBoxLayout()
        body.setSpacing(16)
        outer.addLayout(body, 1)

        # Conversation panel
        conversation_panel = QFrame()
        conversation_panel.setObjectName("panel")
        conversation_layout = QVBoxLayout(conversation_panel)
        conversation_layout.setContentsMargins(16, 16, 16, 16)
        conversation_layout.setSpacing(10)

        section = QLabel("CONVERSATION")
        section.setObjectName("section")
        conversation_layout.addWidget(section)

        self.conversation = QTextEdit()
        self.conversation.setReadOnly(True)
        self.conversation.setPlaceholderText(
            "Voice and typed interactions will appear here."
        )
        conversation_layout.addWidget(self.conversation, 1)

        input_row = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText(
            "Type a command directly to JARVIS..."
        )
        self.command_input.returnPressed.connect(self._send_text)
        input_row.addWidget(self.command_input, 1)

        send_button = QPushButton("SEND")
        send_button.clicked.connect(self._send_text)
        input_row.addWidget(send_button)
        conversation_layout.addLayout(input_row)

        body.addWidget(conversation_panel, 3)

        # Scrollable dashboard
        self.dashboard_scroll = QScrollArea()
        self.dashboard_scroll.setWidgetResizable(True)
        self.dashboard_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.dashboard_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.dashboard_scroll.setFrameShape(QFrame.NoFrame)
        self.dashboard_scroll.setMinimumWidth(375)
        self.dashboard_scroll.setMaximumWidth(435)

        dashboard_container = QWidget()
        dashboard_container.setMinimumWidth(355)
        dashboard_outer = QVBoxLayout(dashboard_container)
        dashboard_outer.setContentsMargins(0, 0, 6, 0)
        dashboard_outer.setSpacing(0)

        side_panel = QFrame()
        side_panel.setObjectName("panel")
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(16, 15, 16, 18)
        side_layout.setSpacing(10)

        dashboard_outer.addWidget(side_panel)
        dashboard_outer.addStretch(1)
        self.dashboard_scroll.setWidget(dashboard_container)
        body.addWidget(self.dashboard_scroll, 2)

        # Core
        self.core_widget = JarvisCoreWidget()
        self.core_widget.setMinimumHeight(190)
        self.core_widget.setMaximumHeight(210)
        self.core_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.core_widget.cancel_requested.connect(self._interrupt_task)
        side_layout.addWidget(self.core_widget)

        self.status_label = QLabel("BOOTING")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setObjectName("status")
        self.status_label.setMinimumHeight(26)
        side_layout.addWidget(self.status_label)

        self.detail_label = QLabel("Initialising local systems...")
        self.detail_label.setAlignment(Qt.AlignCenter)
        self.detail_label.setWordWrap(True)
        self.detail_label.setObjectName("detail")
        self.detail_label.setMinimumHeight(20)
        side_layout.addWidget(self.detail_label)

        # Location
        section = QLabel("LOCATION")
        section.setObjectName("section")
        side_layout.addWidget(section)

        location_card = QFrame()
        location_card.setObjectName("metricCard")
        location_card.setMinimumHeight(77)
        location_layout = QVBoxLayout(location_card)
        location_layout.setContentsMargins(12, 9, 12, 9)
        location_layout.setSpacing(4)

        self.location_value_label = QLabel("DETECTING...")
        self.location_value_label.setObjectName("locationValue")
        self.location_value_label.setMinimumHeight(21)
        location_layout.addWidget(self.location_value_label)

        self.location_detail_label = QLabel("Determining approximate location.")
        self.location_detail_label.setWordWrap(True)
        self.location_detail_label.setObjectName("detail")
        location_layout.addWidget(self.location_detail_label)
        side_layout.addWidget(location_card)

        # Weather
        section = QLabel("ENVIRONMENT")
        section.setObjectName("section")
        side_layout.addWidget(section)

        weather_card = QFrame()
        weather_card.setObjectName("metricCard")
        weather_card.setMinimumHeight(112)
        weather_layout = QVBoxLayout(weather_card)
        weather_layout.setContentsMargins(12, 9, 12, 9)
        weather_layout.setSpacing(4)

        self.weather_location_label = QLabel("WEATHER")
        self.weather_location_label.setObjectName("weatherTitle")
        self.weather_location_label.setMinimumHeight(20)
        weather_layout.addWidget(self.weather_location_label)

        self.weather_value_label = QLabel("Retrieving conditions...")
        self.weather_value_label.setObjectName("weatherValue")
        self.weather_value_label.setMinimumHeight(28)
        weather_layout.addWidget(self.weather_value_label)

        self.weather_detail_label = QLabel("Waiting for weather service.")
        self.weather_detail_label.setWordWrap(True)
        self.weather_detail_label.setObjectName("detail")
        self.weather_detail_label.setMinimumHeight(30)
        weather_layout.addWidget(self.weather_detail_label)
        side_layout.addWidget(weather_card)

        # Telemetry
        section = QLabel("SYSTEM TELEMETRY")
        section.setObjectName("section")
        side_layout.addWidget(section)

        telemetry_container = QWidget()
        telemetry_layout = QGridLayout(telemetry_container)
        telemetry_layout.setContentsMargins(0, 0, 0, 0)
        telemetry_layout.setHorizontalSpacing(8)
        telemetry_layout.setVerticalSpacing(8)
        telemetry_layout.setColumnStretch(0, 1)
        telemetry_layout.setColumnStretch(1, 1)

        self.cpu_temp_card = MetricCard("CPU Temp")
        self.date_card = MetricCard("Date")
        self.cpu_card = MetricCard("CPU")
        self.ram_card = MetricCard("RAM")
        self.disk_card = MetricCard("Disk")
        self.battery_card = MetricCard("Battery")
        self.internet_card = MetricCard("Internet")
        self.ollama_card = MetricCard("Local AI")
        self.download_card = MetricCard("Download")
        self.upload_card = MetricCard("Upload")
        self.uptime_card = MetricCard("Uptime")
        self.process_card = MetricCard("Processes")

        cards = [
            self.cpu_temp_card,
            self.date_card,
            self.cpu_card,
            self.ram_card,
            self.disk_card,
            self.battery_card,
            self.internet_card,
            self.ollama_card,
            self.download_card,
            self.upload_card,
            self.uptime_card,
            self.process_card,
        ]

        for index, card in enumerate(cards):
            telemetry_layout.addWidget(card, index // 2, index % 2)

        side_layout.addWidget(telemetry_container)

        # Core controls
        section = QLabel("CORE CONTROLS")
        section.setObjectName("section")
        side_layout.addWidget(section)

        controls_grid = QGridLayout()
        controls_grid.setSpacing(8)

        self.assistant_button = QPushButton("ASSISTANT: ON")
        self.assistant_button.setProperty("active", True)
        self.assistant_button.clicked.connect(self._toggle_assistant)

        self.mic_button = QPushButton("MIC: ON")
        self.mic_button.setProperty("active", True)
        self.mic_button.clicked.connect(self._toggle_microphone)

        self.voice_button = QPushButton("VOICE: ON")
        self.voice_button.setProperty("active", True)
        self.voice_button.clicked.connect(self._toggle_voice)

        self.sfx_button = QPushButton("SFX: ON")
        self.sfx_button.setProperty("active", True)
        self.sfx_button.clicked.connect(self._toggle_sfx)

        controls_grid.addWidget(self.assistant_button, 0, 0)
        controls_grid.addWidget(self.mic_button, 0, 1)
        controls_grid.addWidget(self.voice_button, 1, 0)
        controls_grid.addWidget(self.sfx_button, 1, 1)

        self.stop_button = QPushButton("STOP J.A.R.V.I.S.")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setToolTip("Completely shut down JARVIS.")
        self.stop_button.clicked.connect(self._request_full_shutdown)
        controls_grid.addWidget(self.stop_button, 2, 0, 1, 2)

        side_layout.addLayout(controls_grid)

        self.core_label = QLabel("CORE: STARTING")
        self.core_label.setObjectName("detail")
        self.core_label.setMinimumHeight(20)
        side_layout.addWidget(self.core_label)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_clock)
        self.timer.start(1000)
        self._update_clock()

    # =====================================================
    # TRAY
    # =====================================================

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        self.tray.setToolTip("J.A.R.V.I.S.")

        menu = QMenu(self)

        show_action = QAction("Open JARVIS", self)
        show_action.triggered.connect(self._show_from_tray)
        menu.addAction(show_action)

        self.tray_mic_action = QAction("Mute microphone", self)
        self.tray_mic_action.triggered.connect(self._toggle_microphone)
        menu.addAction(self.tray_mic_action)

        self.tray_pause_action = QAction("Pause assistant", self)
        self.tray_pause_action.triggered.connect(self._toggle_assistant)
        menu.addAction(self.tray_pause_action)

        self.tray_sfx_action = QAction("Disable sound effects", self)
        self.tray_sfx_action.triggered.connect(self._toggle_sfx)
        menu.addAction(self.tray_sfx_action)

        menu.addSeparator()

        stop_action = QAction("Stop JARVIS", self)
        stop_action.triggered.connect(self._request_full_shutdown)
        menu.addAction(stop_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    # =====================================================
    # CONNECTIONS
    # =====================================================

    def _connect_worker(self):
        self.worker.state_changed.connect(self._state_changed)
        self.worker.user_message.connect(
            lambda text: self._append_message("YOU", text)
        )
        self.worker.jarvis_message.connect(
            lambda text: self._append_message("JARVIS", text)
        )
        self.worker.system_message.connect(
            lambda text: self._append_message("SYSTEM", text)
        )
        self.worker.ready_changed.connect(self._ready_changed)
        self.worker.microphone_changed.connect(self._microphone_changed)
        self.worker.assistant_enabled_changed.connect(
            self._assistant_enabled_changed
        )
        self.worker.sfx_enabled_changed.connect(self._sfx_enabled_changed)
        self.worker.task_busy_changed.connect(self._task_busy_changed)
        self.worker.confirmation_requested.connect(self._confirmation_requested)
        self.worker.fatal_error.connect(self._fatal_error)

    def _connect_monitor(self):
        self.monitor.metrics_updated.connect(self._metrics_updated)
        self.monitor.weather_updated.connect(self._weather_updated)
        self.monitor.location_updated.connect(self._location_updated)

    # =====================================================
    # MONITOR DATA
    # =====================================================

    def _location_updated(self, location):
        if not location.get("available"):
            self.location_value_label.setText("UNAVAILABLE")
            self.location_detail_label.setText(
                location.get("message", "Could not determine location.")
            )
            return

        city = str(location.get("city", ""))
        region = str(location.get("region", ""))
        timezone = str(location.get("timezone", ""))
        display = str(location.get("display", city))

        if city:
            self._detected_city = city

        if timezone:
            try:
                ZoneInfo(timezone)
                self._detected_timezone = timezone
            except Exception:
                self._detected_timezone = None

        self.location_value_label.setText(display.upper())

        details = []
        if region:
            details.append(region)
        if timezone:
            details.append(timezone)
        if location.get("cached"):
            details.append("cached")

        self.location_detail_label.setText(
            "  •  ".join(details) or "Approximate location detected."
        )
        self._update_clock()

    def _weather_updated(self, weather):
        if weather.get("available"):
            self.weather_location_label.setText(
                str(weather.get("location", "Weather")).upper()
            )
            self.weather_value_label.setText(
                f"{weather.get('temperature', '?')}°C  •  "
                f"{weather.get('description', '')}"
            )
            self.weather_detail_label.setText(
                f"Feels like {weather.get('feels_like', '?')}°C"
                f"   •   Humidity {weather.get('humidity', '?')}%"
                f"   •   Wind {weather.get('wind', '?')} km/h"
            )
        else:
            self.weather_location_label.setText("WEATHER")
            self.weather_value_label.setText("Unavailable")
            message = weather.get("message", "Weather unavailable.")
            details = weather.get("details")
            if details:
                message += f"\n{details}"
            self.weather_detail_label.setText(message)

    def _metrics_updated(self, data):
        cpu_temp = data.get("cpu_temp")
        self.cpu_temp_card.set_value(
            "N/A" if cpu_temp is None else f"{float(cpu_temp):.1f}°C"
        )

        self.cpu_card.set_value(f"{float(data.get('cpu', 0) or 0):.0f}%")
        self.ram_card.set_value(f"{float(data.get('ram', 0) or 0):.0f}%")
        self.disk_card.set_value(f"{float(data.get('disk', 0) or 0):.0f}%")

        battery = data.get("battery")
        if battery is None:
            self.battery_card.set_value("N/A")
        else:
            suffix = " ⚡" if data.get("plugged") else ""
            self.battery_card.set_value(f"{float(battery):.0f}%{suffix}")

        self.internet_card.set_value(
            "ONLINE" if data.get("internet") else "OFFLINE"
        )
        self.ollama_card.set_value(
            "ONLINE" if data.get("ollama") else "OFFLINE"
        )
        self.download_card.set_value(
            f"{float(data.get('download', 0) or 0):.2f} Mbps"
        )
        self.upload_card.set_value(
            f"{float(data.get('upload', 0) or 0):.2f} Mbps"
        )
        self.uptime_card.set_value(data.get("uptime", "—"))
        self.process_card.set_value(data.get("processes", "—"))

    # =====================================================
    # CLOCK
    # =====================================================

    def _current_time(self):
        if self._detected_timezone:
            try:
                return datetime.now(ZoneInfo(self._detected_timezone))
            except Exception:
                pass
        return datetime.now()

    def _update_clock(self):
        now = self._current_time()
        self.clock.setText(
            f"{self._detected_city.upper()}  •  "
            f"{now.strftime('%A')}  •  {now.strftime('%H:%M:%S')}"
        )

        if hasattr(self, "date_card"):
            self.date_card.set_value(now.strftime("%d %b %Y"))

    # =====================================================
    # CONVERSATION
    # =====================================================

    def _append_message(self, speaker, text):
        text = str(text).strip()
        if not text:
            return

        colours = {
            "YOU": "#8EEBFF",
            "JARVIS": "#B8DCE4",
            "SYSTEM": "#718E96",
        }

        timestamp = self._current_time().strftime("%H:%M")
        safe_text = html.escape(text).replace("\n", "<br>")
        colour = colours.get(speaker, "#C8E8EE")

        self.conversation.append(
            f'<span style="color:#4E727A">{timestamp}</span> '
            f'<b style="color:{colour}">{speaker}</b><br>'
            f'<span style="color:#C8E8EE">{safe_text}</span><br>'
        )

        bar = self.conversation.verticalScrollBar()
        bar.setValue(bar.maximum())

    # =====================================================
    # JARVIS STATE
    # =====================================================

    def _state_changed(self, name, detail):
        self.status_label.setText(name)
        self.detail_label.setText(detail or "—")
        self.core_widget.set_state(name, detail)

    def _ready_changed(self, ready):
        self.core_label.setText("CORE: ONLINE" if ready else "CORE: OFFLINE")

    def _task_busy_changed(self, busy):
        self.core_widget.set_task_busy(bool(busy))

    # =====================================================
    # CONTROL BUTTONS
    # =====================================================

    @staticmethod
    def _refresh_button(button):
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()

    def _microphone_changed(self, enabled):
        self.mic_button.setText("MIC: ON" if enabled else "MIC: OFF")
        self.mic_button.setProperty("active", enabled)
        self._refresh_button(self.mic_button)
        self.tray_mic_action.setText(
            "Mute microphone" if enabled else "Enable microphone"
        )

    def _assistant_enabled_changed(self, enabled):
        self.assistant_button.setText(
            "ASSISTANT: ON" if enabled else "ASSISTANT: PAUSED"
        )
        self.assistant_button.setProperty("active", enabled)
        self._refresh_button(self.assistant_button)
        self.tray_pause_action.setText(
            "Pause assistant" if enabled else "Resume assistant"
        )

    def _sfx_enabled_changed(self, enabled):
        self.sfx_button.setText("SFX: ON" if enabled else "SFX: OFF")
        self.sfx_button.setProperty("active", enabled)
        self._refresh_button(self.sfx_button)
        self.tray_sfx_action.setText(
            "Disable sound effects" if enabled else "Enable sound effects"
        )

    def _toggle_microphone(self):
        self.worker.set_microphone_enabled(
            not self.worker.microphone_enabled()
        )

    def _toggle_assistant(self):
        self.worker.set_assistant_enabled(
            not self.worker.assistant_enabled()
        )

    def _toggle_voice(self):
        enabled = not self.worker.voice_enabled()
        self.worker.set_voice_enabled(enabled)
        self.voice_button.setText("VOICE: ON" if enabled else "VOICE: OFF")
        self.voice_button.setProperty("active", enabled)
        self._refresh_button(self.voice_button)

    def _toggle_sfx(self):
        self.worker.set_sfx_enabled(
            not self.worker.sfx_enabled()
        )

    def _interrupt_task(self):
        if self.worker.interrupt_current_task():
            self.status_label.setText("INTERRUPTING")
            self.detail_label.setText("Cancelling current task...")
            self.core_widget.set_state("ERROR", "Cancelling current task...")

    # =====================================================
    # COMMANDS / CONFIRMATION
    # =====================================================

    def _send_text(self):
        text = self.command_input.text().strip()
        if not text:
            return

        self.command_input.clear()
        self.worker.submit_text(text)

    def _confirmation_requested(self, message):
        box = QMessageBox(self)
        box.setWindowTitle("J.A.R.V.I.S. // Confirmation")
        box.setText(message)
        box.setInformativeText("This action requires explicit approval.")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)

        self.worker.resolve_confirmation(
            box.exec() == QMessageBox.Yes
        )

    # =====================================================
    # ERRORS
    # =====================================================

    def _fatal_error(self, message):
        self._append_message("SYSTEM", f"Fatal error: {message}")
        QMessageBox.critical(self, "J.A.R.V.I.S. Error", message)

    # =====================================================
    # TRAY
    # =====================================================

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()

    # =====================================================
    # FULL SHUTDOWN
    # =====================================================

    def _request_full_shutdown(self):
        if self._shutting_down:
            return

        box = QMessageBox(self)
        box.setWindowTitle("J.A.R.V.I.S. // Shutdown")
        box.setIcon(QMessageBox.Warning)
        box.setText("Shut down J.A.R.V.I.S. completely?")
        box.setInformativeText(
            "Voice detection, reminders, telemetry, the system tray "
            "service and the control interface will all stop."
        )
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)

        if box.exec() == QMessageBox.Yes:
            self._quit_application()

    def closeEvent(self, event: QCloseEvent):
        if self._shutting_down:
            event.accept()
            return

        event.ignore()
        self.hide()
        self.tray.showMessage(
            "J.A.R.V.I.S.",
            "JARVIS remains active in the system tray.",
            QSystemTrayIcon.Information,
            2500,
        )

    def _quit_application(self):
        if self._shutting_down:
            return

        self._shutting_down = True
        self.status_label.setText("SHUTTING DOWN")
        self.detail_label.setText("Stopping J.A.R.V.I.S. systems...")
        self.core_label.setText("CORE: SHUTTING DOWN")
        self.core_widget.set_task_busy(False)
        self.stop_button.setText("SHUTTING DOWN...")
        self.stop_button.setEnabled(False)
        self.command_input.setEnabled(False)
        QApplication.processEvents()

        self.tray.hide()

        try:
            self.monitor.request_stop()
        except Exception:
            pass

        try:
            self.worker.request_stop()
        except Exception:
            pass

        try:
            self.monitor.wait(3000)
        except Exception:
            pass

        try:
            if not self.worker.wait(5000):
                self.worker.terminate()
                self.worker.wait(1500)
        except Exception:
            pass

        QApplication.instance().quit()
