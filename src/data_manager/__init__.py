class DataManager:
    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = data_dir

    def add_data_point(self, data: object) -> None:
        pass

    def export_current_session(self, name: str) -> str:
        return f"{name}.csv"
