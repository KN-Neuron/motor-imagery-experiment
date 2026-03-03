import queue
import threading
from time import sleep

from websockets import ServerProtocol

from streaming.websocket_streamer import WebsocketStreamer
from websockets.sync.server import serve
import numpy as np


class TestWebSocketStreamer:
    validation_queue: queue.Queue = queue.Queue()

    def _echo_handler(self, ws: ServerProtocol) -> None:
        print("Client connected")
        try:
            while True:
                shape_data = ws.recv()
                assert shape_data is not None, "Expected shape data but received None"
                shape = tuple(map(int, shape_data.split(",")))
                array_data = ws.recv()
                assert array_data is not None, "Expected array data but received None"

                decoded_array = np.frombuffer(array_data, dtype=np.float64).reshape(
                    shape
                )
                correct_array = self.validation_queue.get()

                assert np.array_equal(
                    decoded_array, correct_array
                ), "Received data does not match expected data"
        except Exception as e:
            print("Connection closed:", e)
        finally:
            ws.close()
            print("Client disconnected")

    def _serve(self) -> None:
        with serve(self._echo_handler, "localhost", 9090) as server:
            server.serve_forever()

    def test_streaming(self) -> None:
        threading.Thread(target=self._serve, daemon=True).start()

        streamer = WebsocketStreamer(host="localhost", port=9090, queue_size=10)
        streamer.start()

        for _ in range(5):
            data = np.random.rand(10, 10)
            self.validation_queue.put(data)
            streamer.enqueue_data(data)

        sleep(4)
        streamer.stop()
        assert (
            self.validation_queue.empty()
        ), "Validation queue should be empty after test"
