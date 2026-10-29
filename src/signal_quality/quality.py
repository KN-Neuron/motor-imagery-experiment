from dataclasses import dataclass, field

import numpy as np

from .thresholds import QualityThresholds


@dataclass
class ChannelQuality:
    label: str
    rms_uv: float  # RMS of the signal with the DC offset removed
    peak_to_peak_uv: float
    dc_offset_uv: float
    line_ratio: float  # mains-band power / 1-100 Hz power
    drift_uv_per_s: float
    warnings: list[str] = field(default_factory=list)


def assess_channels(
    data: np.ndarray,
    sample_rate: int,
    labels: list[str],
    thresholds: QualityThresholds | None = None,
) -> list[ChannelQuality]:
    """Per-channel quality of a resting-state fragment, shape (n_channels, n_samples).

    Warning codes: flat, saturated, noisy, line_noise, drift.
    """
    th = thresholds or QualityThresholds()
    n_channels, n_samples = data.shape
    if n_samples < sample_rate:
        raise ValueError("Need at least 1 s of data for a quality check")

    t = np.arange(n_samples) / sample_rate
    window = np.hanning(n_samples)
    freqs = np.fft.rfftfreq(n_samples, 1 / sample_rate)
    broadband = (freqs >= 1) & (freqs <= min(100, sample_rate / 2 - 1))
    mains = np.abs(freqs - th.mains_hz) <= 2

    results = []
    for ch in range(n_channels):
        x = data[ch].astype(float)
        dc = float(x.mean())
        ac = x - dc
        rms = float(np.sqrt(np.mean(ac**2)))
        slope = float(np.polyfit(t, x, 1)[0])

        power = np.abs(np.fft.rfft(ac * window)) ** 2
        total = power[broadband].sum()
        line_ratio = float(power[mains & broadband].sum() / total) if total > 0 else 0.0

        quality = ChannelQuality(
            labels[ch],
            rms,
            float(np.ptp(x)),
            dc,
            line_ratio,
            slope,
        )
        if rms < th.flat_rms_uv:
            quality.warnings.append("flat")
        if np.abs(x).max() > th.saturation_uv:
            quality.warnings.append("saturated")
        if rms > th.high_rms_uv:
            quality.warnings.append("noisy")
        if line_ratio > th.line_noise_ratio:
            quality.warnings.append("line_noise")
        if abs(slope) > th.drift_uv_per_s:
            quality.warnings.append("drift")
        results.append(quality)
    return results
