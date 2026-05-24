"""GPT-SoVITS TTS 工具模块 — API 调用、音频时长获取、缓存管理"""

import os
import hashlib
import socket
import requests
import wave
import contextlib
import time
from pathlib import Path

GPT_SOVITS_URL = "http://127.0.0.1:9880/tts"
GPT_SOVITS_CONTROL_URL = "http://127.0.0.1:9880/control"
LM_STUDIO_API_URL = "http://127.0.0.1:1234/v1/chat/completions"
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "voice_cache")

# ── 千早爱音 参考音频配置 ──
REF_AUDIO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "anon_ref.wav")
PROMPT_TEXT = "千早アノンです。家の都合で変な時期の入学ですが、よかったら仲良くしてください。よろしくお願いします。"
PROMPT_LANG = "ja"


def _check_port(host: str = "127.0.0.1", port: int = 9880) -> bool:
    """尝试 TCP 连接端口，判断服务是否已在运行。"""
    try:
        s = socket.create_connection((host, port), timeout=1)
        s.close()
        return True
    except (OSError, socket.error):
        return False


def restart_server():
    """通过 /control?command=restart 重启 GPT-SoVITS 服务，确保模型状态完全重置。

    GPT-SoVITS 在处理完一次 TTS 请求后，模型内部状态可能卡死，
    导致后续请求的参考音频处理阶段停滞在 "Processing prompt 0.00%"。
    重启是唯一可靠的解决方法。
    """
    try:
        requests.get(GPT_SOVITS_CONTROL_URL, params={"command": "restart"}, timeout=5)
    except requests.RequestException:
        pass  # 重启会导致连接断开，异常是预期的

    # 等待服务重新就绪（最多 90 秒）
    for _ in range(90):
        if _check_port():
            time.sleep(3)  # 端口已开但模型可能还在加载
            return True
        time.sleep(1)

    raise RuntimeError("GPT-SoVITS 重启超时（>90s）")


def _ensure_cache_dir():
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)


def _content_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


def generate_voice_sync(text: str, text_lang: str = "zh") -> tuple[str, float]:
    """调用 GPT-SoVITS v2 API 生成语音（同步阻塞，在子线程中调用）。

    使用千早爱音的参考音频进行跨语言语音合成（日参 → 中出）。
    每次调用前会自动重启 GPT-SoVITS 服务，避免模型状态卡死。

    Args:
        text: 要合成的文本（中文）
        text_lang: 语言代码，默认 "zh"

    Returns:
        (wav_filepath, duration_seconds)

    Raises:
        requests.RequestException: API 调用失败时
        ValueError: 返回数据为空或格式不对时
    """
    _ensure_cache_dir()

    # 重启服务确保模型状态干净，避免 "Processing prompt 0.00%" 卡死
    restart_server()

    cache_name = f"{_content_hash(text)}_{int(time.time())}.wav"
    cache_path = os.path.join(CACHE_DIR, cache_name)

    # GPT-SoVITS v2 API 完整参数（全部显式指定以避免默认值问题）
    payload = {
        "text": text,
        "text_lang": text_lang,
        "ref_audio_path": REF_AUDIO_PATH,
        "prompt_text": PROMPT_TEXT,
        "prompt_lang": PROMPT_LANG,
        "top_k": 5,
        "top_p": 1,
        "temperature": 1,
        "text_split_method": "cut5",
        "batch_size": 1,
        "batch_threshold": 0.75,
        "split_bucket": True,
        "speed_factor": 1.0,
        "fragment_interval": 0.3,
        "seed": -1,
        "media_type": "wav",
        "streaming_mode": False,
        "parallel_infer": True,
        "repetition_penalty": 1.35,
        "sample_steps": 32,
        "super_sampling": False,
    }
    resp = requests.post(GPT_SOVITS_URL, json=payload, timeout=120)
    resp.raise_for_status()

    if not resp.content:
        raise ValueError("GPT-SoVITS 返回空数据")

    with open(cache_path, "wb") as f:
        f.write(resp.content)

    duration = get_audio_duration(cache_path)
    return cache_path, duration


def get_audio_duration(filepath: str) -> float:
    """获取 WAV 文件时长（秒）。"""
    try:
        with contextlib.closing(wave.open(filepath, "r")) as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / rate if rate > 0 else 0.0
    except Exception:
        return 0.0


def translate_to_japanese(chinese_text: str) -> str:
    """调用 LM Studio API 将中文翻译为日文。

    Args:
        chinese_text: 要翻译的中文文本

    Returns:
        翻译后的日文文本

    Raises:
        requests.RequestException: API 调用失败时
    """
    resp = requests.post(LM_STUDIO_API_URL, json={
        "model": "google/gemma-4-e4b",
        "messages": [
            {"role": "system", "content": "你是一个翻译助手。将用户输入的中文翻译成日语。注意事项：人名「千早爱音」必须翻译为「ちはや あのん」，禁止使用其他译法。只输出翻译结果，不要添加任何解释、引号或额外内容。"},
            {"role": "user", "content": chinese_text}
        ],
        "max_tokens": 512,
        "temperature": 0.3,
    }, timeout=30)
    resp.raise_for_status()
    result = resp.json()["choices"][0]["message"]["content"].strip()
    # 后置替换兜底：确保「千早爱音」的日语读法准确
    result = result.replace("千早愛音", "ちはや あのん")
    result = result.replace("千早アノン", "ちはや あのん")
    result = result.replace("チハヤ アノン", "ちはや あのん")
    result = result.replace("Anon", "あのん")
    return result


def cleanup_cache(max_age_hours: int = 24):
    """清理过期缓存文件。"""
    _ensure_cache_dir()
    now = time.time()
    cutoff = now - max_age_hours * 3600
    for fname in os.listdir(CACHE_DIR):
        fpath = os.path.join(CACHE_DIR, fname)
        if fname.endswith(".wav") and os.path.getmtime(fpath) < cutoff:
            os.remove(fpath)
