# gui.py
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout,
    QMessageBox, QTextEdit, QComboBox, QProgressBar
)
from drive_manager import list_drives
from wipe_manager import WipeThread
import report_generator


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
            display = f"{d['name']} | {d['size']} | {d['model']} | {d['media_type']}"
            self.drive_dropdown.addItem(display, d)

    def start_wipe(self):
        drive_info = self.drive_dropdown.currentData()
        if not drive_info:
            QMessageBox.warning(self, "Error", "No drive selected")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Wipe",
            f"Are you sure you want to wipe {drive_info['name']} "
            f"({drive_info['media_type']})?\n"
            f"NIST method will be auto-selected."
        )
        if confirm != QMessageBox.Yes:
            return

        self.progress_bar.show()
        self.log_box.clear()

        # Start wipe thread with auto method (decided inside wipe_manager)
        self.thread = WipeThread(drive_info["name"], drive_info["media_type"])
        self.thread.progress.connect(self.update_log)
        self.thread.finished.connect(self.wipe_done)
        self.thread.start()

    def update_log(self, line):
        self.log_box.append(line)

    def wipe_done(self, result):
        self.progress_bar.hide()

        drive = self.drive_dropdown.currentData()
        success, method, pdf, js = result  # thread returns tuple

        msg = QMessageBox()
        if success:
            msg.setText(f"✅ Wipe completed.\n"
                        f"Drive: {drive['name']}\n"
                        f"Method: {method}\n"
                        f"Reports:\n📄 {pdf}\n📝 {js}")
        else:
            msg.setText(f"❌ Wipe failed for {drive['name']}.\n"
                        f"Reports:\n📄 {pdf}\n📝 {js}")
        msg.exec_()

        self.log_box.append("=== Wipe Done ===")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WiperApp()
    window.show()
    sys.exit(app.exec_())
