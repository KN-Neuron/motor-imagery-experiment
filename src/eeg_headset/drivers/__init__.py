from typing import Any

from .headset_driver import HeadsetDriver
from .mock import MockDriver

__all__ = ["BrainAccessDriver", "MockDriver", "HeadsetDriver"]


def __getattr__(name: str) -> Any:
    # Lazy: the BrainAccess SDK is optional (absent on CI / dev machines).
    if name == "BrainAccessDriver":
        from .brainaccess import BrainAccessDriver

        return BrainAccessDriver
    raise AttributeError(name)
