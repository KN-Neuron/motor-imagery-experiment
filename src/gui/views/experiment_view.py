from .session_view import STEP_DISPLAY, SessionEvent, SessionView

ExperimentEvent = SessionEvent

__all__ = ["ExperimentEvent", "ExperimentView", "STEP_DISPLAY"]


class ExperimentView(SessionView):
    background = "background-color: rgb(25, 15, 40);"
