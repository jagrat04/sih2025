# gui.py
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout,
    QMessageBox, QTextEdit, QComboBox
)
import wipe


class WiperApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SecureWiper GUI")
        self.resize(600, 400)

        layout = QVBoxLayout()

        self.label = QLabel("Select a drive and wipe method:")
        layout.addWidget(self.label)

        # Button to refresh drive list
        self.refresh_button = QPushButton("Refresh Drive List")
        self.refresh_button.clicked.connect(self.load_drives)
        layout.addWidget(self.refresh_button)

        # Dropdown for drives
        self.drive_dropdown = QComboBox()
        layout.addWidget(self.drive_dropdown)

        # Dropdown for wipe methods
        self.method_dropdown = QComboBox()
        for k, v in wipe.WIPE_METHODS.items():
            self.method_dropdown.addItem(f"{k}. {v}", k)
        layout.addWidget(self.method_dropdown)

        # Wipe button
        self.wipe_button = QPushButton("Start Wipe")
        self.wipe_button.clicked.connect(self.start_wipe)
        layout.addWidget(self.wipe_button)

        # Output box
        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        layout.addWidget(self.output_box)

        self.setLayout(layout)
        self.load_drives()

    def load_drives(self):
        drives = wipe.list_drives()
        self.drive_dropdown.clear()
        for d in drives:
            # first word in line is the drive name
            drive_name = d.split()[0]
            self.drive_dropdown.addItem(d, drive_name)

    def start_wipe(self):
        drive = self.drive_dropdown.currentData()
        method = self.method_dropdown.currentData()
        success, message = wipe.wipe_drive(drive, method)

        msg = QMessageBox()
        if success:
            msg.setText(f"✅ Success: {message}")
        else:
            msg.setText(f"❌ Failed: {message}")
        msg.exec_()

        self.output_box.append(message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WiperApp()
    window.show()
    sys.exit(app.exec_())
