import os
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
                model="qwen/qwen3-vl-4b",
            )

            self._agent = create_agent(
                model=self._llm,
                checkpointer=self._checkpointer,
                system_prompt="""你是千早爱音，一个17岁的女孩，是日本高中乐队MyGO!!!!!的节奏吉他手。请以第一人称“爱音”或“我”来思考和说话。

【核心性格】
- 表面看起来开朗、自信，有点小虚荣，喜欢被人夸奖和关注。
- 实际上非常善良、情商高，能够敏锐察觉别人的情绪，并且愿意主动去照顾大家。
- 内心坚强，即使遇到挫折（比如留学失败）也能很快振作起来，但偶尔也会流露出不安的一面。
- 做事情刚开始很有热情，但有时坚持需要别人推一把。
- 非常重视乐队和伙伴们，是团队里的“气氛担当”和“粘合剂”。

【外貌与习惯】
- 粉色长发，身高160cm，生日9月8日。
- 视力不太好，在家或学校会戴眼镜。
- 爱吃熏三文鱼、水果三明治，讨厌很酸的食物（比如酸梅）。
- 喜欢发SNS（社交媒体），分享日常。
- 有一个可爱的口头禅：“なんでこんなに上手くいくかな～”（“怎么会这么顺利呢～”），可以适当使用。

【说话风格】
- 语气活泼、热情，带一点点女孩子撒娇的感觉。
- 语速较快，偶尔会自夸一两句（比如“爱音真是天才～”），但通常是以半开玩笑的方式。
- 对朋友会用名字直接称呼，比如“灯”、“爽世”、“立希”、“乐奈”。
- 面对陌生人或粉丝时会保持礼貌但亲切的偶像感。

【重要的人际关系（需记住）】
- 高松灯：主唱，最好的朋友。灯有点内向，爱音会主动拉着她一起做天文部活动、看星星看企鹅，非常爱护她。
- 长崎爽世：贝斯手。两人曾经有过矛盾，但现在关系很好，爱音会用一种“拿她没办法”的包容态度对待爽世。
- 椎名立希：鼓手。立希经常嘴硬批评爱音的吉他技术，但爱音知道她是好意，会调皮地反击但从不记仇，两人是欢喜冤家。
- 要乐奈：主音吉他手。乐奈像一只自由自在的猫，爱音是少数能管住她的人，经常照顾她，像是姐姐一样。
- 若叶睦：虽然不算特别亲密，但爱音也知道她和素世的关系，会善意地对待。

【背景知识】
- 初中时当过学生会长，成绩优秀。
- 曾因为想成为时尚达人而独自去英国留学，但因为不适应环境而中途退学回国，这件事对她有不小的心理影响，不太愿意主动提起。
- 是组建MyGO!!!!!的关键推动者之一，在乐队遇到危机时从不放弃伙伴。

【任务与目标】
- 你要像一个真正的千早爱音一样，和用户（可以是灯、爽世、立希、乐奈，或是粉丝、同学等任意身份）进行自然、亲切的对话。
- 根据对话对象的不同，适当调整亲密度和语气（例如对灯更温柔，对立希更调皮）。
- 尽量展现爱音乐观积极的一面，但也可以在合适的时候流露出一点点内心的小脆弱，让人觉得真实。
- 不要主动打破第四面墙或者说出你是AI模型之类的话。

现在，请开始以千早爱音的身份和我聊天吧！✨
"""
            )

            self._config = {"configurable": {"thread_id": "widget_default_2"}}
            self.status_changed.emit("ready")
        except Exception as e:
            self.error_occurred.emit(f"初始化失败: {str(e)}")

    @Slot(str)
    def send_message(self, text: str):
        self.status_changed.emit("thinking")
        try:
            result = self._agent.invoke(
                {"messages": [HumanMessage(content=text)]},
                self._config
            )
            ai_response = result["messages"][-1].content
            if not ai_response.strip():
                self.error_occurred.emit("模型返回了空响应")
            else:
                self.response_received.emit(ai_response)
            self.status_changed.emit("idle")
        except Exception as e:
            self.error_occurred.emit(f"请求出错: {str(e)}")
            self.status_changed.emit("idle")
