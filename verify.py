import sys
import json
from blockchain_connector import get_ledger

def verify_by_txid(txid):
    """
    Verifies a transaction ID against the ledger.
    Returns: (bool, str) tuple of (success, message)
    """
    ledger = get_ledger()
    if txid in ledger:
        message = f"Verified on ledger!\nTXID: {txid}\nHash: {ledger[txid]['hash']}"
        return True, message
    else:
        message = f"TXID {txid} not found in ledger records."
        return False, message

def verify_by_json_data(cert_data):
    """
    Verifies a certificate from a dictionary object.
    This is the function the certificate viewer imports.
    Returns: (bool, str) tuple of (success, message)
    """
    txid = cert_data.get("ledger_txid")
    final_hash = cert_data.get("final_hash")

    if not txid or not final_hash:
        return False, "Invalid certificate format (missing hash or txid)."

    ledger = get_ledger()
    if txid in ledger and ledger[txid]["hash"] == final_hash:
        message = f"Hash matches ledger record for drive {cert_data.get('drive')}."
        return True, message
    elif txid in ledger:
        return False, "Hash mismatch! The certificate may be fraudulent."
    else:
        return False, "TXID not found in ledger."

def verify_by_json_file(cert_file):
    """
    Verifies a certificate from a JSON file path (for CLI use).
    """
    try:
        with open(cert_file, "r") as f:
            cert = json.load(f)
        is_valid, message = verify_by_json_data(cert)
        if is_valid:
            print(f"✅ VERIFIED\n{message}")
        else:
            print(f"❌ VERIFICATION FAILED\n{message}")
    except Exception as e:
        print(f"Error reading certificate: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 verify.py <txid>")
        print("  python3 verify.py <certificate.json>")
        sys.exit(1)

    arg = sys.argv[1]
    if arg.endswith(".json"):
        verify_by_json_file(arg)
    else:
        is_valid, message = verify_by_txid(arg)
        print(message)

