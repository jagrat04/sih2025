# wipe.py
import os
import json
from datetime import datetime
from reportlab.pdfgen import canvas
from cryptography.fernet import Fernet

# generate or reuse encryption key (for signing wipe certificates)
KEY_FILE = "certificate.key"
if not os.path.exists(KEY_FILE):
    with open(KEY_FILE, "wb") as kf:
        kf.write(Fernet.generate_key())

with open(KEY_FILE, "rb") as kf:
    fernet = Fernet(kf.read())


def generate_certificate(file_path, status):
    """Generate PDF + JSON certificate for wipe."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cert_data = {
        "file": file_path,
        "status": status,
        "timestamp": timestamp,
    }

    # sign data (tamper-proof)
    signature = fernet.encrypt(json.dumps(cert_data).encode()).decode()
    cert_data["signature"] = signature

    # JSON certificate
    json_file = f"{file_path}_wipe_certificate.json"
    with open(json_file, "w") as jf:
        json.dump(cert_data, jf, indent=4)

    # PDF certificate
    pdf_file = f"{file_path}_wipe_certificate.pdf"
    c = canvas.Canvas(pdf_file)
    c.setFont("Helvetica", 12)
    c.drawString(100, 750, "SecureWiper - Wipe Certificate")
    c.drawString(100, 720, f"File: {file_path}")
    c.drawString(100, 700, f"Status: {status}")
    c.drawString(100, 680, f"Timestamp: {timestamp}")
    c.drawString(100, 660, f"Signature: {signature[:60]}...")
    c.save()

    print(f"Certificate generated: {pdf_file}, {json_file}")
    return pdf_file, json_file


def wipe_file(file_path, passes=3):
    """Securely wipe a file with random data (default 3 passes)."""
    if not os.path.isfile(file_path):
        print(f"File {file_path} not found!")
        generate_certificate(file_path, "FAILED - Not Found")
        return None

    length = os.path.getsize(file_path)

    with open(file_path, "ba+", buffering=0) as f:
        for i in range(passes):
            print(f"Pass {i+1}/{passes} wiping...")
            f.seek(0)
            f.write(os.urandom(length))

    os.remove(file_path)
    print(f"File {file_path} securely wiped.")

    # return cert file paths
    pdf_file, json_file = generate_certificate(file_path, "SUCCESS - Wiped")
    return pdf_file, json_file
