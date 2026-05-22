import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain.agents import create_agent


connection = sqlite3.connect("resources/checkpoint.db",check_same_thread=False)

checkpoint = SqliteSaver(connection)

checkpoint.setup()

from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="lm-studio",
    model="google/gemma-4-e4b",
    

)


agent = create_agent(
    model=llm,
    checkpointer=checkpoint,
    system_prompt = "你叫千早爱音，是一名女高中生，你加入了一个少女乐队。"
)

from langchain.messages import HumanMessage

config = {"configurable":{"thread_id":"thread_10"}}

res = agent.invoke(
    {"messages":[HumanMessage(content="我喜欢摇滚音乐")]},
    config #调用时添加thread_id
)

print(res)

res = agent.invoke(
    {"messages":[HumanMessage(content="我喜欢什么音乐？")]},
    config #调用时添加thread_id
)

print(res)