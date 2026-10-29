from abc import abstractmethod
from typing import Any, Callable

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QHideEvent, QKeySequence, QShortcut, QShowEvent


class View(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.pending_events: list[Any] = []
        self.shortcuts: list[QShortcut] = []
        self._setup_ui()

    @abstractmethod
    def _setup_ui(self) -> None:
        ...

    @abstractmethod
    def update_content(self, *args: Any, **kwargs: Any) -> None:
        ...

    def get_pending_events(self) -> list[Any]:
        events = self.pending_events.copy()
        self.pending_events.clear()
        return events

    def _register_shortcut(
        self, key_sequence: Any, callback: Callable[[], None]
    ) -> QShortcut:
        shortcut = QShortcut(QKeySequence(key_sequence), self)
        shortcut.setEnabled(False)
        shortcut.activated.connect(callback)
        self.shortcuts.append(shortcut)
        return shortcut

    def showEvent(self, event: QShowEvent | None) -> None:
        super().showEvent(event)
        for s in self.shortcuts:
            s.setEnabled(True)

    def hideEvent(self, event: QHideEvent | None) -> None:
        super().hideEvent(event)
        for s in self.shortcuts:
            s.setEnabled(False)
