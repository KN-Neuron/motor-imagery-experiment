from typing import Protocol
import numpy as np

from .headset_driver import HeadsetDriver
from .brainaccess import BrainAccessDriver
from .mock import MockDriver


__all__ = ["BrainAccessDriver", "MockDriver", "HeadsetDriver"]
