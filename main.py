import os
os.add_dll_directory(r"C:\Program Files\BrainAccess\BrainAccess Board\dist\Lib\site-packages\brainaccess\lib")

from brainaccess.core.eeg_manager import EEGManager
mgr = EEGManager()