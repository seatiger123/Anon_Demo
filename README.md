# 千早爱音 AI Chatbot 🎸

一个基于本地大语言模型的桌面 AI 聊天助手，角色为《BanG Dream! It's MyGO!!!!!》中的 **千早爱音**。
支持语音对话，可将 AI 回复翻译为日文并通过 GPT-SoVITS 合成语音朗读。

## 功能

- **悬浮头像** — 桌面右下角的圆形头像，鼠标悬停放大，可拖拽移动
- **个性聊天** — 爱音角色扮演，符合原作性格与语气，简短活泼的回复风格
- **原生窗口** — 无边框圆角聊天窗口，支持 Win32 原生边缘拖拽调整大小
- **逐条显示** — AI 回复按句子拆分，模拟真人打字节奏
- **深色模式** — 支持一键切换亮色/深色主题
- **语音模式** — 输入框旁「🎤 语音」开关，开启后 AI 回复将翻译为日文并合成语音朗读
- **语音气泡** — 微信风格的语音消息气泡，点击播放/暂停，支持波形动画和右键「转文字」
- **入场语音** — AI 就绪后自动播放入场音效
- **对话记忆** — 基于 LangGraph 的 SQLite 检查点，保留多轮对话上下文
- **GPT-SoVITS 自启动** — 程序启动时自动拉起 GPT-SoVITS API 服务，无需手动操作
- **离线运行** — 完全本地推理，无需联网

## 环境要求

- Python 3.10+
- [LM Studio](https://lmstudio.ai/) 或任何兼容 OpenAI API 的本地推理服务
- [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) v2/v2Pro（语音模式可选）

## 安装

```bash
# 克隆仓库
git clone https://github.com/seatiger123/Anon_Demo.git
cd Anon_Demo

# 安装依赖
pip install PySide6 langchain langchain-openai langgraph langgraph-checkpoint-sqlite requests
```

## 使用

### 文本模式

1. 启动 LM Studio，加载模型（推荐 `google/gemma-4-e4b`），开启本地服务器（默认 `http://127.0.0.1:1234`）
2. 运行程序：

```bash
python main.py
```

3. 点击桌面的粉色圆形头像打开聊天窗口，开始与爱音对话

### 语音模式

语音模式需要额外安装 [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) v2Pro，并配置参考音频路径。

1. 在 `voice_utils.py` 中配置你的 GPT-SoVITS 路径和参考音频：

```python
REF_AUDIO_PATH = r"C:\path\to\your\reference_audio.wav"
PROMPT_TEXT = "参考音频的日文原文"
PROMPT_LANG = "ja"
```

2. 正常启动 `main.py`，程序会自动启动 GPT-SoVITS API 服务
3. 在输入框点击「🎤 语音」按钮切换到语音模式
4. 发送消息，AI 回复将自动翻译为日文并通过语音朗读

## 项目结构

```
Anon_Demo/
├── main.py                 # 入口：创建窗口、管理线程、信号中继
├── agent_worker.py         # AI 工作线程：LangChain Agent + LLM 调用
├── agent_MAIN.py           # Agent 测试脚本
├── gpt_sovits_server.py    # GPT-SoVITS API 服务自启动管理器
├── voice_worker.py         # 语音生成工作线程（异步调用 TTS API）
├── voice_utils.py          # TTS 工具模块（API 调用、翻译、缓存管理）
├── system_prompt.txt       # 角色设定提示词（爱音的人设与回复规则）
├── ui/
│   ├── chat_window.py      # 聊天窗口 UI（气泡消息、语音气泡、主题切换）
│   └── floating_widget.py  # 桌面悬浮头像（拖拽、悬停动画、右键菜单）
└── resources/
    ├── icon.png            # 悬浮头像图标
    ├── entrance_voice.wav  # 入场语音
    └── voice_cache/        # 语音缓存目录（自动生成）
```

## 技术栈

- **[PySide6](https://pypi.org/project/PySide6/)** — Qt for Python 桌面 UI
- **[LangChain](https://www.langchain.com/)** / **[LangGraph](https://langchain-ai.github.io/langgraph/)** — AI Agent 框架与对话状态管理
- **[LangGraph Checkpoint (SQLite)](https://langchain-ai.github.io/langgraph/)** — 对话历史持久化
- **[LM Studio](https://lmstudio.ai/)** — 本地模型推理服务
- **[GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)** — 语音合成（支持跨语言音色克隆）
- **Win32 API** — 原生窗口圆角与边缘 resize

## 配置

### LLM 配置

在 `agent_worker.py` 中修改：

```python
self._llm = ChatOpenAI(
    base_url="http://127.0.0.1:1234/v1",  # 你的 API 地址
    api_key="lm-studio",
    model="google/gemma-4-e4b",            # 你的模型名称
    max_tokens=512,
)
```

### 角色设定

角色设定和回复规则在 `system_prompt.txt` 中修改。

### 语音配置

在 `voice_utils.py` 中配置：

| 配置项 | 说明 |
|---|---|
| `REF_AUDIO_PATH` | 参考音频路径（用于音色克隆） |
| `PROMPT_TEXT` | 参考音频的对应文本 |
| `PROMPT_LANG` | 参考音频语言（`"ja"` / `"zh"`） |
| `GPT_SOVITS_URL` | GPT-SoVITS API 地址（默认 `http://127.0.0.1:9880/tts`） |

### GPT-SoVITS 路径

在 `gpt_sovits_server.py` 中修改：

```python
GPT_SOVITS_DIR = r"C:\GPT-sovit\GPT-SoVITS-v2pro-20250604-nvidia50"
```

## 语音流程

```
语音模式：
用户输入 → Agent 生成中文回复
  → 翻译为日文 → GPT-SoVITS 日文语音合成
  → 语音气泡（朗读日文）+ 中文原文（灰色说明文字）

文本模式：
用户输入 → Agent 生成中文回复 → 逐条气泡显示
```

## 许可

MIT
