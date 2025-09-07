# wipe.py
import subprocess
import os
import datetime
import json

WIPE_METHODS = {
    "1": "zero",       # Overwrite with zeros
    "2": "random",     # Overwrite with random data
    "3": "dodshort",   # DoD 5220.22-M short
    "4": "dod",        # Full DoD
    "5": "gutmann"     # Gutmann (35 passes)
}


def wipe_drive(drive, method):
    if method not in WIPE_METHODS:
        return False, "Invalid method"

    wipe_method = WIPE_METHODS[method]
    cmd = ["sudo", "nwipe", "--method", wipe_method, f"/dev/{drive}"]
    try:
        subprocess.run(cmd, check=True)
        return True, f"/dev/{drive} wiped with {wipe_method}"
    except subprocess.CalledProcessError as e:
        return False, str(e)


def wipe_file(file_path):
    """Wipes a file using shred, then creates PDF + JSON certificates."""
    if not os.path.exists(file_path):
        return None

    try:
        subprocess.run(["shred", "-u", "-v", file_path], check=True)

        # Generate certificates
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.basename(file_path)
        pdf_file = f"{base_name}_{timestamp}.pdf"
        json_file = f"{base_name}_{timestamp}.json"

        # Write JSON certificate
        cert_data = {
            "file": base_name,
            "timestamp": timestamp,
            "method": "shred -u -v (secure delete)"
        }
        with open(json_file, "w") as f:
            json.dump(cert_data, f, indent=4)

        # Create PDF certificate
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(pdf_file, pagesize=letter)
        c.drawString(100, 750, "Secure Wipe Certificate")
        c.drawString(100, 720, f"File: {base_name}")
        c.drawString(100, 700, f"Time: {timestamp}")
        c.drawString(100, 680, f"Method: shred -u -v")
        c.save()

        return pdf_file, json_file
    except Exception as e:
        print("Error wiping file:", e)
        return None
