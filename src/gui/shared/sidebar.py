from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont


class SidebarButton(QWidget):
    """Icon button for the sidebar — draws icon + small label via QPainter."""

    clicked = pyqtSignal()

    def __init__(self, icon: str, label: str, tooltip: str, parent=None):
        super().__init__(parent)
        self.icon = icon
        self.label = label
        self.is_hovered = False
        self.is_active = False
        self.setFixedSize(60, 58)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_active(self, active: bool):
        self.is_active = active
        self.update()

    def set_icon(self, icon: str):
        self.icon = icon
        self.update()

    def set_label(self, label: str):
        self.label = label
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # Hover background
        if self.is_hovered:
            painter.setBrush(QColor(80, 85, 140, 90))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(5, 3, w - 10, h - 6, 9, 9)

        # Active: left accent bar
        if self.is_active:
            painter.setBrush(QColor(120, 150, 255))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(0, 14, 3, h - 28, 2, 2)

        # Icon
        if self.is_active:
            icon_color = QColor(210, 220, 255)
        elif self.is_hovered:
            icon_color = QColor(190, 200, 240)
        else:
            icon_color = QColor(120, 125, 160)

        icon_font = QFont("Segoe UI Symbol", 19)
        painter.setFont(icon_font)
        painter.setPen(icon_color)
        painter.drawText(0, 2, w, h - 16, Qt.AlignmentFlag.AlignHCenter, self.icon)

        # Label
        label_color = QColor(160, 165, 200) if self.is_hovered else QColor(80, 85, 115)
        label_font = QFont("Segoe UI", 7, QFont.Weight.Medium)
        painter.setFont(label_font)
        painter.setPen(label_color)
        painter.drawText(0, h - 18, w, 14, Qt.AlignmentFlag.AlignHCenter, self.label)

    def enterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class Sidebar(QWidget):
    """Sidebar with common controls."""

    fullscreen_toggled = pyqtSignal()
    pause_toggled = pyqtSignal()
    back_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_fullscreen = False
        self.is_paused = False
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedWidth(68)
        self.setStyleSheet("Sidebar { background-color: rgb(13, 13, 22); }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 52, 4, 14)
        layout.setSpacing(4)

        self.fullscreen_btn = SidebarButton("▢", "VIEW", "Toggle Fullscreen")
        self.fullscreen_btn.clicked.connect(self._on_fullscreen_clicked)
        layout.addWidget(self.fullscreen_btn)

        layout.addStretch()

        self.pause_btn = SidebarButton("⏸", "PAUSE", "Pause")
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        self.pause_btn.hide()
        layout.addWidget(self.pause_btn)

        self.back_btn = SidebarButton("←", "BACK", "Back to Menu")
        self.back_btn.clicked.connect(self._on_back_clicked)
        self.back_btn.hide()
        layout.addWidget(self.back_btn)

        self.quit_btn = SidebarButton("✕", "QUIT", "Quit application")
        self.quit_btn.clicked.connect(self.quit_requested.emit)
        self.quit_btn.hide()
        layout.addWidget(self.quit_btn)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()

        # Top branding area
        painter.setBrush(QColor(18, 18, 32))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, w, 44)

        # Top accent line
        painter.setBrush(QColor(90, 110, 220))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, w, 3)

        # Hexagon logo character
        hex_font = QFont("Segoe UI Symbol", 18, QFont.Weight.Bold)
        painter.setFont(hex_font)
        painter.setPen(QColor(110, 130, 240))
        painter.drawText(0, 3, w, 41, Qt.AlignmentFlag.AlignCenter, "⬡")

        # Right edge separator
        painter.setPen(QColor(255, 255, 255, 18))
        painter.drawLine(w - 1, 0, w - 1, self.height())

    def _on_fullscreen_clicked(self):
        self.is_fullscreen = not self.is_fullscreen
        self.fullscreen_btn.set_active(self.is_fullscreen)
        self.fullscreen_btn.set_icon("▣" if self.is_fullscreen else "▢")
        self.fullscreen_toggled.emit()

    def _on_pause_clicked(self):
        self.is_paused = not self.is_paused
        self.pause_btn.set_active(self.is_paused)
        self.pause_btn.set_icon("▶" if self.is_paused else "⏸")
        self.pause_btn.set_label("RESUME" if self.is_paused else "PAUSE")
        self.pause_btn.setToolTip("Resume" if self.is_paused else "Pause")
        print(f"[Sidebar] Pause toggled: {self.is_paused}")
        self.pause_toggled.emit()

    def _on_back_clicked(self):
        self.back_requested.emit()

    def reset_pause(self):
        if self.is_paused:
            self._on_pause_clicked()

    def set_buttons_visibility(self, show_pause: bool = False, show_back: bool = False, show_quit: bool = False):
        self.pause_btn.setVisible(show_pause)
        self.back_btn.setVisible(show_back)
        self.quit_btn.setVisible(show_quit)

    def update_states(self, is_fullscreen: bool):
        self.is_fullscreen = is_fullscreen
        self.fullscreen_btn.set_active(is_fullscreen)
        self.fullscreen_btn.set_icon("▣" if is_fullscreen else "▢")

    def reset_pause(self):
        self.is_paused = False
        self.pause_btn.set_active(False)
        self.pause_btn.set_icon("⏸")
        self.pause_btn.set_label("PAUSE")
        self.pause_btn.setToolTip("Pause")
