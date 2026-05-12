from __future__ import annotations

import atexit
import sys
import time
from dataclasses import dataclass
from multiprocessing.connection import Connection
from typing import Any

import numpy as np
import multiprocessing as mp

from src.eeg_headset.headset_config import HeadsetConfig

from .protocol import DriverRecipe, WorkerError
from .worker import worker_main


@dataclass(frozen=True)
class IpcOptions:
    start_method: str = "spawn"
    request_timeout_s: float = 10.0


class IpcHeadsetDriver:
    """Implements HeadsetDriver by delegating to a subprocess via multiprocessing Pipe.

    This is primarily meant to isolate native SDK crashes (access violations) from the Qt GUI process.
    """

    def __init__(
        self,
        recipe: DriverRecipe,
        config: HeadsetConfig,
        options: IpcOptions | None = None,
    ) -> None:
        self._recipe = recipe
        self._config = config
        self._options = options or IpcOptions()

        ctx = mp.get_context(self._options.start_method)
        parent_conn, child_conn = ctx.Pipe(duplex=True)
        self._conn: Connection = parent_conn
        self._proc = ctx.Process(target=worker_main, args=(child_conn, recipe), daemon=True)
        self._proc.start()

        atexit.register(self._atexit_cleanup)

        # Handshake
        hello = self._recv_or_raise()
        if not hello.get("ok"):
            raise WorkerError(hello.get("error", "Worker failed"), hello.get("traceback"))

        result = hello.get("result") or {}
        self._sampling_rate = int(result.get("sampling_rate", config.sample_rate_hz))
        self._channel_count = int(result.get("channel_count", config.n_channels))

    @property
    def sampling_rate(self) -> int:
        return self._sampling_rate

    @property
    def channel_count(self) -> int:
        return self._channel_count

    @property
    def config(self) -> HeadsetConfig:
        return self._config

    def _send(self, msg: dict[str, Any]) -> None:
        try:
            self._conn.send(msg)
        except (BrokenPipeError, EOFError, OSError) as exc:
            raise RuntimeError("Headset worker IPC channel is closed") from exc

    def _recv_or_raise(self) -> dict[str, Any]:
        deadline = time.time() + self._options.request_timeout_s
        while True:
            if self._conn.poll(0.05):
                try:
                    return self._conn.recv()
                except (EOFError, OSError) as exc:
                    raise RuntimeError("Headset worker process crashed or exited") from exc

            if time.time() > deadline:
                raise TimeoutError("Timed out waiting for worker response")

    def _rpc(self, op: str, **kwargs: Any) -> Any:
        self._send({"op": op, **kwargs})
        resp = self._recv_or_raise()
        if not resp.get("ok"):
            raise WorkerError(resp.get("error", "Worker error"), resp.get("traceback"))
        return resp.get("result")

    @property
    def is_connected(self) -> bool:
        status = self._rpc("status")
        return bool((status or {}).get("is_connected"))

    @property
    def is_streaming(self) -> bool:
        status = self._rpc("status")
        return bool((status or {}).get("is_streaming"))

    def connect(self) -> None:
        self._rpc("connect")

    def disconnect(self) -> None:
        # Best-effort shutdown; caller expects idempotence.
        try:
            self._rpc("disconnect")
        finally:
            self._shutdown_worker()

    def start_stream(self) -> None:
        self._rpc("start_stream")

    def stop_stream(self) -> None:
        self._rpc("stop_stream")

    def annotate(self, text: str) -> None:
        self._rpc("annotate", text=text)

    def read_available_samples(self) -> np.ndarray:
        payload = self._rpc("read") or {}
        dtype = np.dtype(payload.get("dtype", "float32"))
        shape = tuple(payload.get("shape", (self.channel_count, 0)))
        data = payload.get("data", b"")
        if not data:
            return np.empty((self.channel_count, 0), dtype=dtype)
        arr = np.frombuffer(data, dtype=dtype)
        arr = arr.reshape(shape)
        return arr.copy()

    def _shutdown_worker(self) -> None:
        if getattr(self, "_proc", None) is None:
            return

        if not self._proc.is_alive():
            return

        try:
            self._send({"op": "shutdown"})
            _ = self._recv_or_raise()
        except Exception:
            pass

        try:
            self._proc.join(timeout=1.0)
        except Exception:
            pass

        if self._proc.is_alive():
            try:
                self._proc.kill()  # Python 3.7+
            except Exception:
                pass

    def _atexit_cleanup(self) -> None:
        # Avoid doing too much work during interpreter shutdown.
        try:
            self._shutdown_worker()
        except Exception:
            pass


def make_brainaccess_recipe(model: str, config_path: str) -> DriverRecipe:
    return {"version": 1, "driver": "brainaccess", "params": {"model": model, "config_path": config_path}}


def make_mock_recipe(n_channels: int = 4, sample_rate_hz: int = 250) -> DriverRecipe:
    return {"version": 1, "driver": "mock", "params": {"n_channels": n_channels, "sample_rate_hz": sample_rate_hz}}
