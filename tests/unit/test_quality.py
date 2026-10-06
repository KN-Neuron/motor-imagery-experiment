import numpy as np

from src.signal_quality.quality import assess_channels
from src.signal_quality.thresholds import QualityThresholds

FS = 250


def make_data() -> tuple[np.ndarray, list[str]]:
    rng = np.random.default_rng(0)
    t = np.arange(10 * FS) / FS
    good = 20 * np.sin(2 * np.pi * 10 * t) + rng.normal(0, 5, t.size)
    flat = np.zeros_like(t)
    saturated = good.copy()
    saturated[100] = 3100
    mains = good + 60 * np.sin(2 * np.pi * 50 * t)
    drift = good + 100 * t  # 100 uV/s ramp
    noisy = rng.normal(0, 300, t.size)
    data = np.vstack([good, flat, saturated, mains, drift, noisy])
    return data, ["good", "flat", "sat", "mains", "drift", "noisy"]


def test_channels_are_flagged_with_the_right_warning() -> None:
    data, labels = make_data()
    result = {q.label: q for q in assess_channels(data, FS, labels)}
    assert result["good"].warnings == []
    assert "flat" in result["flat"].warnings
    assert "saturated" in result["sat"].warnings
    assert "line_noise" in result["mains"].warnings
    assert "drift" in result["drift"].warnings
    assert "noisy" in result["noisy"].warnings


def test_thresholds_are_configurable() -> None:
    data, labels = make_data()
    lenient = QualityThresholds(
        flat_rms_uv=0.0,
        saturation_uv=1e9,
        high_rms_uv=1e9,
        line_noise_ratio=1.1,
        drift_uv_per_s=1e9,
    )
    assert all(not q.warnings for q in assess_channels(data, FS, labels, lenient))


def test_rms_ignores_dc_offset() -> None:
    data, labels = make_data()
    shifted = data + 1000
    a = assess_channels(data[:1], FS, labels[:1])[0]
    b = assess_channels(shifted[:1], FS, labels[:1])[0]
    assert abs(a.rms_uv - b.rms_uv) < 1e-6 and b.dc_offset_uv > 900
