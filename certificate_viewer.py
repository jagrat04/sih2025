import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QDialogButtonBox,
    QFormLayout, QWidget, QHBoxLayout
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from verify import verify_by_json_data

class CertificateViewer(QDialog):
    """
    A dialog window to display wipe certificate details and offer verification.
    """
    def __init__(self, result_data, parent=None):
        super().__init__(parent)
        self.result_data = result_data
        self.setWindowTitle("Wipe Certificate")
        self.setMinimumWidth(600)

        # Main layout
        main_layout = QVBoxLayout(self)

        # Title
        title = QLabel("Secure Wipe Certificate of Erasure")
        title.setFont(QFont("Helvetica-Bold", 16))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Form layout for certificate data
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignRight)

        # Extract data for display
        self.cert_data = self.result_data.get("cert_data", {})
        pdf_path = self.result_data.get("pdf", "N/A")

        # Data fields to display
        fields = {
            "Status": self.cert_data.get("status", "Unknown"),
            "Drive": self.cert_data.get("drive", "N/A"),
            "Serial Number": self.cert_data.get("serial", "N/A"),
            "Wipe Method": self.cert_data.get("wipe_method", "N/A"),
            "Timestamp": self.cert_data.get("timestamp", "N/A"),
            "Final Verification Hash": self.cert_data.get("final_hash", "N/A"),
            "Ledger TXID": self.cert_data.get("ledger_txid", "N/A"),
            "PDF Report": pdf_path,
        }
        
        for label, value in fields.items():
            value_label = QLabel(str(value))
            value_label.setFont(QFont("Courier New", 10))
            value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            form_layout.addRow(f"<b>{label}:</b>", value_label)

        main_layout.addWidget(form_widget)
        
        # --- Verification Section ---
        self.verification_status = QLabel("Not Verified")
        self.verification_status.setAlignment(Qt.AlignCenter)
        self.verification_status.setFont(QFont("Helvetica-Bold", 12))
        main_layout.addWidget(self.verification_status)

        # --- Buttons ---
        button_layout = QHBoxLayout()

        self.verify_button = QPushButton("Verify Certificate")
        self.verify_button.clicked.connect(self.run_verification)
        button_layout.addWidget(self.verify_button)

        self.open_pdf_button = QPushButton("Open PDF Report")
        self.open_pdf_button.setEnabled(os.path.exists(pdf_path))
        self.open_pdf_button.clicked.connect(lambda: self.open_file(pdf_path))
        button_layout.addWidget(self.open_pdf_button)

        main_layout.addLayout(button_layout)
        
        # --- Close Button ---
        self.close_button = QDialogButtonBox(QDialogButtonBox.Close)
        self.close_button.rejected.connect(self.reject)
        main_layout.addWidget(self.close_button)

    def run_verification(self):
        """
        Runs the verification logic from verify.py and updates the UI.
        """
        is_valid, message = verify_by_json_data(self.cert_data)

        if is_valid:
            self.verification_status.setText(f"✅ VERIFIED\n{message}")
            self.verification_status.setStyleSheet("color: green;")
        else:
            self.verification_status.setText(f"❌ VERIFICATION FAILED\n{message}")
            self.verification_status.setStyleSheet("color: red;")
        
        self.verify_button.setEnabled(False)

    def open_file(self, file_path):
        """Opens a file using the default OS application."""
        if sys.platform == "win32":
            os.startfile(file_path)
        elif sys.platform == "darwin": # macOS
            subprocess.run(["open", file_path])
        else: # linux
            subprocess.run(["xdg-open", file_path])
