"""User-facing texts (Polish first, English second) shown to participants."""

from .experiment_step_type import ExperimentStepType as T

CUE_TEXT: dict[T, tuple[str, str]] = {
    T.LEFT_HAND_IMAGERY: (
        "WYOBRAŹ SOBIE zaciskanie LEWEJ dłoni (nie ruszaj ręką)",
        "IMAGINE clenching your LEFT hand (do not move it)",
    ),
    T.RIGHT_HAND_IMAGERY: (
        "WYOBRAŹ SOBIE zaciskanie PRAWEJ dłoni (nie ruszaj ręką)",
        "IMAGINE clenching your RIGHT hand (do not move it)",
    ),
    T.LEFT_HAND_EXECUTION: ("ZACIŚNIJ LEWĄ dłoń", "CLENCH your LEFT hand"),
    T.RIGHT_HAND_EXECUTION: ("ZACIŚNIJ PRAWĄ dłoń", "CLENCH your RIGHT hand"),
    T.DOUBLE_BLINK: ("ZAMRUGAJ MOCNO DWA RAZY", "BLINK firmly TWICE"),
    T.JAW_CLENCH: ("ZACIŚNIJ SZCZĘKĘ", "CLENCH your JAW"),
    T.HEAD_MOVEMENT: ("PORUSZ GŁOWĄ", "MOVE your HEAD"),
    T.SSVEP_FOCUS: (
        "SKUP WZROK NA MIGAJĄCYM PUNKCIE",
        "FOCUS on the flashing dot",
    ),
    T.REST_EYES_OPEN: (
        "ODPOCZYNEK – oczy OTWARTE, patrz na krzyżyk",
        "REST – eyes OPEN, look at the cross",
    ),
    T.REST_EYES_CLOSED: (
        "ODPOCZYNEK – oczy ZAMKNIĘTE",
        "REST – eyes CLOSED",
    ),
}

DEFAULT_INSTRUCTION = (
    "Za chwilę rozpocznie się badanie.\n"
    "Siedź wygodnie i nieruchomo, rozluźnij twarz i szczękę.\n"
    "Podczas zadań WYOBRAŻENIOWYCH wyobrażaj sobie ruch, ale NIE poruszaj ręką.\n"
    "Podczas zadań WYKONYWANYCH naprawdę zaciskaj dłoń.\n"
    "Możesz w każdej chwili przerwać badanie.\n"
    "\n"
    "The experiment is about to start.\n"
    "Sit comfortably and still, relax your face and jaw.\n"
    "During IMAGERY tasks imagine the movement but do NOT move your hand.\n"
    "During EXECUTION tasks really clench your hand.\n"
    "You may stop at any time.\n"
    "\n"
    "Naciśnij SPACJĘ, aby kontynuować / Press SPACE to continue"
)

PRACTICE_TEXT = (
    "TRENING – kilka prób próbnych (nie będą analizowane).\n"
    "PRACTICE – a few trial runs (excluded from analysis).\n"
    "\n"
    "Naciśnij SPACJĘ / Press SPACE"
)

BREAK_TEXT = (
    "Odpoczynek. Naciśnij SPACJĘ, aby kontynuować.\n" "Rest. Press SPACE to continue."
)

END_TEXT = (
    "Koniec badania. Dziękujemy!\n"
    "End of the session. Thank you!\n"
    "\n"
    "Naciśnij SPACJĘ / Press SPACE"
)

PAUSE_HINT = "PAUZA / PAUSED"
