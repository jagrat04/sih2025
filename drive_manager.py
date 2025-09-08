# drive_manager.py
import subprocess

def get_boot_drive():
    """Find boot/system drive (mounted on /)."""
    try:
        output = subprocess.check_output(
            ["findmnt", "-n", "-o", "SOURCE", "/"], text=True
        ).strip()
        return output.replace("/dev/", "").rstrip("0123456789")
    except Exception:
        return None

# import subprocess

def get_drive_type(dev):
    try:
        # Get drive info
        output = subprocess.check_output(["lsblk", "-d", "-o", "NAME,ROTA,TYPE,MODEL", dev], text=True)
        if "nvme" in dev:
            return "NVMe SSD"
        elif "usb" in output.lower():
            return "USB"
        elif "mmc" in dev:
            return "SD Card"
        elif "0 disk" in output:  # non-rotational = SSD
            return "SATA SSD"
        elif "1 disk" in output:  # rotational = HDD
            return "HDD"
    except Exception as e:
        print("Error detecting type:", e)
    return "Unknown"



def list_drives():
    """Return list of drives with classification."""
    try:
        boot_drive = get_boot_drive()
        # TRAN (sata, nvme, usb, mmc) + TYPE (disk)
        output = subprocess.check_output(
            ["lsblk", "-d", "-o", "NAME,ROTA,TRAN,TYPE,SIZE,MODEL"], text=True
        )
        lines = output.strip().split("\n")[1:]
        drives = []

        for line in lines:
            parts = line.split()
            if not parts or parts[3] != "disk":
                continue

            name, rota, tran, dtype, size, *model = parts
            if name == boot_drive:
                continue

            model_str = " ".join(model)
            media_type = classify_drive(name, rota, tran)
            drives.append({
                "name": name,
                "size": size,
                "tran": tran,
                "rota": rota,
                "model": model_str,
                "media_type": media_type
            })
        return drives
    except Exception as e:
        return [{"error": str(e)}]


def classify_drive(name, rota, tran):
    """Classify media type based on TRAN and rota."""
    if tran == "nvme":
        return "NVMe M.2 SSD"
    elif tran == "sata" and rota == "1":
        return "HDD"
    elif tran == "sata" and rota == "0":
        return "SATA SSD"
    elif tran == "usb":
        return "USB Thumb Drive"
    elif tran == "mmc" or name.startswith("mmcblk"):
        return "SD / microSD"
    else:
        return "Unknown"