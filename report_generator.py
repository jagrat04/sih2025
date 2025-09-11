import json
import os
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

KEYS_DIR = "keys"
WIPES_DIR = "wipes"

def ensure_dirs():
    """Ensure the necessary directories for keys and wipe reports exist."""
    os.makedirs(KEYS_DIR, exist_ok=True)
    os.makedirs(WIPES_DIR, exist_ok=True)

def load_private_key():
    """
    Loads an existing Ed25519 private key from the 'keys' directory.
    If no key exists, it generates a new one and saves it.
    """
    key_path = os.path.join(KEYS_DIR, "private_key.pem")
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)
    else:
        # Generate and save a new private key if one isn't found
        private_key = Ed25519PrivateKey.generate()
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        return private_key

def generate_pdf(cert_data, pdf_path):
    """Generates a PDF certificate from the provided data."""
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    # Title
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2.0, height - 1*inch, "Certificate of Data Erasure")

    # Certificate Details
    c.setFont("Helvetica", 11)
    text = c.beginText(1*inch, height - 2*inch)
    text.setLeading(18)  # Set line spacing

    for key, value in cert_data.items():
        # Use a monospaced font for long hashes to ensure alignment and readability
        if len(str(value)) > 70:
            text.setFont("Helvetica-Bold", 11)
            text.textLine(f"{key}:")
            text.setFont("Courier", 9)
            text.textLine(f"  {value}")
        else:
            text.setFont("Helvetica-Bold", 11)
            text.textOut(f"{key}: ")
            text.setFont("Helvetica", 11)
            text.textLine(str(value))
            
    c.drawText(text)
    
    # Footer
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(1*inch, 1*inch, "This certificate confirms sanitation in accordance with NIST 800-88 guidelines.")
    
    c.save()

def generate_report_and_sign(drive, serial, wipe_method, success, final_hash, txid):
    """
    Creates JSON and PDF reports, signs the data, and returns the certificate details.
    """
    ensure_dirs()
    timestamp = datetime.datetime.now()
    
    cert_data = {
        "Drive Name": drive,
        "Drive Serial": serial or "N/A",
        "Wipe Method": wipe_method,
        "Status": "Success" if success else "FAILED",
        "Timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "Verification Hash": final_hash,
        "Ledger ID": txid,
    }
    
    base_name = f"{drive.replace('/', '_')}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
    json_path = os.path.join(WIPES_DIR, f"{base_name}.json")
    pdf_path = os.path.join(WIPES_DIR, f"{base_name}.pdf")
    sig_path = os.path.join(WIPES_DIR, f"{base_name}.sig")

    # 1. Save JSON report
    with open(json_path, "w") as f:
        json.dump(cert_data, f, indent=4)

    # 2. Generate PDF certificate
    generate_pdf(cert_data, pdf_path)

    # 3. Sign the JSON data with the private key
    private_key = load_private_key()
    message = json.dumps(cert_data, sort_keys=True).encode()
    signature = private_key.sign(message)
    with open(sig_path, "wb") as f:
        f.write(signature)
    
    # Return file paths and the data dictionary for the GUI viewer
    return json_path, pdf_path, cert_data

