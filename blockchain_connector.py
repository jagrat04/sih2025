#blockchain_connector.py
import json
import os

# The ledger file that stores anchored hashes
LEDGER_FILE = "ledger.json"

def anchor_hash(final_hash: str):
    """
    Anchor the final wipe hash into a local JSON ledger.
    For now, the TXID is simply the hash itself.
    Returns the txid.
    """
    txid = final_hash  # in real blockchain this would be txid, here we just reuse the hash

    # Load existing ledger (if it exists)
    ledger = {}
    if os.path.exists(LEDGER_FILE):
        try:
            with open(LEDGER_FILE, "r") as f:
                ledger = json.load(f)
        except json.JSONDecodeError:
            # Reset if file corrupted
            ledger = {}

    # Add this txid/hash entry
    ledger[txid] = {
        "hash": final_hash
    }

    # Save updated ledger back to disk
    with open(LEDGER_FILE, "w") as f:
        json.dump(ledger, f, indent=2)

    return txid

def get_ledger():
    """
    Load the entire ledger dictionary.
    """
    if os.path.exists(LEDGER_FILE):
        try:
            with open(LEDGER_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def verify_hash(txid: str):
    """
    Check if a given txid (hash) exists in the ledger.
    """
    ledger = get_ledger()
    return txid in ledger
