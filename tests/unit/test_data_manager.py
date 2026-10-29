from src.data_manager import DataManager


class TestDataManager:
    def test_initialization(self) -> None:
        dm = DataManager()
        assert dm is not None
