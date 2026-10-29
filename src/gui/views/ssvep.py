"""Clock-based SSVEP flicker helpers (pure functions, no Qt).

NOT VALIDATED: the stimulus is drawn from Qt paint events and is not locked to
the monitor's VSync, so frames can be dropped or shown late. Flicker timing has
not been measured; do not rely on it for a rigorous SSVEP study.
"""


def ssvep_visible(elapsed_s: float, freq_hz: float) -> bool:
    """Square wave with 50 % duty cycle derived from elapsed time, not frames."""
    return (elapsed_s * freq_hz) % 1.0 < 0.5


def refresh_warning(refresh_hz: float, freq_hz: float) -> str | None:
    """Warn when freq_hz cannot be shown as whole, equal on/off frame counts."""
    if refresh_hz <= 0:
        return "Monitor refresh rate unknown; SSVEP timing cannot be checked."
    frames = refresh_hz / freq_hz
    if abs(frames - round(frames)) > 0.01:
        return (
            f"{freq_hz:g} Hz is not a divisor of the {refresh_hz:g} Hz refresh "
            f"rate ({frames:.2f} frames per cycle): flicker will be irregular."
        )
    if round(frames) % 2:
        return (
            f"{freq_hz:g} Hz at {refresh_hz:g} Hz needs {round(frames)} frames per "
            "cycle (odd): on/off phases cannot have equal length."
        )
    return None
