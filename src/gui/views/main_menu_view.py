from enum import Enum
from PyQt6.QtWidgets import QWidget, QPushButton, QLabel
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import QApplication
from ..shared.button import Button
import os


class MainMenuEvent(Enum):
    TOGGLE_FULLSCREEN = "toggle_fullscreen"
    EXPERIMENT_BTN_CLICKED = "experiment_btn_clicked"
    CALIBRATION_BTN_CLICKED = "calibration_btn_clicked"
    QUIT = "quit"

class MainMenuView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.experiment_btn: Button = None
        self.calibration_btn: Button = None
        self.pending_events = []
        self.headset_connected = False
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the UI components"""
        # Set background color
        self.setStyleSheet("background-color: rgb(30, 30, 40);")        
        
        # Create main buttons (will be positioned in update_content)
        def on_experiment_click():
            mods = QApplication.keyboardModifiers()
            alt_pressed = bool(mods & Qt.KeyboardModifier.AltModifier)
            print(f"[DEBUG] Experiment button clicked, Alt pressed: {alt_pressed}")
            self.pending_events.append((MainMenuEvent.EXPERIMENT_BTN_CLICKED, alt_pressed))
        
        # Create buttons with temporary geometry (will be updated)
        self.experiment_btn = Button(
            QRect(0, 0, 200, 50), "Start Experiment", on_experiment_click,
            base_color=(60, 60, 80, 180),
            hover_color=(80, 80, 120, 200),
            parent=self
        )
        
        self.calibration_btn = Button(
            QRect(0, 0, 200, 50), "Start Calibration", 
            lambda: self.pending_events.append(MainMenuEvent.CALIBRATION_BTN_CLICKED),
            base_color=(60, 60, 80, 180),
            hover_color=(80, 80, 120, 200),
            parent=self
        )

    def update_content(self, headset_connected: bool):
        """Update the view content"""
        self.headset_connected = headset_connected
        
        # Update main buttons geometry
        width = self.width()
        height = self.height()
        
        btn_w, btn_h = 200, 50
        spacing = 20
        btn_x = (width - btn_w) // 2
        btn_y = int(height * 0.5)
        
        # Update button positions (don't recreate!)
        self.experiment_btn.setGeometry(btn_x, btn_y, btn_w, btn_h)
        self.calibration_btn.setGeometry(btn_x, btn_y + btn_h + spacing, btn_w, btn_h)
        
        # Trigger repaint
        self.update()
    
    
    def paintEvent(self, event):
        """Custom paint for title, logo, and status"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Draw title
        title_font = QFont('Arial', 56, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(255, 255, 255))
        title_text = "Hex-O-Spell Experiment"
        title_metrics = painter.fontMetrics()
        title_width = title_metrics.horizontalAdvance(title_text)
        title_x = (width - title_width) // 2
        title_y = int(height * 0.1) + title_metrics.ascent()
        painter.drawText(title_x, title_y, title_text)
        
        # Draw KN NEURON logo and text
        try:
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'imgs', 'kn_neuron_logo.png')
            logo_pixmap = QPixmap(logo_path).scaled(40, 40, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            
            kn_font = QFont('Arial', 24, QFont.Weight.Bold)
            painter.setFont(kn_font)
            painter.setPen(QColor(200, 200, 200))
            kn_text = "KN NEURON"
            kn_metrics = painter.fontMetrics()
            kn_width = kn_metrics.horizontalAdvance(kn_text)
            
            total_width = 40 + 10 + kn_width
            logo_x = (width - total_width) // 2
            logo_y = int(height * 0.21)
            
            painter.drawPixmap(logo_x, logo_y, logo_pixmap)
            painter.drawText(logo_x + 40 + 10, logo_y + 8 + kn_metrics.ascent(), kn_text)
        except Exception:
            pass
        
        # Draw headset status
        status_font = QFont('Arial', 28)
        painter.setFont(status_font)
        status_metrics = painter.fontMetrics()
        
        painter.setPen(QColor(255, 255, 255))
        status_text_1 = "Headset: "
        status_width_1 = status_metrics.horizontalAdvance(status_text_1)
        
        status_color = QColor(50, 200, 50) if self.headset_connected else QColor(220, 50, 50)
        status_text_2 = "Connected" if self.headset_connected else "Disconnected"
        status_width_2 = status_metrics.horizontalAdvance(status_text_2)
        
        total_status_width = status_width_1 + status_width_2
        status_x = (width - total_status_width) // 2
        status_y = int(height * 0.29) + status_metrics.ascent()
        
        painter.drawText(status_x, status_y, status_text_1)
        painter.setPen(status_color)
        painter.drawText(status_x + status_width_1, status_y, status_text_2)
    
    def get_pending_events(self) -> list[MainMenuEvent]:
        """Get and clear pending events"""
        events = self.pending_events.copy()
        self.pending_events.clear()
        return events
    
    def keyPressEvent(self, event):
        """Handle key presses"""
        if event.key() == Qt.Key.Key_Q:
            self.pending_events.append(MainMenuEvent.QUIT)
