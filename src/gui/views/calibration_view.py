from .session_view import SessionEvent, SessionView

CalibrationEvent = SessionEvent

__all__ = ["CalibrationEvent", "CalibrationView"]


class CalibrationView(SessionView):
    background = "background-color: rgb(20, 20, 35);"
