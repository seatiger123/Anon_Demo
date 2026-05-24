"""GPT-SoVITS API 服务管理器 — 自启动/停止/状态检测"""

import os
import socket
import subprocess
import threading
import time

from PySide6.QtCore import QObject, Signal

# ── GPT-SoVITS 路径配置 ──
GPT_SOVITS_DIR = r"C:\GPT-sovit\GPT-SoVITS-v2pro-20250604-nvidia50"
PYTHON_PATH = os.path.join(GPT_SOVITS_DIR, "runtime", "python.exe")
API_SCRIPT = os.path.join(GPT_SOVITS_DIR, "api_v2.py")
CONFIG_PATH = os.path.join(GPT_SOVITS_DIR, "GPT_SoVITS", "configs", "tts_infer.yaml")
HOST = "127.0.0.1"
PORT = 9880
TIMEOUT = 60  # 模型加载最长等待秒数


def _check_port(host: str, port: int) -> bool:
    """尝试 TCP 连接端口，判断服务是否已在运行。"""
    try:
        s = socket.create_connection((host, port), timeout=1)
        s.close()
        return True
    except (OSError, socket.error):
        return False


class GptSovitsServer(QObject):
    """Qt 感知的服务管理器，负责启动/停止 API 子进程。"""

    server_ready = Signal()       # API 就绪
    server_failed = Signal(str)   # 启动失败，附带错误信息

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process: subprocess.Popen | None = None
        self._stop_event = threading.Event()

    # ── 公共接口 ──

    def start(self):
        """检测服务状态，按需启动子进程。"""
        # 前置检查
        if not os.path.exists(PYTHON_PATH):
            self.server_failed.emit(
                f"GPT-SoVITS 运行环境不存在: {PYTHON_PATH}"
            )
            return
        if not os.path.exists(API_SCRIPT):
            self.server_failed.emit(f"API 脚本不存在: {API_SCRIPT}")
            return

        # 检测是否已在运行
        if _check_port(HOST, PORT):
            print("[GPT-SoVITS] 检测到服务已在运行")
            self.server_ready.emit()
            return

        print("[GPT-SoVITS] 正在启动服务...")
        try:
            self._process = subprocess.Popen(
                [
                    PYTHON_PATH, API_SCRIPT,
                    "-a", HOST,
                    "-p", str(PORT),
                    "-c", CONFIG_PATH,
                ],
                cwd=GPT_SOVITS_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception as e:
            self.server_failed.emit(f"启动 GPT-SoVITS 失败: {e}")
            return

        # 后台线程等待就绪
        thread = threading.Thread(target=self._wait_for_server, daemon=True)
        thread.start()

    def stop(self):
        """终止子进程。"""
        self._stop_event.set()
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(5)
            except Exception:
                pass
            self._process = None

    def cleanup(self):
        """供 app.aboutToQuit 连接的清理方法。"""
        self.stop()

    # ── 内部方法 ──

    def _wait_for_server(self):
        """轮询端口直到就绪或超时。"""
        start = time.time()
        while time.time() - start < TIMEOUT:
            if self._stop_event.is_set():
                return
            if _check_port(HOST, PORT):
                self.server_ready.emit()
                return
            time.sleep(1)

        self.server_failed.emit(
            f"GPT-SoVITS 启动超时（>{TIMEOUT}s），请检查日志"
        )
