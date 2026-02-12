from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QFrame
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QPainter, QColor


class Sidebar(QWidget):
    """Reusable sidebar with common controls"""
    
    # Signals for actions
    fullscreen_toggled = pyqtSignal()
    pause_toggled = pyqtSignal()
    back_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_fullscreen = False
        self.is_paused = False
        self.show_back_button = False
        self.show_pause_button = False
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup sidebar UI"""
        self.setFixedWidth(60)
        self.setStyleSheet("""
            Sidebar {
                background-color: rgb(20, 20, 30);
            }
        """)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(8)
        
        # Fullscreen button
        self.fullscreen_btn = self._create_sidebar_button("FS", "Toggle Fullscreen")
        self.fullscreen_btn.clicked.connect(self._on_fullscreen_clicked)
        layout.addWidget(self.fullscreen_btn)
        
        layout.addStretch()
        
        # Pause button (hidden by default)
        self.pause_btn = QPushButton("||", self)
        self.pause_btn.setFixedSize(50, 45)
        self.pause_btn.setToolTip("Pause")
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(60, 60, 80, 180);
                color: white;
                border-radius: 8px;
                font-size: 22px;
                font-weight: bold;
                font-family: Arial;
                border: 1px solid rgba(80, 80, 100, 100);
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 120, 220);
                border: 1px solid rgba(120, 120, 160, 150);
            }
            QPushButton:pressed {
                background-color: rgba(50, 50, 70, 200);
            }
        """)
        self.pause_btn.hide()
        layout.addWidget(self.pause_btn)
        
        # Back button (hidden by default)
        self.back_btn = self._create_sidebar_button("<", "Back to Menu")
        self.back_btn.clicked.connect(self._on_back_clicked)
        self.back_btn.hide()
        layout.addWidget(self.back_btn)
    
    def paintEvent(self, event):
        """Draw white separator line on the right edge"""
        painter = QPainter(self)
        painter.setPen(QColor(255, 255, 255, 80))
        # Draw line at right edge
        painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
    
    def _create_sidebar_button(self, text: str, tooltip: str) -> QPushButton:
        """Create a styled sidebar button"""
        btn = QPushButton(text)
        btn.setFixedSize(50, 45)
        btn.setToolTip(tooltip)
        btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(60, 60, 80, 180);
                color: white;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                font-family: Arial;
                border: 1px solid rgba(80, 80, 100, 100);
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 120, 220);
                border: 1px solid rgba(120, 120, 160, 150);
            }
            QPushButton:pressed {
                background-color: rgba(50, 50, 70, 200);
            }
        """)
        return btn
    
    def _on_fullscreen_clicked(self):
        self.is_fullscreen = not self.is_fullscreen
        self.fullscreen_btn.setText("WIN" if self.is_fullscreen else "FS")
        self.fullscreen_toggled.emit()
    
    def _on_pause_clicked(self):
        self.is_paused = not self.is_paused
        new_text = ">" if self.is_paused else "||"
        self.pause_btn.setText(new_text)
        self.pause_btn.setToolTip("Resume" if self.is_paused else "Pause")
        # Force visual update
        self.pause_btn.update()
        print(f"[DEBUG SIDEBAR] Pause toggled: {self.is_paused}, text: {new_text}")
        self.pause_toggled.emit()
    
    def _on_back_clicked(self):
        self.back_requested.emit()
    
    def set_buttons_visibility(self, show_pause: bool = False, show_back: bool = False):
        """Configure which buttons to show"""
        self.show_pause_button = show_pause
        self.show_back_button = show_back
        self.pause_btn.setVisible(show_pause)
        self.back_btn.setVisible(show_back)
    
    def update_states(self, is_fullscreen: bool):
        """Update button states"""
        self.is_fullscreen = is_fullscreen
        self.fullscreen_btn.setText("WIN" if is_fullscreen else "FS")
    
    def reset_pause(self):
        """Reset pause state"""
        self.is_paused = False
        self.pause_btn.setText("||")
        self.pause_btn.setToolTip("Pause")
