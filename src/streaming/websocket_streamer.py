import queue
import threading
from typing import Optional

import numpy as np
from websockets.sync.client import connect


class WebsocketStreamer:
    def __init__(
        self, host: str = "localhost", port: int = 9090, queue_size: int = 100
    ):
        self.host = host
        self.port = port

        self._queue: queue.Queue = queue.Queue(maxsize=queue_size)

        self._thread: Optional[threading.Thread] = None
        self._running = False

    def enqueue_data(self, data: np.ndarray) -> None:
        """
        Drops the numpy array into the queue.
        """
        if not self._running:
            raise RuntimeError(
                "Streamer is not running. Call start() before enqueueing data."
            )

        if self._queue.full():
            self._queue.get_nowait()  # Drop the oldest data if the queue is full
        self._queue.put_nowait(data)

    def start(self) -> None:
        """Starts the streaming thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stops the streaming thread."""
        if not self._running:
            return

        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _worker(self) -> None:
        """The main function of the streaming thread."""

        with connect(f"ws://{self.host}:{self.port}") as socket:  # noqa: E231
            while self._running:
                try:
                    data: np.ndarray = self._queue.get(timeout=0.1)
                    shape = data.shape

                    socket.send(f"{shape[0]}, {shape[1]}")
                    socket.send(data.tobytes())

                except queue.Empty:
                    continue
