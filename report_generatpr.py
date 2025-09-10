import json
import os
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

KEYS_DIR = "keys"

def ensure_wipes_folder():
    if not os.path.exists("wipes"):
        os.makedirs("wipes")

def load_private_key():
    """Load or generate an Ed25519 private key"""
    if not os.path.exists(KEYS_DIR):
        os.makedirs(KEYS_DIR)

    key_path = os.path.join(KEYS_DIR, "private_key.pem")
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)
    else:
        # Generate new private key
        private_key = Ed25519PrivateKey.generate()
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        return private_key

def generate_pdf(cert_data, pdf_path):
    """Generate PDF certificate"""
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, height - 80, "Secure Wipe Certificate")

    c.setFont("Helvetica", 12)
    y = height - 120
    for key, value in cert_data.items():
        c.drawString(50, y, f"{key}: {value}")
        y -= 20

    c.showPage()
    c.save()

def generate_report_and_sign(drive, wipe_method, final_hash, txid):
    """
    Generate JSON + PDF certificate and sign the JSON
    drive        - device name
    wipe_method  - wipe method string
    final_hash   - final computed hash
    txid         - transaction ID returned from blockchain_connector.anchor_hash()
    """
    ensure_wipes_folder()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    cert_data = {
        "drive": drive,
        "wipe_method": wipe_method,
        "final_hash": final_hash,
        "ledger_txid": txid,   # ✅ now using the correct txid returned by blockchain
        "timestamp": timestamp,
        "status": "Wipe completed successfully"
    }

    json_path = f"wipes/{drive}_{timestamp}.json"
    pdf_path = f"wipes/{drive}_{timestamp}.pdf"
    sig_path = f"wipes/{drive}_{timestamp}.sig"

    # Save JSON
    with open(json_path, "w") as f:
        json.dump(cert_data, f, indent=4)

    # Save PDF
    generate_pdf(cert_data, pdf_path)

    # Sign the JSON
    private_key = load_private_key()
    message = json.dumps(cert_data, sort_keys=True).encode()
    signature = private_key.sign(message)
    with open(sig_path, "wb") as f:
        f.write(signature)

    print(f"[+] Certificate generated:\n - {json_path}\n - {pdf_path}\n - {sig_path}")
    return json_path, pdf_path, sig_path
