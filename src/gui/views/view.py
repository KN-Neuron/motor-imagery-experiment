from abc import abstractmethod

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QShortcut, QKeySequence


class View(QWidget):
    def __init__(self):
        super().__init__()
        self.pending_events = []
        self.shortcuts: list[QShortcut] = []
        self._setup_ui()

    @abstractmethod
    def _setup_ui(self):
        ...

    @abstractmethod
    def update_content(self, *args, **kwargs):
        ...

    def get_pending_events(self) -> list:
        events = self.pending_events.copy()
        self.pending_events.clear()
        return events

    def _register_shortcut(self, key_sequence, callback) -> QShortcut:
        shortcut = QShortcut(QKeySequence(key_sequence), self)
        shortcut.setEnabled(False)
        shortcut.activated.connect(callback)
        self.shortcuts.append(shortcut)
        return shortcut

    def showEvent(self, event):
        super().showEvent(event)
        for s in self.shortcuts:
            s.setEnabled(True)

    def hideEvent(self, event):
        super().hideEvent(event)
        for s in self.shortcuts:
            s.setEnabled(False)
