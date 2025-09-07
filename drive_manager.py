# drive_manager.py
import subprocess

def get_boot_drive():
    """Find boot/system drive (mounted on /)."""
    try:
        output = subprocess.check_output(
            ["findmnt", "-n", "-o", "SOURCE", "/"], text=True
        ).strip()
        # e.g. /dev/sda1 → sda
        return output.replace("/dev/", "").rstrip("0123456789")
    except Exception:
        return None


def list_drives():
    """List available drives excluding the boot drive."""
    try:
        boot_drive = get_boot_drive()
        output = subprocess.check_output(
            ["lsblk", "-d", "-o", "NAME,SIZE,MODEL,TRAN"], text=True
        )
        lines = output.strip().split("\n")[1:]  # skip header
        drives = []
        for line in lines:
            parts = line.split()
            if not parts:
                continue
            name = parts[0]
            if name == boot_drive:
                continue
            drives.append(line)
        return drives
    except Exception as e:
        return [f"Error: {e}"]
