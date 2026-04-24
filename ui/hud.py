"""
HELIX — Voice HUD (Phase 5 full implementation)
PyQt6 non-blocking UI with async worker threads.

Current state (Phase 1):  Shell skeleton — window launches, shows status.
Phase 5 target:           Full voice capture, animated waveform, response display.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor, QPalette


# ── Worker Thread — keeps UI non-blocking ──────────────────
class HelixWorker(QObject):
    """Runs router.process() in background thread."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, router, prompt: str):
        super().__init__()
        self.router = router
        self.prompt = prompt

    def run(self):
        try:
            response = self.router.process(self.prompt)
            self.finished.emit(response)
        except Exception as e:
            self.error.emit(str(e))


# ── Main HUD Window ────────────────────────────────────────
class HelixHUD(QMainWindow):
    def __init__(self, router=None):
        super().__init__()
        self.router = router
        self.thread = None
        self.worker = None
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle("HELIX — AI OS")
        self.setMinimumSize(700, 500)
        self.setStyleSheet("""
            QMainWindow { background-color: #0a0a0f; }
            QWidget { background-color: #0a0a0f; color: #00ff88; font-family: 'Consolas'; }
            QTextEdit { background-color: #0d1117; border: 1px solid #00ff4430;
                        border-radius: 6px; padding: 8px; font-size: 13px; }
            QLineEdit { background-color: #0d1117; border: 1px solid #00ff88;
                        border-radius: 6px; padding: 8px; font-size: 13px; color: #ffffff; }
            QPushButton { background-color: #00ff4420; border: 1px solid #00ff44;
                          border-radius: 6px; padding: 8px 16px; font-size: 13px; }
            QPushButton:hover { background-color: #00ff4440; }
            QPushButton:disabled { border-color: #333; color: #555; }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("◈  H E L I X")
        title.setFont(QFont("Consolas", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #00ff88; letter-spacing: 4px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Status bar
        self.status = QLabel("● ONLINE  |  Sentinel: llama3  |  Oracle: Gemini")
        self.status.setStyleSheet("color: #00ff4480; font-size: 11px;")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)

        # Output display
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("HELIX responses appear here...")
        layout.addWidget(self.output)

        # Input row
        input_row = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Type command or press 🎤 to speak...")
        self.input_box.returnPressed.connect(self._on_submit)
        input_row.addWidget(self.input_box)

        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setFixedWidth(48)
        self.mic_btn.setToolTip("Voice input (Phase 5)")
        self.mic_btn.clicked.connect(self._on_mic)
        input_row.addWidget(self.mic_btn)

        self.send_btn = QPushButton("Send")
        self.send_btn.setFixedWidth(80)
        self.send_btn.clicked.connect(self._on_submit)
        input_row.addWidget(self.send_btn)

        layout.addLayout(input_row)

    def _on_submit(self):
        prompt = self.input_box.text().strip()
        if not prompt or not self.router:
            return
        self.input_box.clear()
        self._set_busy(True)
        self.output.append(f"\n> {prompt}")
        self._run_in_thread(prompt)

    def _on_mic(self):
        self.output.append("\n[Voice input coming in Phase 5]")

    def _run_in_thread(self, prompt: str):
        self.thread = QThread()
        self.worker = HelixWorker(self.router, prompt)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_response)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.thread.start()

    def _on_response(self, text: str):
        self.output.append(f"\nHELIX: {text}\n")
        self._set_busy(False)

    def _on_error(self, err: str):
        self.output.append(f"\n[ERROR] {err}\n")
        self._set_busy(False)

    def _set_busy(self, busy: bool):
        self.send_btn.setEnabled(not busy)
        self.input_box.setEnabled(not busy)
        self.status.setText("● PROCESSING..." if busy else
                            "● ONLINE  |  Sentinel: llama3  |  Oracle: Gemini")


def launch_hud(router=None):
    app = QApplication(sys.argv)
    window = HelixHUD(router=router)
    window.show()
    sys.exit(app.exec())
