from typing import Optional


class EggHeadset:
    def __init__(self, device_address: Optional[str] = None) -> None:
        self.device_address = device_address
        self.connected = False

    def connect(self) -> bool:
        return False

    def disconnect(self) -> None:
        pass

    def read_data(self) -> Optional[str]:
        return None

    def process_data(self, raw_data: object) -> str:
        return str(raw_data)
