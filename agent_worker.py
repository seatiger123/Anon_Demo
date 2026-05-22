import os
import re
import sqlite3

from PySide6.QtCore import QObject, Signal, Slot

from langgraph.checkpoint.sqlite import SqliteSaver
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage


class AgentWorker(QObject):
    response_received = Signal(str)
    error_occurred = Signal(str)
    status_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._llm = None
        self._checkpointer = None
        self._agent = None
        self._config = None

    @Slot()
    def initialize(self):
        self.status_changed.emit("initializing")
        try:
            db_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "resources"
            )
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "checkpoint.db")

            connection = sqlite3.connect(db_path, check_same_thread=False)
            self._checkpointer = SqliteSaver(connection)
            self._checkpointer.setup()

            self._llm = ChatOpenAI(
                base_url="http://127.0.0.1:1234/v1",
                api_key="lm-studio",
                model="google/gemma-4-e4b",
                max_tokens=512,
            )

            prompt_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "system_prompt.txt"
            )
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()

            self._agent = create_agent(
                model=self._llm,
                checkpointer=self._checkpointer,
                system_prompt=system_prompt,
            )

            self._config = {"configurable": {"thread_id": "widget_default_9"}}
            self.status_changed.emit("ready")
        except Exception as e:
            self.error_occurred.emit(f"初始化失败: {str(e)}")

    @Slot(str)
    def send_message(self, text: str):
        self.status_changed.emit("thinking")
        try:
            for attempt in range(3):
                result = self._agent.invoke(
                    {"messages": [HumanMessage(content=text)]},
                    self._config
                )
                ai_response = result["messages"][-1].content
                stripped = re.sub(r'[（(][^）)]*[）)]', '', ai_response).strip()
                ai_response = stripped if stripped else ai_response
                if ai_response.strip():
                    self.response_received.emit(ai_response)
                    break

                # 诊断日志：打印完整的 messages 结构
                print(f"[Agent Debug] Attempt {attempt + 1}: empty response")
                print(f"[Agent Debug] messages count: {len(result['messages'])}")
                for i, m in enumerate(result["messages"]):
                    print(f"  [{i}] type={type(m).__name__} content={repr(m.content)[:120]}")
                    if hasattr(m, "tool_calls") and m.tool_calls:
                        print(f"       tool_calls={m.tool_calls}")
                last = result["messages"][-1]
                print(f"[Agent Debug] last msg full repr: {repr(last)}")

                if attempt < 2:
                    # 清空本轮失败 checkpoint，以干净状态重试
                    tid = self._config["configurable"]["thread_id"]
                    self._checkpointer.delete_thread(tid)
                    print(f"[Agent Debug] Deleted thread {tid!r}, retrying...")
                else:
                    self.error_occurred.emit("模型返回了空响应")
            self.status_changed.emit("idle")
        except Exception as e:
            self.error_occurred.emit(f"请求出错: {str(e)}")
            self.status_changed.emit("idle")
