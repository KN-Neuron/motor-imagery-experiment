from dataclasses import dataclass


@dataclass
class QualityThresholds:
    """Pre-recording signal checks. Defaults are STARTING VALUES, not validated
    against BrainAccess dry electrodes: tune them on real recordings."""

    flat_rms_uv: float = 0.5  # RMS below -> channel is flat (no contact / dead)
    saturation_uv: float = 3000.0  # |x| above -> near the EDF range (±3200 uV)
    high_rms_uv: float = 150.0  # RMS above -> very noisy channel
    line_noise_ratio: float = 0.3  # 48-52 Hz power / 1-100 Hz power above -> mains
    drift_uv_per_s: float = 50.0  # |linear trend| above -> strong DC drift
    mains_hz: float = 50.0
