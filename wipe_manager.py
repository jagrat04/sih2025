# wipe_manager.py
import subprocess
from PyQt5.QtCore import QThread, pyqtSignal
from drive_manager import get_drive_type, list_drives

WIPE_METHODS = {
    "HDD": {
        "method": "Overwrite 1-pass",
        "command": lambda dev: ["nwipe", "--method=zero", dev]
    },
    "SATA SSD": {
        "method": "Secure Erase",
        "command": lambda dev: ["hdparm", "--user-master", "u", "--security-set-pass", "p", dev, "&&",
                                "hdparm", "--user-master", "u", "--security-erase", "p", dev]
    },
    "NVMe SSD": {
        "method": "NVMe Format",
        "command": lambda dev: ["nvme", "format", dev]
    },
    "USB": {
        "method": "Overwrite",
        "command": lambda dev: ["dd", "if=/dev/zero", f"of={dev}", "bs=64M", "status=progress"]
    },
    "SD Card": {
        "method": "Overwrite",
        "command": lambda dev: ["dd", "if=/dev/zero", f"of={dev}", "bs=64M", "status=progress"]
    },
    "Android (encrypted)": {
        "method": "Crypto Erase",
        "command": lambda dev: ["echo", "Factory reset required (key discard)"]
    },
    "Android (unencrypted)": {
        "method": "Overwrite",
        "command": lambda dev: ["fastboot", "erase", "userdata"]
    }
}

def get_command_for_device(dev):
    drive_type = get_drive_type(dev)
    if drive_type in WIPE_METHODS:
        return WIPE_METHODS[drive_type]["command"](dev), WIPE_METHODS[drive_type]["method"]
    else:
        return None, "Unknown"

# NIST mapping table
NIST_METHODS = {
    "HDD":        ("Overwrite 1-pass", ["sudo", "nwipe", "--method=zero"]),
    "SATA SSD":   ("Secure Erase", ["sudo", "hdparm", "--security-erase", "p"]),
    "NVMe M.2 SSD": ("NVMe Format", ["sudo", "nvme", "format"]),
    "USB Thumb Drive": ("Overwrite", ["sudo", "dd", "if=/dev/zero", "bs=64M"]),
    "SD / microSD":   ("Overwrite", ["sudo", "dd", "if=/dev/zero", "bs=64M"]),
    "Unknown":    ("Default Overwrite", ["sudo", "nwipe", "--method=zero"])
}


class WipeThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(self, drive, media_type):
        super().__init__()
        self.drive = drive
        self.media_type = media_type

    def run(self):
        method_name, base_cmd = NIST_METHODS.get(self.media_type, NIST_METHODS["Unknown"])

        # Finalize full command depending on tool
        if "nwipe" in base_cmd[0]:
            cmd = base_cmd + [f"/dev/{self.drive}"]
        elif "hdparm" in base_cmd[0]:
            cmd = base_cmd + [f"/dev/{self.drive}"]
        elif "nvme" in base_cmd[0]:
            cmd = base_cmd + [f"/dev/{self.drive}"]
        elif "dd" in base_cmd[0]:
            cmd = base_cmd + [f"of=/dev/{self.drive}"]
        else:
            cmd = base_cmd + [f"/dev/{self.drive}"]

        self.progress.emit(f"Using NIST method: {method_name}")
        self.progress.emit(f"Running command: {' '.join(cmd)}")

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
