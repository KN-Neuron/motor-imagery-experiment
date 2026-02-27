from PyQt6.QtWidgets import QWidget, QPushButton, QLabel
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QKeySequence, QShortcut
from enum import Enum
from src.sample_manager.experiment_step_type import ExperimentStepType


class ExperimentEvent(Enum):
    TOGGLE_FULLSCREEN = "toggle_fullscreen"
    ABORT = "abort"
    QUIT = "quit"
    PAUSE = "pause"


class ExperimentView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.pending_events = []
        self.step_type = None
        self.no_eeg_mode = False
        self.progress_percent = 0.0
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI components"""
        # Set background color - deep purple
        self.setStyleSheet("background-color: rgb(25, 15, 40);")
        
        # Setup ESC shortcut (will be activated when view is shown)
        self.esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.esc_shortcut.activated.connect(self._on_esc_pressed)
        self.esc_shortcut.setEnabled(False)  # Disabled by default    

    def update_content(self, step_type, no_eeg_mode, progress_percent):
        """Update the view content"""
        self.step_type = step_type
        self.no_eeg_mode = no_eeg_mode
        self.progress_percent = progress_percent
        
        # Trigger repaint
        self.update()
    
    def paintEvent(self, event):
        """Custom paint for experiment content"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Draw NO EEG MODE label
        if self.no_eeg_mode:
            mode_font = QFont('Arial', 16)
            painter.setFont(mode_font)
            painter.setPen(QColor(180, 100, 100))
            mode_text = "NO EEG MODE"
            mode_metrics = painter.fontMetrics()
            mode_width = mode_metrics.horizontalAdvance(mode_text)
            mode_x = width - mode_width - 15
            mode_y = 15 + mode_metrics.ascent()
            painter.drawText(mode_x, mode_y, mode_text)
        
        # Draw progress bar at bottom
        bar_height = 8
        bar_y = height - bar_height
        bar_width = width
        
        # Background (darker)
        painter.fillRect(0, bar_y, bar_width, bar_height, QColor(40, 40, 60))
        
        # Progress fill (blue)
        if self.progress_percent > 0:
            fill_width = int(bar_width * self.progress_percent)
            painter.fillRect(0, bar_y, fill_width, bar_height, QColor(80, 120, 200))
        
        # Draw step info
        if self.step_type:
            # Map step types to display text and colors
            step_colors = {
                ExperimentStepType.FIXATION: (QColor(200, 200, 200), "FIXATION"),
                ExperimentStepType.REST: (QColor(150, 150, 200), "REST"),
                ExperimentStepType.DOUBLE_BLINK: (QColor(100, 200, 255), "DOUBLE BLINK"),
                ExperimentStepType.LEFT_HAND: (QColor(255, 150, 150), "LEFT HAND CLENCH"),
                ExperimentStepType.RIGHT_HAND: (QColor(150, 255, 150), "RIGHT HAND CLENCH"),
                ExperimentStepType.JAW_CLENCH: (QColor(255, 200, 100), "JAW CLENCH"),
                ExperimentStepType.HEAD_MOVEMENT: (QColor(200, 150, 255), "HEAD MOVEMENT"),
                ExperimentStepType.SSVEP_FOCUS: (QColor(255, 255, 150), "SSVEP FOCUS"),
            }
            
            color, text = step_colors.get(self.step_type, (QColor(255, 255, 255), self.step_type.value.upper()))
            
            # Draw step title
            title_font = QFont('Arial', 48, QFont.Weight.Bold)
            painter.setFont(title_font)
            painter.setPen(color)
            title_metrics = painter.fontMetrics()
            title_width = title_metrics.horizontalAdvance(text)
            title_x = (width - title_width) // 2
            title_y = int(height * 0.4) + title_metrics.ascent()
            painter.drawText(title_x, title_y, text)
            
            # Show ESC hint
            hint_font = QFont('Arial', 18)
            painter.setFont(hint_font)
            painter.setPen(QColor(150, 150, 150))
            hint_text = "Press ESC to abort experiment"
            hint_metrics = painter.fontMetrics()
            hint_width = hint_metrics.horizontalAdvance(hint_text)
            hint_x = (width - hint_width) // 2
            hint_y = int(height * 0.92) + hint_metrics.ascent()
            painter.drawText(hint_x, hint_y, hint_text)
    
    def get_pending_events(self) -> list[ExperimentEvent]:
        """Get and clear pending events"""
        events = self.pending_events.copy()
        self.pending_events.clear()
        return events
    
    def _on_esc_pressed(self):
        """Handle ESC shortcut"""
        print("[DEBUG EXPERIMENT VIEW] ESC shortcut triggered - adding ABORT event")
        self.pending_events.append(ExperimentEvent.ABORT)
    
    def showEvent(self, event):
        """Enable ESC shortcut when view is shown"""
        super().showEvent(event)
        self.esc_shortcut.setEnabled(True)
        print("[DEBUG EXPERIMENT VIEW] ESC shortcut enabled")
    
    def hideEvent(self, event):
        """Disable ESC shortcut when view is hidden"""
        super().hideEvent(event)
        self.esc_shortcut.setEnabled(False)
        print("[DEBUG EXPERIMENT VIEW] ESC shortcut disabled")
