"""语音生成工作线程 — 在子线程中调用 GPT-SoVITS API，不阻塞 UI"""

from PySide6.QtCore import QObject, Signal, Slot

from voice_utils import generate_voice_sync, translate_to_japanese


class VoiceWorker(QObject):
    voice_ready = Signal(str, float, str, str)  # filepath, duration, spoken_text, original_text
    voice_error = Signal(str, str)               # error_message, original_text

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancelled = False

    @Slot(str, str)
    def generate(self, text: str, text_lang: str = "zh"):
        """在子线程中翻译（如需）并调用 GPT-SoVITS API 生成语音。

        Args:
            text: 原始文本（语音模式中文，普通模式直接合成）
            text_lang: 目标语音语言代码，默认 "zh"
                       "ja" 时先翻译再合成
        """
        self._cancelled = False
        try:
            original_text = text
            actual_text = text
            # 日文语音模式：先翻译
            if text_lang == "ja":
                actual_text = translate_to_japanese(text)
                if self._cancelled:
                    return

            filepath, duration = generate_voice_sync(actual_text, text_lang=text_lang)
            if self._cancelled:
                return
            if duration <= 0:
                self.voice_error.emit("语音生成失败：音频时长为零", original_text)
                return
            self.voice_ready.emit(filepath, duration, actual_text, original_text)
        except Exception as e:
            if not self._cancelled:
                self.voice_error.emit(f"语音生成失败: {str(e)}", original_text)

    def cancel(self):
        """取消正在进行的生成。"""
        self._cancelled = True
