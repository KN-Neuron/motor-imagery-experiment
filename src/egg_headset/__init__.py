from __future__ import annotations

from collections import deque
import importlib
import itertools
from typing import Any, Optional

import numpy as np


def _load_brainaccess() -> tuple[Any | None, Any | None, Any | None]:
    try:
        acquisition_module = "brainaccess.utils.acquisition"
        bacore_module = "brainaccess.core"
        eeg_manager_module = "brainaccess.core.eeg_manager"

        acquisition_mod = importlib.import_module(acquisition_module)
        bacore_mod = importlib.import_module(bacore_module)
        eeg_manager_mod = importlib.import_module(eeg_manager_module)
        eeg_manager_cls = getattr(eeg_manager_mod, "EEGManager", None)
        return acquisition_mod, bacore_mod, eeg_manager_cls
    except Exception:
        return None, None, None


acquisition, bacore, EEGManager = _load_brainaccess()


class EggHeadset:
    """Interfejs do opaski EEG.

    - gdy opaska jest dostępna: łączy się z fizyczną opaską
    - gdy brak opaski: działa w trybie mock (do testów)
    """

    def __init__(
        self,
        device_address: Optional[str] = None,
        port: str = "COM4",
        cap: Optional[dict] = None,
        core_version: tuple[int, int, int] = (2, 0, 0),
    ) -> None:
        self.device_address = device_address
        self.port = port
        self.cap = cap or {0: "Fp1", 1: "Fp2", 2: "O1", 3: "O2"}
        self.connected = False
        self.is_running = False

        self._is_mock_mode = True
        self._sample_rate_hz = 250
        self._n_channels = 4
        self._buffer_max_seconds = 60
        self._buffer: deque[tuple[float, ...]] = deque(
            maxlen=self._buffer_max_seconds * self._sample_rate_hz
        )
        self._sample_index = 0
        self._last_annotation_index: int | None = None

        self._core_version = core_version
        self.eeg_manager: Any | None = None
        self.eeg: Any | None = None

        if bacore is None or acquisition is None or EEGManager is None:
            pass
        else:
            try:
                bacore.init(bacore.Version(2, 0, 0))
                self.eeg_manager = EEGManager()
                self.eeg = acquisition.EEG()
                self._is_mock_mode = False
            except Exception as exc:
                print(f"Inicjalizacja nie powiodła się: {exc}")
                self.eeg_manager = None
                self.eeg = None
                self._is_mock_mode = True

        if isinstance(self.cap, dict):
            self._n_channels = len(self.cap)

    def connect(self) -> bool:
        if self.eeg is None or self.eeg_manager is None:
            print("Opaska niedostępna — tryb mock")
            self._is_mock_mode = True
            self.connected = True
            return True

        try:
            connect_kwargs: dict[str, Any] = {
                "cap": self.cap,
                "port": self.port,
            }
            self.eeg.setup(self.eeg_manager, **connect_kwargs)
            self.connected = True
            self._is_mock_mode = False
            return True
        except Exception as exc:
            print(f"Nie udało się połączyć: {exc} (fallback do mock)")
            self._is_mock_mode = True
            self.connected = True
            return True

    def disconnect(self) -> None:
        self.connected = False

    def start(self) -> None:
        if self.is_running:
            return

        if not self._is_mock_mode and self.eeg is not None:
            try:
                self.eeg.start_acquisition()
            except Exception as exc:
                print(f"Nie udało się uruchomić akwizycji: {exc}")
                self._is_mock_mode = True

        self.is_running = True
        print("Akwizycja EEG uruchomiona")

    def stop(self) -> None:
        if not self.is_running:
            return

        self.is_running = False
        print("Akwizycja EEG zatrzymana")

    def read_data(self) -> Optional[str]:
        if not self.connected:
            return None

        if self.is_running:
            self._try_pull_samples(min_samples=25)
        return "EEG data"

    def annotate(self, text: str) -> None:
        if not self.is_running:
            raise RuntimeError("Akwizycja nie jest uruchomiona")

        self._last_annotation_index = self._sample_index

        if not self._is_mock_mode and self.eeg is not None:
            try:
                self.eeg.annotate(text)
            except Exception as exc:
                print(f"Nie udało się dodać annotacji: {exc}")
                return

        print(f"Dodano annotację: {text}")

    def get_output(self) -> np.ndarray:
        """Zwraca próbki EEG 4×250 od startu ostatniej annotacji.

        Zawsze zwraca tablicę o kształcie (channels, 250).
        Jeśli brakuje próbek, w trybie mock dociąga/generuje dane,
        a w razie potrzeby dopełnia zerami.
        """

        if self._last_annotation_index is None:
            raise RuntimeError(
                "Brak annotacji — wywołaj annotate() przed get_output()."
            )

        start = self._last_annotation_index
        needed_end = start + self._sample_rate_hz
        self._ensure_samples_available(needed_end)

        output = self._slice_buffer(start, needed_end)
        if output.shape != (self._n_channels, self._sample_rate_hz):
            padded = np.zeros(
                (self._n_channels, self._sample_rate_hz),
                dtype=float,
            )
            take = min(output.shape[1], self._sample_rate_hz)
            if output.shape[0] == self._n_channels and take > 0:
                idx = (slice(None), slice(0, take))
                padded[idx] = output[idx]

            return padded

        return output

    def _ensure_samples_available(self, required_sample_index: int) -> None:
        if not self.is_running:
            return

        max_iters = 20
        while self._sample_index < required_sample_index and max_iters > 0:
            missing = required_sample_index - self._sample_index
            to_pull = min(missing, self._sample_rate_hz)
            self._try_pull_samples(min_samples=to_pull)
            max_iters -= 1

    def _try_pull_samples(self, min_samples: int) -> None:
        if min_samples <= 0:
            return

        if self._is_mock_mode or self.eeg is None:
            samples = self._mock_generate_samples(min_samples)
            self._append_samples(samples)
            return

        try:
            if hasattr(self.eeg, "get_data"):
                data = self.eeg.get_data()
                self._append_samples(np.asarray(data))
                return
            if hasattr(self.eeg, "get_samples"):
                data = self.eeg.get_samples()
                self._append_samples(np.asarray(data))
                return
        except Exception as exc:
            print(f"Nie udało się pobrać próbek: {exc}")
            self._is_mock_mode = True
            samples = self._mock_generate_samples(min_samples)
            self._append_samples(samples)

    def _append_samples(self, samples: np.ndarray) -> None:
        arr = np.asarray(samples, dtype=float)
        if arr.ndim == 1:
            if arr.size == self._n_channels:
                arr = arr.reshape(self._n_channels, 1)
            else:
                return
        if arr.ndim != 2:
            return

        if arr.shape[0] != self._n_channels:
            if arr.shape[1] == self._n_channels:
                arr = arr.T
        if arr.shape[0] != self._n_channels:
            return

        for i in range(arr.shape[1]):
            self._buffer.append(tuple(float(x) for x in arr[:, i]))
            self._sample_index += 1

    def _slice_buffer(self, start_index: int, end_index: int) -> np.ndarray:
        buffer_len = len(self._buffer)
        buffer_start_index = self._sample_index - buffer_len
        if start_index < buffer_start_index:
            return np.zeros((self._n_channels, 0), dtype=float)

        rel_start = start_index - buffer_start_index
        rel_end = max(rel_start, end_index - buffer_start_index)
        if rel_start >= buffer_len:
            return np.zeros((self._n_channels, 0), dtype=float)

        snapshot = list(self._buffer)
        stop = min(rel_end, len(snapshot))
        chunk = list(itertools.islice(snapshot, rel_start, stop))
        if not chunk:
            return np.zeros((self._n_channels, 0), dtype=float)

        arr = np.asarray(chunk, dtype=float)
        return arr.T

    def _mock_generate_samples(self, n_samples: int) -> np.ndarray:
        base = np.arange(
            self._sample_index, self._sample_index + n_samples, dtype=float
        )
        n_channels = self._n_channels
        return np.vstack([base + ch for ch in range(n_channels)])

    def process_data(self, raw_data: object) -> str:
        return str(raw_data)

    def save(self, filename: str) -> None:
        if self._is_mock_mode or self.eeg is None:
            print("Nie można zapisać")
            return

        try:
            raw = self.eeg.get_mne()
            raw.save(filename, overwrite=True)
            print(f"Dane zapisane do {filename}")
        except Exception as exc:
            print(f"Nie udało się zapisać: {exc}")


BrainAccessHalo = EggHeadset

__all__ = ["EggHeadset", "BrainAccessHalo"]
