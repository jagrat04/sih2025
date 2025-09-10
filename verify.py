import sys
import json
from blockchain_connector import get_ledger

def verify_by_txid(txid: str):
    """
    Verify a transaction by TXID against the blockchain ledger.
    """
    ledger = get_ledger()
    if txid in ledger:
        print("✅ Verified on blockchain!")
        print(f"TXID: {txid}")
        print(f"Hash: {ledger[txid]['hash']}")
    else:
        print(f"❌ TXID {txid} not found in blockchain records.")


def verify_by_json(cert_file: str):
    """
    Verify using a generated JSON certificate file.
    """
    try:
        with open(cert_file, "r") as f:
            cert = json.load(f)
    except Exception as e:
        print(f"❌ Error reading certificate: {e}")
        return

    txid = cert.get("ledger_txid")
    final_hash = cert.get("final_hash")

    if not txid or not final_hash:
        print("❌ Invalid certificate format. Missing TXID or hash.")
        return

    ledger = get_ledger()
    if txid in ledger:
        stored_hash = ledger[txid]["hash"]
        if stored_hash == final_hash:
            print("✅ Certificate Verified!")
            print(f"Drive: {cert.get('drive')}")
            print(f"Status: {cert.get('status')}")
            print(f"Final Hash: {final_hash}")
            print(f"TXID: {txid}")
        else:
            print("❌ Hash mismatch! Certificate has been tampered.")
            print(f"Expected: {stored_hash}")
            print(f"Found: {final_hash}")
    else:
        print(f"❌ TXID {txid} not found in blockchain records.")


def usage():
    print("Usage:")
    print("  python3 verify.py txid <transaction_id>")
    print("  python3 verify.py cert <certificate.json>")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        usage()
        sys.exit(1)

    mode = sys.argv[1]
    value = sys.argv[2]

    if mode == "txid":
        verify_by_txid(value)
    elif mode == "cert":
        verify_by_json(value)
    else:
        usage()
