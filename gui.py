# gui.py
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QFileDialog,
    QLabel, QVBoxLayout, QMessageBox, QTextEdit
)
import wipe
import os


class WiperApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SecureWiper GUI")
        self.resize(600, 350)

        layout = QVBoxLayout()

        self.label = QLabel(
            "Choose a file to securely wipe.\n"
            "Certificates (PDF + JSON) will be generated."
        )
        layout.addWidget(self.label)

        self.button = QPushButton("Select File to Wipe")
        self.button.clicked.connect(self.select_file)
        layout.addWidget(self.button)

        # Text box to show certificate paths
        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        layout.addWidget(self.output_box)

        self.setLayout(layout)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Wipe")
        if file_path:
            result = wipe.wipe_file(file_path)

            msg = QMessageBox()
            if result:
                pdf_file, json_file = result
                msg.setText(f"✅ File wiped successfully!\nCertificates generated.")
                msg.exec_()

                self.output_box.append("Certificates created:\n")
                self.output_box.append(f"📄 PDF: {pdf_file}")
                self.output_box.append(f"📝 JSON: {json_file}\n")

                # optional: auto-open PDF
                if os.path.exists(pdf_file):
                    os.system(f"xdg-open '{pdf_file}' &")

            else:
                msg.setText(f"❌ Failed to wipe {file_path}")
                msg.exec_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WiperApp()
    window.show()
    sys.exit(app.exec_())
