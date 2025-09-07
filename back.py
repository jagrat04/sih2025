import subprocess
import os
import sys

WIPE_METHODS = {
    "1": "zero",       # Overwrite with zeros
    "2": "random",     # Overwrite with random data
    "3": "dodshort",   # DoD 5220.22-M short
    "4": "dod",        # Full DoD
    "5": "gutmann"     # Gutmann (35 passes)
}

def list_drives():
    print("\nAvailable drives:\n")
    output = subprocess.check_output(
        ["lsblk", "-d", "-o", "NAME,SIZE,MODEL,TRAN"], text=True
    )
    print(output)

def wipe_drive(drive, method):
    if method not in WIPE_METHODS:
        print("Invalid method selected!")
        return
    
    wipe_method = WIPE_METHODS[method]
    cmd = ["sudo", "nwipe", "--method", wipe_method, f"/dev/{drive}"]
    print(f"\nRunning: {' '.join(cmd)}\n")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print("Error: Failed to run nwipe. Is it installed and run as root?")

def main():
    while True:
        print("\n=== Drive Wiper Tool (Linux) ===")
        print("1. List drives")
        print("2. Wipe drive")
        print("3. Exit")
        
        choice = input("Select option: ")
        
        if choice == "1":
            list_drives()
        elif choice == "2":
            drive = input("Enter drive name (e.g. sdb): ")
            print("\nSelect wipe method:")
            for k, v in WIPE_METHODS.items():
                print(f"{k}. {v}")
            method = input("Enter method number: ")
            wipe_drive(drive, method)
        elif choice == "3":
            sys.exit(0)
        else:
            print("Invalid option")

if __name__ == "__main__":
    main()
