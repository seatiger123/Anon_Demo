import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, QThread

from agent_worker import AgentWorker
from ui.floating_widget import FloatingWidget
from ui.chat_window import ChatWindow


class UiRelay(QObject):
    """Lives in main thread. Routes worker signals to UI thread-safely.

    Without this relay, lambdas connected directly to a worker-thread QObject
    get called in the worker thread, causing "setParent" crashes.
    """

    def __init__(self, chat):
        super().__init__()
        self.chat = chat

    def on_response(self, text: str):
        self.chat.display_message(text, is_user=False)
        self.chat.set_loading(False)

    def on_error(self, text: str):
        self.chat.show_error(text)
        self.chat.set_loading(False)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    floating = FloatingWidget()
    chat = ChatWindow()

    # Position floating widget at bottom-right
    screen = app.primaryScreen()
    sg = screen.availableGeometry()
    floating.move(
        sg.right() - floating.width() - 20,
        sg.bottom() - floating.height() - 60
    )

    # Agent worker thread
    worker_thread = QThread()
    worker = AgentWorker()
    worker.moveToThread(worker_thread)

    worker_thread.started.connect(worker.initialize)
    worker_thread.finished.connect(worker_thread.deleteLater)

    # Relay — stays in main thread as the receiver for all worker signals
    relay = UiRelay(chat)

    # Floating widget -> Chat window
    floating.clicked.connect(chat.show)
    floating.clicked.connect(chat.raise_)
    floating.clicked.connect(chat.activateWindow)

    # Chat window -> Agent worker (cross-thread, auto QueuedConnection)
    chat.message_sent.connect(worker.send_message)

    # Agent worker -> relay (cross-thread, relay is in main thread, auto QueuedConnection)
    worker.response_received.connect(relay.on_response)
    worker.error_occurred.connect(relay.on_error)
    worker.status_changed.connect(lambda s: print(f"[Agent] {s}"))

    worker_thread.start()

    floating.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()