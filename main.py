import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, QThread, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from agent_worker import AgentWorker
from voice_worker import VoiceWorker
from gpt_sovits_server import GptSovitsServer
from ui.floating_widget import FloatingWidget
from ui.chat_window import ChatWindow


# ── 入场语音 ──
_voice_players = []


def _play_entrance_voice():
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "resources", "entrance_voice.wav"
    )
    if not os.path.exists(path):
        print(f"[Audio] Entrance voice not found: {path}")
        return

    print(f"[Audio] Playing entrance voice...")
    player = QMediaPlayer()
    output = QAudioOutput()
    player.setAudioOutput(output)
    player.setSource(QUrl.fromLocalFile(path))
    output.setVolume(0.8)
    player.play()

    _voice_players.append(player)
    _voice_players.append(output)
    player.mediaStatusChanged.connect(
        lambda status: _voice_players.clear()
        if status == QMediaPlayer.MediaStatus.EndOfMedia else None
    )


class UiRelay(QObject):
    """Lives in main thread. Routes worker signals to UI thread-safely.

    Without this relay, lambdas connected directly to a worker-thread QObject
    get called in the worker thread, causing "setParent" crashes.
    """

    def __init__(self, chat, voice_worker):
        super().__init__()
        self.chat = chat
        self._voice_worker = voice_worker

    def on_response(self, text: str):
        # 取消之前的语音生成（如果还在进行中）
        self._voice_worker.cancel()
        if self.chat.is_voice_mode():
            # 语音模式：中文 → 日文翻译 → 日文语音合成
            self.chat.set_loading_text("对方正在说话...")
            self._voice_worker.generate(text, text_lang="ja")
        else:
            # 文本模式：现有逻辑
            self.chat.display_splitted_response(text)

    def on_voice_ready(self, filepath: str, duration: float, spoken: str, original: str):
        self.chat.display_voice_response(spoken, filepath, duration, chinese_text=original, is_user=False)

    def on_voice_error(self, error_msg: str, original: str):
        # 语音生成失败，降级为文本显示
        print(f"[Voice] {error_msg}")
        self.chat.display_splitted_response(original)

    def on_error(self, text: str):
        self.chat.show_error(text)
        self.chat.set_loading(False)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # GPT-SoVITS 语音服务自启动
    gpt_sovits = GptSovitsServer()
    gpt_sovits.server_ready.connect(
        lambda: print("[GPT-SoVITS] API 服务就绪")
    )
    gpt_sovits.server_failed.connect(
        lambda msg: print(f"[GPT-SoVITS] {msg} — 语音功能将不可用")
    )
    gpt_sovits.start()
    app.aboutToQuit.connect(gpt_sovits.cleanup)

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

    # Voice worker thread
    voice_thread = QThread()
    voice_worker = VoiceWorker()
    voice_worker.moveToThread(voice_thread)
    voice_thread.finished.connect(voice_thread.deleteLater)

    # Relay — stays in main thread as the receiver for all worker signals
    relay = UiRelay(chat, voice_worker)

    # Floating widget -> Chat window
    floating.clicked.connect(chat.show)
    floating.clicked.connect(chat.raise_)
    floating.clicked.connect(chat.activateWindow)
    floating.theme_toggled.connect(chat.toggle_theme)

    # Chat window -> Agent worker (cross-thread, auto QueuedConnection)
    chat.message_sent.connect(worker.send_message)

    # Chat window voice mode toggle -> debug log
    chat.voice_mode_changed.connect(
        lambda on: print(f"[Voice] 语音模式={'开启' if on else '关闭'}")
    )

    # Agent worker -> relay (cross-thread, relay is in main thread, auto QueuedConnection)
    worker.response_received.connect(relay.on_response)
    worker.error_occurred.connect(relay.on_error)
    worker.status_changed.connect(lambda s: _play_entrance_voice() if s == "ready" else None)
    worker.status_changed.connect(lambda s: print(f"[Agent] {s}"))

    # Voice worker -> relay
    voice_worker.voice_ready.connect(relay.on_voice_ready)
    voice_worker.voice_error.connect(relay.on_voice_error)

    worker_thread.start()
    voice_thread.start()

    # 应用退出时清理
    app.aboutToQuit.connect(voice_thread.quit)
    app.aboutToQuit.connect(worker_thread.quit)
    app.aboutToQuit.connect(voice_thread.wait)
    app.aboutToQuit.connect(worker_thread.wait)

    floating.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
