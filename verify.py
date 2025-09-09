import sys
import json
from blockchain_connector import get_ledger

def verify_by_txid(txid):
    ledger = get_ledger()
    if txid in ledger:
        print(f"✅ Verified on blockchain!\nTXID: {txid}\nHash: {ledger[txid]['hash']}")
    else:
        print(f"❌ TXID {txid} not found in blockchain records.")

def verify_by_json(cert_file):
    try:
        with open(cert_file, "r") as f:
            cert = json.load(f)
    except Exception as e:
        print(f"Error reading certificate: {e}")
        return

    txid = cert.get("ledger_txid")
    final_hash = cert.get("final_hash")

    if not txid or not final_hash:
        print("❌ Invalid certificate format.")
        return

    ledger = get_ledger()
    if txid in ledger and ledger[txid]["hash"] == final_hash:
        print(f"✅ Verified!\nDrive: {cert.get('drive')}\nHash: {final_hash}\nTXID: {txid}")
    else:
        print("❌ Verification failed! Hash mismatch or TXID not found.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 verify.py <txid>")
        print("  python3 verify.py <certificate.json>")
        sys.exit(1)

    arg = sys.argv[1]
    if arg.endswith(".json"):
        verify_by_json(arg)
    else:
        verify_by_txid(arg)
