# wipe_manager.py
import subprocess
from PyQt5.QtCore import QThread, pyqtSignal

WIPE_METHODS = {
    "1": "zero",
    "2": "random",
    "3": "dodshort",
    "4": "dod",
    "5": "gutmann"
}

class WipeThread(QThread):
    progress = pyqtSignal(str)   # progress log line
    finished = pyqtSignal(bool)  # success/fail

    def __init__(self, drive, method):
        super().__init__()
        self.drive = drive
        self.method = method

    def run(self):
        cmd = ["sudo", "nwipe", "--method", self.method, f"/dev/{self.drive}"]
        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            for line in process.stdout:
                self.progress.emit(line.strip())
            process.wait()
            self.finished.emit(process.returncode == 0)
        except Exception as e:
            self.progress.emit(f"Error: {e}")
            self.finished.emit(False)
