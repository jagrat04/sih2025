# report_generator.py
import datetime
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

def generate_report(drive, method, success):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{drive}_{timestamp}"
    pdf_file = f"{base_name}.pdf"
    json_file = f"{base_name}.json"

    data = {
        "drive": drive,
        "method": method,
        "timestamp": timestamp,
        "status": "success" if success else "failed"
    }
    with open(json_file, "w") as f:
        json.dump(data, f, indent=4)

    c = canvas.Canvas(pdf_file, pagesize=letter)
    c.drawString(100, 750, "Secure Wipe Report")
    c.drawString(100, 720, f"Drive: {drive}")
    c.drawString(100, 700, f"Method: {method}")
    c.drawString(100, 680, f"Time: {timestamp}")
    c.drawString(100, 660, f"Status: {data['status']}")
    c.save()

    return pdf_file, json_file
