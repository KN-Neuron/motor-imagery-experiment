from __future__ import annotations

import traceback
from typing import Any

import numpy as np
from multiprocessing.connection import Connection

from src.eeg_headset.drivers import BrainAccessDriver, MockDriver
from src.eeg_headset.headset_config import HeadsetConfig, HeadsetModel

from .protocol import DriverRecipe


def _make_driver(recipe: DriverRecipe):
    if recipe.get("version") != 1:
        raise ValueError(f"Unsupported recipe version: {recipe.get('version')}")

    driver = recipe.get("driver")
    params = recipe.get("params") or {}

    if driver == "mock":
        n_channels = int(params.get("n_channels", 4))
        sfreq = int(params.get("sample_rate_hz", 250))
        return MockDriver(config=HeadsetConfig.mock(n_channels=n_channels, sample_rate_hz=sfreq))

    if driver == "brainaccess":
        model = params.get("model")
        config_path = params.get("config_path", "brainaccess.config.yaml")
        if not model:
            raise ValueError("Missing params.model for brainaccess driver")
        config = HeadsetConfig(model=HeadsetModel(str(model)), config_path=str(config_path))
        return BrainAccessDriver(config=config)

    raise ValueError(f"Unknown driver kind: {driver!r}")


def _ok(result: Any | None = None) -> dict[str, Any]:
    return {"ok": True, "result": result}


def _err(message: str) -> dict[str, Any]:
    return {"ok": False, "error": message, "traceback": traceback.format_exc()}


def worker_main(conn: Connection, recipe: DriverRecipe) -> None:
    """Worker process entrypoint.

    Receives commands via conn (pickled dicts) and executes them on the real driver.
    """

    try:
        driver = _make_driver(recipe)
    except Exception:
        conn.send(_err("Failed to construct driver"))
        return

    # Handshake
    try:
        conn.send(
            _ok(
                {
                    "sampling_rate": driver.sampling_rate,
                    "channel_count": driver.channel_count,
                    "device_name": getattr(driver.config, "device_name", None),
                }
            )
        )
    except Exception:
        conn.send(_err("Failed during handshake"))
        return

    while True:
        try:
            msg = conn.recv()
        except EOFError:
            break

        try:
            op = msg.get("op")

            if op == "shutdown":
                conn.send(_ok())
                break

            if op == "status":
                conn.send(_ok({"is_connected": driver.is_connected, "is_streaming": driver.is_streaming}))
                continue

            if op == "connect":
                driver.connect()
                conn.send(_ok())
                continue

            if op == "disconnect":
                driver.disconnect()
                conn.send(_ok())
                continue

            if op == "start_stream":
                driver.start_stream()
                conn.send(_ok())
                continue

            if op == "stop_stream":
                driver.stop_stream()
                conn.send(_ok())
                continue

            if op == "annotate":
                driver.annotate(str(msg.get("text", "")))
                conn.send(_ok())
                continue

            if op == "read":
                arr = driver.read_available_samples()
                if not isinstance(arr, np.ndarray):
                    raise TypeError(f"read_available_samples returned {type(arr)}")

                # Send a compact payload: dtype/shape + raw bytes.
                payload = {
                    "dtype": str(arr.dtype),
                    "shape": tuple(arr.shape),
                    "data": arr.tobytes(order="C"),
                }
                conn.send(_ok(payload))
                continue

            raise ValueError(f"Unknown op: {op!r}")

        except Exception as exc:
            conn.send(_err(str(exc)))

    try:
        conn.close()
    except Exception:
        pass
