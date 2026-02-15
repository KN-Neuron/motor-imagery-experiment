from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QFont


class CalibrationView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.pending_events = []
        self.setStyleSheet("background-color: rgb(30, 30, 40);")

    def update_content(self):
        """Update the view content"""
        self.update()
    
    def paintEvent(self, event):
        """Custom paint for calibration content"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # TODO: Implement calibration rendering
        painter.setPen(QColor(255, 255, 255))
        font = QFont('Arial', 24)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Calibration View\n(TODO)")

    def get_pending_events(self) -> list:
        """Get and clear pending events"""
        events = self.pending_events.copy()
        self.pending_events.clear()
        return events
