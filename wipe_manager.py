import subprocess
import os
import json
import time
import hashlib
import random
import struct

from PyQt5.QtCore import QThread, pyqtSignal
from drive_manager import get_drive_type, list_drives
from report_generator import generate_report_and_sign
from blockchain_connector import anchor_hash

WIPE_METHODS = {
    "HDD": {
        "method": "Overwrite 1-pass",
        "command": lambda dev: ["sudo", "nwipe", "--method=zero", dev]
    },
    "SATA SSD": {
        "method": "Secure Erase",
        "command": lambda dev: ["sudo", "hdparm", "--user-master", "u", "--security-set-pass", "p", dev,
                                "&&", "sudo", "hdparm", "--user-master", "u", "--security-erase", "p", dev]
    },
    "NVMe SSD": {
        "method": "NVMe Format",
        "command": lambda dev: ["sudo", "nvme", "format", dev]
    },
    "USB": {
        "method": "Overwrite",
        "command": lambda dev: ["sudo", "dd", "if=/dev/zero", f"of={dev}", "bs=64M", "status=progress"]
    },
    "SD Card": {
        "method": "Overwrite",
        "command": lambda dev: ["sudo", "dd", "if=/dev/zero", f"of={dev}", "bs=64M", "status=progress"]
    },
    "Android (encrypted)": {
        "method": "Crypto Erase",
        "command": lambda dev: ["echo", "Factory reset required (key discard)"]
    },
    "Android (unencrypted)": {
        "method": "Overwrite",
        "command": lambda dev: ["sudo", "fastboot", "erase", "userdata"]
    },
    # ✅ NEW DUMMY TEST ENTRY
    "Dummy Test": {
        "method": "Dummy Overwrite",
        "command": lambda dev: ["dd", "if=/dev/zero", "of=dummy_test.img", "bs=1M", "count=5", "status=progress"]
    }
}

# NIST mapping table
NIST_METHODS = {
    "HDD": (
        "Overwrite 1-pass",
        ["sudo", "nwipe", "--autonuke", "--method=zero"]
    ),
    "SATA SSD": (
        "Secure Erase",
        ["sudo", "hdparm", "--user-master", "u", "--security-erase", "p"]
    ),
    "NVMe M.2 SSD": (
        "NVMe Format",
        ["sudo", "nvme", "format"]
    ),
    "USB Thumb Drive": (
        "Overwrite",
        ["sudo", "dd", "if=/dev/zero", "bs=64M", "status=progress"]
    ),
    "SD / microSD": (
        "Overwrite",
        ["sudo", "dd", "if=/dev/zero", "bs=64M", "status=progress"]
    ),
    "Dummy Test": (  # ✅ also map dummy into NIST
        "Dummy Overwrite",
        ["dd", "if=/dev/zero", "of=dummy_test.img", "bs=1M", "count=5", "status=progress"]
    ),
    "Unknown": (
        "Default Overwrite",
        ["sudo", "nwipe", "--autonuke", "--method=zero"]
    ),
}


class WipeThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(object)  # will emit a dict result

    def __init__(self, drive, media_type, serial=None, sample_count=5):
        super().__init__()
        self.drive = drive
        self.media_type = media_type
        self.serial = serial
        self.sample_count = sample_count
        self.out_dir = os.path.abspath("wipes")
        os.makedirs(self.out_dir, exist_ok=True)

    def _device_path(self):
        if self.media_type == "Dummy Test":
            # ✅ point to dummy file instead of /dev/ drive
            return "dummy_test.img"
        return f"/dev/{self.drive}"

    def _device_size_bytes(self):
        try:
            if self.media_type == "Dummy Test":
                return os.path.getsize("dummy_test.img")
            out = subprocess.check_output(["blockdev", "--getsize64", self._device_path()], text=True).strip()
            return int(out)
        except Exception:
            return None

    def _chain_hash(self, prev_hash_hex, entry_bytes):
        h = hashlib.sha256()
        h.update(prev_hash_hex.encode("utf-8"))
        h.update(entry_bytes)
        return h.hexdigest()

    def _sample_random_sectors(self, device_path, device_size_bytes, count):
        samples = []
        if device_size_bytes is None or device_size_bytes <= 0:
            return samples
        sector_size = 512
        total_sectors = device_size_bytes // sector_size
        if total_sectors <= 0:
            return samples
        picks = set()
        attempts = 0
        while len(picks) < count and attempts < count * 10:
            candidate = random.randint(1, max(1, total_sectors - 1))
            picks.add(candidate)
            attempts += 1
        for sector in sorted(picks):
            try:
                with open(device_path, "rb") as f:
                    f.seek(sector * sector_size)
                    data = f.read(sector_size)
                    hexdata = data.hex()
                    samples.append({
                        "sector_index": sector,
                        "offset_bytes": sector * sector_size,
                        "hex": hexdata
                    })
            except Exception as e:
                samples.append({
                    "sector_index": sector,
                    "offset_bytes": sector * sector_size,
                    "error": str(e)
                })
        return samples

    def run(self):
        result = {
            "success": False,
            "method": None,
            "pdf": None,
            "json": None,
            "final_hash": None,
            "txid": None,
            "log_path": None
        }

        device_path = self._device_path()
        method_name, base_cmd = NIST_METHODS.get(self.media_type, NIST_METHODS["Unknown"])

        if base_cmd[0] in ("sudo",):
            cmd = base_cmd + [device_path]
        else:
            cmd = base_cmd + [device_path]

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        base_name = f"{self.drive}_{timestamp}"
        log_file = os.path.join(self.out_dir, f"{base_name}.log")
        result["log_path"] = log_file

        log_entries = []
        prev_hash = ""

        start_entry = {
            "event": "start_wipe",
            "drive": self.drive,
            "device_path": device_path,
            "serial": self.serial,
            "media_type": self.media_type,
            "method_name": method_name,
            "timestamp": timestamp
        }
        entry_bytes = json.dumps(start_entry, sort_keys=True).encode("utf-8")
        prev_hash = self._chain_hash(prev_hash, entry_bytes)
        start_entry["chain_hash"] = prev_hash
        log_entries.append(start_entry)

        self.progress.emit(f"Using NIST method: {method_name}")
        self.progress.emit(f"Running command: {' '.join(cmd)}")
        try:
            if any("&&" in str(x) for x in cmd):
                cmd_str = " ".join(cmd)
                proc = subprocess.Popen(cmd_str, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
            else:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    ln = line.rstrip("\n")
                    self.progress.emit(ln)
                    log_entry = {
                        "event": "wipe_progress_line",
                        "line": ln,
                        "timestamp": time.strftime("%Y%m%d_%H%M%S")
                    }
                    eb = json.dumps(log_entry, sort_keys=True).encode("utf-8")
                    prev_hash = self._chain_hash(prev_hash, eb)
                    log_entry["chain_hash"] = prev_hash
                    log_entries.append(log_entry)

            returncode = proc.wait()
            success = (returncode == 0)
            result["success"] = success
            self.progress.emit(f"Process finished with return code: {returncode}")
        except Exception as e:
            self.progress.emit(f"Error running wipe command: {e}")
            log_entry = {
                "event": "wipe_error",
                "error": str(e),
                "timestamp": time.strftime("%Y%m%d_%H%M%S")
            }
            eb = json.dumps(log_entry, sort_keys=True).encode("utf-8")
            prev_hash = self._chain_hash(prev_hash, eb)
            log_entry["chain_hash"] = prev_hash
            log_entries.append(log_entry)
            result["success"] = False

        try:
            self.progress.emit("Starting random sector sampling...")
            dev_size = self._device_size_bytes()
            samples = self._sample_random_sectors(device_path, dev_size, self.sample_count)
            sample_entry = {
                "event": "sector_samples",
                "samples": samples,
                "timestamp": time.strftime("%Y%m%d_%H%M%S")
            }
            eb = json.dumps(sample_entry, sort_keys=True).encode("utf-8")
            prev_hash = self._chain_hash(prev_hash, eb)
            sample_entry["chain_hash"] = prev_hash
            log_entries.append(sample_entry)
            self.progress.emit(f"Sampled {len(samples)} sectors.")
        except Exception as e:
            self.progress.emit(f"Sector sampling failed: {e}")
            sample_entry = {
                "event": "sector_samples_error",
                "error": str(e),
                "timestamp": time.strftime("%Y%m%d_%H%M%S")
            }
            eb = json.dumps(sample_entry, sort_keys=True).encode("utf-8")
            prev_hash = self._chain_hash(prev_hash, eb)
            sample_entry["chain_hash"] = prev_hash
            log_entries.append(sample_entry)

        end_entry = {
            "event": "end_wipe",
            "timestamp": time.strftime("%Y%m%d_%H%M%S"),
            "success": result["success"]
        }
        eb = json.dumps(end_entry, sort_keys=True).encode("utf-8")
        prev_hash = self._chain_hash(prev_hash, eb)
        end_entry["chain_hash"] = prev_hash
        log_entries.append(end_entry)

        try:
            with open(log_file, "w") as f:
                json.dump({"entries": log_entries}, f, indent=2)
            self.progress.emit(f"Wipe log saved: {log_file}")
        except Exception as e:
            self.progress.emit(f"Failed to write log file: {e}")

        final_hash = prev_hash
        result["final_hash"] = final_hash

        try:
            txid = anchor_hash(final_hash)
            result["txid"] = txid
            self.progress.emit(f"Anchored final hash to ledger: {txid}")
        except Exception as e:
            self.progress.emit(f"Failed to anchor hash: {e}")

        try:
            pdf_file, json_file = generate_report_and_sign(
                drive=self.drive,
                serial=self.serial,
                method=method_name,
                success=result["success"],
                final_hash=final_hash,
                log_path=log_file,
                txid=result.get("txid")
            )
            result["pdf"] = pdf_file
            result["json"] = json_file
            self.progress.emit(f"Generated report: {pdf_file}, {json_file}")
        except Exception as e:
            self.progress.emit(f"Failed to generate signed report: {e}")

        self.finished.emit(result)
