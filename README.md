# 千早爱音 AI Chatbot 🎸

一个基于本地大语言模型的桌面 AI 聊天助手，角色为《BanG Dream! It's MyGO!!!!!》中的 **千早爱音**。

## 功能

- **悬浮头像** — 桌面右下角的圆形头像，鼠标悬停放大，可拖拽移动
- **个性聊天** — 爱音角色扮演，符合原作性格与语气，简短活泼的回复风格
- **原生窗口** — 无边框圆角聊天窗口，支持 Win32 原生边缘拖拽调整大小
- **逐条显示** — AI 回复按句子拆分，模拟真人打字节奏
- **深色模式** — 支持一键切换亮色/深色主题
- **入场语音** — AI 就绪后自动播放入场音效
- **对话记忆** — 基于 LangGraph 的 SQLite 检查点，保留多轮对话上下文
- **离线运行** — 完全本地推理，无需联网

## 环境要求

- Python 3.10+
- [LM Studio](https://lmstudio.ai/) 或任何兼容 OpenAI API 的本地推理服务

## 安装

```bash
# 克隆仓库
git clone https://github.com/seatiger123/Anon_Demo.git
cd Anon_Demo

# 安装依赖
pip install PySide6 langchain langchain-openai langgraph langgraph-checkpoint-sqlite
```

## 使用

1. 启动 LM Studio，加载模型（推荐 `google/gemma-4-e4b`），开启本地服务器（默认 `http://127.0.0.1:1234`）
2. 运行程序：

```bash
python main.py
```

3. 点击桌面的粉色圆形头像打开聊天窗口，开始与爱音对话

## 项目结构

```
Anon_Demo/
├── main.py                 # 入口：创建窗口、管理线程
├── agent_worker.py         # AI 工作线程：LangChain Agent + LLM 调用
├── agent_MAIN.py           # 简单的 Agent 测试脚本
├── system_prompt.txt       # 角色设定提示词（爱音的人设与回复规则）
├── ui/
│   ├── chat_window.py      # 聊天窗口 UI（气泡消息、主题切换、Win32 原生窗口）
│   └── floating_widget.py  # 桌面悬浮头像（拖拽、悬停动画、右键菜单）
└── resources/
    ├── icon.png            # 悬浮头像图标
    ├── entrance_voice.wav  # 入场语音
    └── checkpoint.db       # 对话记忆数据库（自动生成）
```

## 技术栈

- **[PySide6](https://pypi.org/project/PySide6/)** — Qt for Python 桌面 UI
- **[LangChain](https://www.langchain.com/)** / **[LangGraph](https://langchain-ai.github.io/langgraph/)** — AI Agent 框架与对话状态管理
- **[LangGraph Checkpoint (SQLite)](https://langchain-ai.github.io/langgraph/)** — 对话历史持久化
- **[LM Studio](https://lmstudio.ai/)** — 本地模型推理服务
- **Win32 API** — 原生窗口圆角与边缘 resize

## 配置

如需更换模型或修改 API 地址，编辑 `agent_worker.py`：

```python
self._llm = ChatOpenAI(
    base_url="http://127.0.0.1:1234/v1",  # 你的 API 地址
    api_key="lm-studio",
    model="google/gemma-4-e4b",            # 你的模型名称
    max_tokens=512,
)
```

角色设定和回复规则在 `system_prompt.txt` 中修改。

## 许可

MIT
