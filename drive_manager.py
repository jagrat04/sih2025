#drive_manager.py
import subprocess

def get_boot_drive():
    """Find boot/system drive (mounted on /). Return base name like 'sda'."""
    try:
        output = subprocess.check_output(
            ["findmnt", "-n", "-o", "SOURCE", "/"], text=True
        ).strip()
        if output.startswith("/dev/"):
            # strip partition number
            dev = output.replace("/dev/", "")
            # e.g., sda1 -> sda
            base = dev.rstrip("0123456789")
            return base
        return None
    except Exception:
        return None

def get_drive_type(dev):
    try:
        # if dev is like "/dev/nvme0n1" user might pass with or without /dev/
        dev_arg = dev if dev.startswith("/dev/") else f"/dev/{dev}"
        # get transport & rota info
        out = subprocess.check_output(["lsblk", "-d", "-o", "NAME,ROTA,TRAN,TYPE,MODEL,SERIAL", dev_arg], text=True)
        lower = out.lower()
        if "nvme" in dev_arg or "nvme" in lower:
            return "NVMe SSD"
        if "usb" in lower:
            return "USB"
        if "mmc" in dev_arg or "mmcblk" in lower:
            return "SD Card"
        # fallback: look for rota 0/1
        # parse out rota value
        lines = out.strip().splitlines()
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 2:
                rota = parts[1]
                if rota == "1":
                    return "HDD"
                elif rota == "0":
                    return "SATA SSD"
    except Exception as e:
        print("Error detecting type:", e)
    return "Unknown"


def list_drives():
    """Return list of drives with classification and serial number if available."""
    try:
        boot_drive = get_boot_drive()
        # get NAME,ROTA,TRAN,TYPE,SIZE,MODEL,SERIAL
        output = subprocess.check_output(
            ["lsblk", "-d", "-o", "NAME,ROTA,TRAN,TYPE,SIZE,MODEL,SERIAL"], text=True
        )
        lines = output.strip().split("\n")[1:]
        drives = []

        for line in lines:
            parts = line.split()
            if not parts:
                continue
            # we need to be careful splitting: model may contain spaces, but lsblk lists columns,
            # using indices: NAME(0), ROTA(1), TRAN(2), TYPE(3), SIZE(4), MODEL(5..-2), SERIAL(-1)
            # A robust way: use subprocess to call lsblk per-device if parsing fails.
            # For simplicity, attempt naive parse and fallback.
            try:
                name = parts[0]
                rota = parts[1]
                tran = parts[2]
                dtype = parts[3]
                size = parts[4]
                serial = parts[-1] if len(parts) >= 7 else ""
                model_parts = parts[5:-1] if len(parts) >= 7 else parts[5:]
                model_str = " ".join(model_parts).strip()
            except Exception:
                # fallback: call lsblk for this device specifically
                try:
                    out2 = subprocess.check_output(["lsblk", "-dn", "-o", "NAME,SIZE,MODEL,SERIAL,TRAN,ROTA", name], text=True)
                    p = out2.strip().split()
                    name = p[0]
                    size = p[1]
                    model_str = p[2] if len(p) > 2 else ""
                    serial = p[3] if len(p) > 3 else ""
                    tran = p[4] if len(p) > 4 else ""
                    rota = p[5] if len(p) > 5 else ""
                    dtype = "disk"
                except Exception:
                    continue

            if dtype != "disk":
                continue

            if name == boot_drive:
                continue

            media_type = classify_drive(name, rota, tran)
            drives.append({
                "name": name,
                "size": size,
                "tran": tran,
                "rota": rota,
                "model": model_str,
                "serial": serial,
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
