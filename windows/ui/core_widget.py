import math

from PySide6.QtCore import (
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QMouseEvent,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QWidget


STATE_COLORS = {
    "SLEEPING": QColor("#376874"),
    "LISTENING": QColor("#66E5FF"),
    "TRANSCRIBING": QColor("#75D6F0"),
    "THINKING": QColor("#8CAEFF"),
    "PLANNING": QColor("#A38CFF"),
    "EXECUTING": QColor("#62F0C3"),
    "VERIFYING": QColor("#7DE3B5"),
    "DONE": QColor("#7CFFBC"),
    "ERROR": QColor("#FF6C7A"),
}

CANCEL_COLOR = QColor("#FF4455")


class JarvisCoreWidget(QWidget):
    """
    Animated JARVIS core.

    The core becomes a cancel control ONLY while a task is active:
    - idle / sleeping: hovering has no effect
    - task active + hover: core turns red and shows "Cancel task"
    - task active + click: emits cancel_requested

    Escape can still be handled by the main window as a backup cancel key.
    """

    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._state = "SLEEPING"
        self._detail = ""
        self._angle = 0.0
        self._pulse = 0.0

        self._hovering_core = False
        self._task_busy = False

        self.setMinimumSize(220, 220)
        self.setMouseTracking(True)
        self.setCursor(Qt.ArrowCursor)
        self.setToolTip("")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(35)

    # =====================================================
    # PUBLIC API
    # =====================================================

    def set_state(self, state, detail=""):
        self._state = str(state).upper().strip()
        self._detail = str(detail)
        self.update()

    def set_task_busy(self, busy):
        """
        Enable or disable the core's cancel interaction.

        When busy becomes False, any current red-hover state is
        immediately removed even if the mouse is still over the core.
        """

        busy = bool(busy)

        if busy == self._task_busy:
            return

        self._task_busy = busy

        if not busy:
            self._hovering_core = False
            self.setCursor(Qt.ArrowCursor)
            self.setToolTip("")

        else:
            self.setToolTip(
                "Click the JARVIS core to cancel the current task. "
                "Esc also cancels the task."
            )

            # If the task begins while the cursor is already sitting on
            # the circle, activate the cancel hover immediately instead
            # of waiting for the mouse to move again.
            local_position = self.mapFromGlobal(
                QCursor.pos()
            )

            inside = (
                self.rect().contains(
                    local_position
                )
                and
                self._point_is_inside_core(
                    local_position.x(),
                    local_position.y(),
                )
            )

            self._hovering_core = inside

            self.setCursor(
                Qt.PointingHandCursor
                if inside
                else Qt.ArrowCursor
            )

        self.update()

    # =====================================================
    # CANCEL STATE
    # =====================================================

    def _cancel_hover_active(self):
        return (
            self._task_busy
            and self._hovering_core
        )

    # =====================================================
    # GEOMETRY
    # =====================================================

    def _core_geometry(self):
        width = self.width()
        height = self.height()

        size = min(
            width,
            height,
        )

        center_x = width / 2.0
        center_y = height / 2.0

        outer_radius = size * 0.46

        return (
            center_x,
            center_y,
            size,
            outer_radius,
        )

    def _point_is_inside_core(self, x, y):
        center_x, center_y, _, radius = (
            self._core_geometry()
        )

        dx = (
            float(x)
            - center_x
        )

        dy = (
            float(y)
            - center_y
        )

        return (
            dx * dx
            + dy * dy
        ) <= (
            radius * radius
        )

    # =====================================================
    # MOUSE EVENTS
    # =====================================================

    def mouseMoveEvent(
        self,
        event: QMouseEvent,
    ):
        # While JARVIS is not doing a task,
        # hovering over the reactor does nothing.
        if not self._task_busy:

            if self._hovering_core:

                self._hovering_core = False

                self.setCursor(
                    Qt.ArrowCursor
                )

                self.update()

            super().mouseMoveEvent(
                event
            )

            return

        position = (
            event.position()
        )

        inside = (
            self._point_is_inside_core(
                position.x(),
                position.y(),
            )
        )

        if (
            inside
            != self._hovering_core
        ):
            self._hovering_core = (
                inside
            )

            self.setCursor(
                Qt.PointingHandCursor
                if inside
                else Qt.ArrowCursor
            )

            self.update()

        super().mouseMoveEvent(
            event
        )

    def leaveEvent(
        self,
        event,
    ):
        if self._hovering_core:

            self._hovering_core = False

            self.setCursor(
                Qt.ArrowCursor
            )

            self.update()

        super().leaveEvent(
            event
        )

    def mousePressEvent(
        self,
        event: QMouseEvent,
    ):
        # Clicking the reactor while idle
        # should do absolutely nothing.
        if not self._task_busy:

            super().mousePressEvent(
                event
            )

            return

        if (
            event.button()
            == Qt.LeftButton
            and
            self._point_is_inside_core(
                event.position().x(),
                event.position().y(),
            )
        ):
            self.cancel_requested.emit()

            event.accept()

            return

        super().mousePressEvent(
            event
        )

    # =====================================================
    # ANIMATION
    # =====================================================

    def _tick(self):
        speed = {
            "SLEEPING":
                0.6,

            "LISTENING":
                2.4,

            "TRANSCRIBING":
                1.8,

            "THINKING":
                2.0,

            "PLANNING":
                2.3,

            "EXECUTING":
                2.7,

            "VERIFYING":
                2.0,

            "DONE":
                0.9,

            "ERROR":
                1.2,

        }.get(
            self._state,
            1.0,
        )

        # Only accelerate when the cancel
        # interaction is genuinely active.
        if self._cancel_hover_active():

            speed = max(
                speed,
                3.2,
            )

        self._angle = (
            self._angle
            + speed
        ) % 360

        self._pulse += (
            0.07
        )

        self.update()

    # =====================================================
    # DRAWING
    # =====================================================

    def paintEvent(
        self,
        event,
    ):
        painter = QPainter(
            self
        )

        painter.setRenderHint(
            QPainter.Antialiasing,
            True,
        )

        width = self.width()
        height = self.height()

        size = min(
            width,
            height,
        )

        center_x = (
            width
            / 2.0
        )

        center_y = (
            height
            / 2.0
        )

        normal_color = (
            STATE_COLORS.get(
                self._state,
                QColor(
                    "#66E5FF"
                ),
            )
        )

        cancel_hover = (
            self._cancel_hover_active()
        )

        # Red is used ONLY while a task is
        # active AND the cursor is on the core.
        color = (
            CANCEL_COLOR
            if cancel_hover
            else normal_color
        )

        pulse = (
            math.sin(
                self._pulse
            )
            + 1.0
        ) / 2.0

        # =================================================
        # OUTER DIM RING
        # =================================================

        painter.setPen(
            QPen(
                QColor(
                    color.red(),
                    color.green(),
                    color.blue(),
                    (
                        65
                        if cancel_hover
                        else 55
                    ),
                ),
                1.0,
            )
        )

        radius = (
            size
            * 0.43
        )

        painter.drawEllipse(
            int(
                center_x
                - radius
            ),
            int(
                center_y
                - radius
            ),
            int(
                radius
                * 2
            ),
            int(
                radius
                * 2
            ),
        )

        # =================================================
        # ROTATING OUTER ARCS
        # =================================================

        painter.setPen(
            QPen(
                QColor(
                    color.red(),
                    color.green(),
                    color.blue(),
                    (
                        230
                        if cancel_hover
                        else 190
                    ),
                ),
                (
                    4.0
                    if cancel_hover
                    else 3.0
                ),
            )
        )

        arc_radius = (
            size
            * 0.39
        )

        rect_x = int(
            center_x
            - arc_radius
        )

        rect_y = int(
            center_y
            - arc_radius
        )

        rect_size = int(
            arc_radius
            * 2
        )

        painter.drawArc(
            rect_x,
            rect_y,
            rect_size,
            rect_size,
            int(
                self._angle
                * 16
            ),
            int(
                92
                * 16
            ),
        )

        painter.drawArc(
            rect_x,
            rect_y,
            rect_size,
            rect_size,
            int(
                (
                    self._angle
                    + 180
                )
                * 16
            ),
            int(
                58
                * 16
            ),
        )

        # =================================================
        # INNER ARCS
        # =================================================

        painter.setPen(
            QPen(
                QColor(
                    color.red(),
                    color.green(),
                    color.blue(),
                    (
                        175
                        if cancel_hover
                        else 120
                    ),
                ),
                (
                    2.4
                    if cancel_hover
                    else 2.0
                ),
            )
        )

        inner_radius = (
            size
            * 0.30
        )

        inner_x = int(
            center_x
            - inner_radius
        )

        inner_y = int(
            center_y
            - inner_radius
        )

        inner_size = int(
            inner_radius
            * 2
        )

        painter.drawArc(
            inner_x,
            inner_y,
            inner_size,
            inner_size,
            int(
                (
                    -self._angle
                    * 1.4
                )
                * 16
            ),
            int(
                125
                * 16
            ),
        )

        painter.drawArc(
            inner_x,
            inner_y,
            inner_size,
            inner_size,
            int(
                (
                    -self._angle
                    * 1.4
                    + 190
                )
                * 16
            ),
            int(
                80
                * 16
            ),
        )

        # =================================================
        # CORE GLOW
        # =================================================

        glow_alpha = int(
            (
                80
                if cancel_hover
                else 50
            )
            +
            pulse
            * (
                120
                if cancel_hover
                else 90
            )
        )

        painter.setPen(
            Qt.NoPen
        )

        painter.setBrush(
            QColor(
                color.red(),
                color.green(),
                color.blue(),
                min(
                    glow_alpha,
                    220,
                ),
            )
        )

        core_radius = (
            size
            * (
                0.135
                +
                pulse
                * (
                    0.018
                    if cancel_hover
                    else 0.012
                )
            )
        )

        painter.drawEllipse(
            int(
                center_x
                - core_radius
            ),
            int(
                center_y
                - core_radius
            ),
            int(
                core_radius
                * 2
            ),
            int(
                core_radius
                * 2
            ),
        )

        # =================================================
        # CORE OUTLINE
        # =================================================

        painter.setBrush(
            Qt.NoBrush
        )

        painter.setPen(
            QPen(
                color,
                (
                    3.0
                    if cancel_hover
                    else 2.0
                ),
            )
        )

        outline_radius = (
            size
            * 0.17
        )

        painter.drawEllipse(
            int(
                center_x
                - outline_radius
            ),
            int(
                center_y
                - outline_radius
            ),
            int(
                outline_radius
                * 2
            ),
            int(
                outline_radius
                * 2
            ),
        )

        # =================================================
        # CENTER TEXT
        # =================================================

        if cancel_hover:

            text = (
                "Cancel task"
            )

            text_color = QColor(
                "#FFF3F4"
            )

        else:

            text = (
                self._state
            )

            text_color = QColor(
                "#E6FCFF"
            )

        painter.setPen(
            text_color
        )

        font_size = max(
            8,
            int(
                size
                * (
                    0.038
                    if cancel_hover
                    else 0.045
                )
            ),
        )

        font = QFont(
            "Segoe UI",
            font_size,
        )

        font.setBold(
            True
        )

        painter.setFont(
            font
        )

        text_rect_height = int(
            size
            * 0.16
        )

        painter.drawText(
            0,
            int(
                center_y
                - text_rect_height / 2
            ),
            width,
            text_rect_height,
            Qt.AlignCenter,
            text,
        )