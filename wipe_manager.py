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

# NIST mapping table - Corrected to include --nogui for nwipe
NIST_METHODS = {
    "HDD": (
        "Overwrite 1-pass (NIST 800-88 Clear)",
        ["sudo", "nwipe", "--autonuke", "--nogui", "--method=zero"]
    ),
    "SATA SSD": (
        "Secure Erase (NIST 800-88 Purge)",
        ["sudo", "hdparm", "--user-master", "u", "--security-erase", "p"]
    ),
    "NVMe M.2 SSD": (
        "NVMe Format (NIST 800-88 Purge)",
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
    "Dummy Test": (
        "Dummy Overwrite",
        ["dd", "if=/dev/zero", "of=dummy_test.img", "bs=1M", "count=5", "status=progress"]
    ),
    "Unknown": (
        "Default Overwrite (NIST 800-88 Clear)",
        ["sudo", "nwipe", "--autonuke", "--nogui", "--method=zero"]
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
        # Create dummy file if it doesn't exist for the test option
        if self.media_type == "Dummy Test" and not os.path.exists("dummy_test.img"):
            with open("dummy_test.img", "wb") as f:
                f.truncate(5 * 1024 * 1024) # 5MB

    def _device_path(self):
        if self.media_type == "Dummy Test":
            return os.path.abspath("dummy_test.img")
        return f"/dev/{self.drive}"

    def _device_size_bytes(self):
        try:
            return os.path.getsize(self._device_path())
        except Exception:
            try:
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
        if total_sectors <= 1:
            return samples
        picks = set()
        # Ensure we don't try to sample more sectors than exist
        count = min(count, total_sectors)
        
        attempts = 0
        while len(picks) < count and attempts < count * 20:
            candidate = random.randint(0, total_sectors - 1)
            picks.add(candidate)
            attempts += 1
            
        for sector in sorted(list(picks)):
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
            "pdf": None,
            "json": None,
            "cert_data": None,
            "log_path": None
        }

        device_path = self._device_path()
        method_name, base_cmd = NIST_METHODS.get(self.media_type, NIST_METHODS["Unknown"])
        
        # FIX: Correctly construct the command for all cases
        cmd = list(base_cmd)
        is_dd_command = 'dd' in cmd
        
        if is_dd_command:
             # dd command needs its 'of=' part constructed with the full path
             for i, part in enumerate(cmd):
                 if part.startswith('of='):
                     cmd[i] = f"of={device_path}"
                     break
        else:
            # Most other commands just append the device path at the end
            cmd.append(device_path)


        timestamp = time.strftime("%Y%m%d_%H%M%S")
        base_name = f"{self.drive}_{timestamp}"
        log_file = os.path.join(self.out_dir, f"{base_name}.log")
        result["log_path"] = log_file

        log_entries = []
        prev_hash = hashlib.sha256(b"genesis").hexdigest()

        start_entry = {
            "event": "start_wipe",
            "drive": self.drive,
            "device_path": device_path,
            "serial": self.serial,
            "media_type": self.media_type,
            "method_name": method_name,
            "timestamp": time.time()
        }
        entry_bytes = json.dumps(start_entry, sort_keys=True).encode("utf-8")
        prev_hash = self._chain_hash(prev_hash, entry_bytes)
        start_entry["chain_hash"] = prev_hash
        log_entries.append(start_entry)

        self.progress.emit(f"Using method: {method_name}")
        self.progress.emit(f"Running command: {' '.join(cmd)}")
        
        proc = None
        try:
            # Using shell=True for commands with '&&' might be risky, but needed for hdparm chain
            use_shell = "&&" in " ".join(cmd)
            proc = subprocess.Popen(
                " ".join(cmd) if use_shell else cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=use_shell
            )

            for line in iter(proc.stdout.readline, ''):
                ln = line.strip()
                if ln:
                    self.progress.emit(ln)
                    log_entry = { "event": "wipe_progress", "line": ln, "timestamp": time.time() }
                    eb = json.dumps(log_entry, sort_keys=True).encode("utf-8")
                    prev_hash = self._chain_hash(prev_hash, eb)
                    log_entry["chain_hash"] = prev_hash
                    log_entries.append(log_entry)
            
            proc.stdout.close()
            returncode = proc.wait()
            success = (returncode == 0)
            result["success"] = success
            self.progress.emit(f"Process finished with return code: {returncode}")
        
        except Exception as e:
            self.progress.emit(f"Error running wipe command: {e}")
            log_entry = { "event": "wipe_error", "error": str(e), "timestamp": time.time() }
            eb = json.dumps(log_entry, sort_keys=True).encode("utf-8")
            prev_hash = self._chain_hash(prev_hash, eb)
            log_entry["chain_hash"] = prev_hash
            log_entries.append(log_entry)
            result["success"] = False
        finally:
            if proc and proc.poll() is None:
                proc.kill()


        self.progress.emit("Starting random sector sampling for verification...")
        dev_size = self._device_size_bytes()
        samples = self._sample_random_sectors(device_path, dev_size, self.sample_count)
        sample_entry = { "event": "sector_samples", "samples": samples, "timestamp": time.time() }
        eb = json.dumps(sample_entry, sort_keys=True).encode("utf-8")
        prev_hash = self._chain_hash(prev_hash, eb)
        sample_entry["chain_hash"] = prev_hash
        log_entries.append(sample_entry)
        self.progress.emit(f"Sampled {len(samples)} sectors.")

        final_hash = prev_hash
        txid = anchor_hash(final_hash)
        
        end_entry = {
            "event": "end_wipe",
            "timestamp": time.time(),
            "success": result["success"],
            "final_hash": final_hash,
            "txid": txid
        }
        eb = json.dumps(end_entry, sort_keys=True).encode("utf-8")
        prev_hash = self._chain_hash(prev_hash, eb)
        end_entry["chain_hash"] = prev_hash
        log_entries.append(end_entry)

        with open(log_file, "w") as f:
            json.dump({"log_entries": log_entries}, f, indent=2)

        # Generate certificate and reports
        try:
            json_path, pdf_path, cert_data_dict = generate_report_and_sign(
                drive=self.drive,
                serial=self.serial,
                wipe_method=method_name,
                success=result["success"],
                final_hash=final_hash,
                txid=txid
            )
            result["pdf"] = pdf_path
            result["json"] = json_path
            result["cert_data"] = cert_data_dict # This is the crucial part for the viewer
            self.progress.emit(f"Generated report: {pdf_path}")
        except Exception as e:
            self.progress.emit(f"Failed to generate signed report: {e}")

        self.finished.emit(result)

