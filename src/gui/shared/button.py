from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QColor
from typing import Callable, Tuple

class Button(QPushButton):
    def __init__(self, 
        rect: QRect, 
        text: str, 
        callback: Callable[[], None],
        base_color: Tuple[int, int, int, int] = (40, 120, 220, 255),
        hover_color: Tuple[int, int, int, int] = (60, 150, 240, 255),
        text_color: Tuple[int, int, int] = (255, 255, 255),
        parent=None
    ) -> None:
        super().__init__(text, parent)
        self.setGeometry(rect)
        self.callback = callback
        self.base_color = base_color
        self.hover_color = hover_color
        self.text_color = text_color
        
        # Connect click
        self.clicked.connect(self.callback)
        
        # Apply stylesheet
        self._update_stylesheet(False)
        
    def _update_stylesheet(self, hover: bool):
        color = self.hover_color if hover else self.base_color
        bg_color = f"rgba({color[0]}, {color[1]}, {color[2]}, {color[3]})"
        text_col = f"rgb({self.text_color[0]}, {self.text_color[1]}, {self.text_color[2]})"
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_col};
                border-radius: 12px;
                font-size: 22px;
                font-family: Arial;
                border: none;
            }}
            QPushButton:hover {{
                background-color: rgba({self.hover_color[0]}, {self.hover_color[1]}, {self.hover_color[2]}, {self.hover_color[3]});
            }}
        """)
    
    def enterEvent(self, event):
        self._update_stylesheet(True)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._update_stylesheet(False)
        super().leaveEvent(event)
