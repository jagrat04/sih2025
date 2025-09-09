import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout,
    QMessageBox, QTextEdit, QComboBox, QProgressBar
)
from drive_manager import list_drives
from wipe_manager import WipeThread

class WiperApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SecureWiper GUI")
        self.resize(700, 500)

        layout = QVBoxLayout()

        self.label = QLabel("Select a drive to wipe (method auto-selected per NIST):")
        layout.addWidget(self.label)

        # Drive dropdown
        self.drive_dropdown = QComboBox()
        layout.addWidget(self.drive_dropdown)

        # Refresh button
        self.refresh_button = QPushButton("Refresh Drives")
        self.refresh_button.clicked.connect(self.load_drives)
        layout.addWidget(self.refresh_button)

        # Start wipe button
        self.wipe_button = QPushButton("Start Wipe")
        self.wipe_button.clicked.connect(self.start_wipe)
        layout.addWidget(self.wipe_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Log box
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        self.setLayout(layout)
        self.load_drives()

    def load_drives(self):
        drives = list_drives()
        self.drive_dropdown.clear()
        for d in drives:
            if "error" in d:
                self.drive_dropdown.addItem(d["error"], None)
                continue
            display = f"{d['name']} | {d['size']} | {d['model']} | {d['media_type']} | {d.get('serial','')}"
            self.drive_dropdown.addItem(display, d)

    def start_wipe(self):
        drive_info = self.drive_dropdown.currentData()
        if not drive_info:
            QMessageBox.warning(self, "Error", "No drive selected")
            return

        # Confirm (uncomment if desired)
        # confirm = QMessageBox.question(
        #     self,
        #     "Confirm Wipe",
        #     f"Are you sure you want to wipe {drive_info['name']} "
        #     f"({drive_info['media_type']})?\n"
        #     f"NIST method will be auto-selected."
        # )
        # if confirm != QMessageBox.Yes:
        #     return

        self.progress_bar.show()
        self.log_box.clear()

        # Start wipe thread with auto method (decided inside wipe_manager)
        # The finished signal now returns a rich result tuple/object
        self.thread = WipeThread(drive_info["name"], drive_info["media_type"], drive_info.get("serial"))
        self.thread.progress.connect(self.update_log)
        self.thread.finished.connect(self.wipe_done)
        self.thread.start()

    def update_log(self, line):
        # May receive long strings; ensure UI remains responsive
        self.log_box.append(line)

    def wipe_done(self, result):
        """Result is a dict:
           {
             success: bool,
             method: str,
             pdf: str,
             json: str,
             final_hash: str,
             txid: str or None,
             log_path: str
           }
        """
        self.progress_bar.hide()

        drive = self.drive_dropdown.currentData()
        if result is None:
            QMessageBox.critical(self, "Error", "Wipe thread failed unexpectedly.")
            return

        success = result.get("success", False)
        method = result.get("method", "Unknown")
        pdf = result.get("pdf")
        js = result.get("json")
        final_hash = result.get("final_hash")
        txid = result.get("txid")

        msg = QMessageBox()
        if success:
            body = (f"✅ Wipe completed.\n"
                    f"Drive: {drive['name']}\n"
                    f"Method: {method}\n\n"
                    f"Reports:\n📄 {pdf}\n📝 {js}\n\n"
                    f"Verification Hash:\n{final_hash}\n")
            if txid:
                body += f"\nBlockchain TxID / Ledger ID:\n{txid}"
            msg.setText(body)
        else:
            body = (f"❌ Wipe failed for {drive['name']}.\n"
                    f"Method: {method}\n\n"
                    f"Reports (if any):\n📄 {pdf}\n📝 {js}\n\n"
                    f"Verification Hash:\n{final_hash if final_hash else 'N/A'}")
            if txid:
                body += f"\nLedger ID (partial): {txid}"
            msg.setText(body)
        msg.exec_()

        self.log_box.append("=== Wipe Done ===")
        if final_hash:
            self.log_box.append(f"Verification Hash: {final_hash}")
        if txid:
            self.log_box.append(f"Ledger TX/ID: {txid}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WiperApp()
    window.show()
    sys.exit(app.exec_())
