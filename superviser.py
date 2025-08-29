
import streamlit as st
import uuid
import asyncio
import os
import json

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch

# --- LangGraph sub function ---
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
# --- LangGraph sub function ---

# --- ローカルツール ---
import datetime
from langchain_core.tools import tool
# --- ローカルツール ---

# MCPサーバーを利用するためのインポート
from langchain_mcp_adapters.client import MultiServerMCPClient


load_dotenv()

# --- 記憶 ---
from langgraph.store.memory import InMemoryStore
from langgraph.store.postgres import PostgresStore
from langmem import create_manage_memory_tool, create_search_memory_tool

def create_conn_url():
    username = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    dbname = os.getenv("POSTGRES_DB")
    return f"postgresql://{username}:{password}@{host}:{port}/{dbname}"
# --- 記憶 ---

# --- langfuse ---
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

langfuse = Langfuse()
langfuse_handler = CallbackHandler()
# --- langfuse ---


llm = ChatOpenAI(temperature=0, model="gpt-4.1-mini")

# Initialize Tavily Search Tool
tavily_search_tool = TavilySearch(
    max_results=5,
    topic="general",
)

postgres_conn_url = create_conn_url()
store_cm = PostgresStore.from_conn_string(
    postgres_conn_url,
    index={
        "dims": 1536,
        "embed": "openai:text-embedding-3-small",
    }
)

db_store = store_cm.__enter__()
db_store.setup()

memory_store = InMemoryStore(
    index={
        "dims": 1536,
        "embed": "openai:text-embedding-3-small",
    }
)


# -----------------
# エージェントの定義
# -----------------

# Search Planner エージェント
search_planner = create_react_agent(
    llm,
    tools=[],
    name="search_planner",
    prompt="あなたのタスクは与えられたテーマに関するレポートを書くためにどのように情報をWeb検索を使って収集をしたらよいか、計画を立てることです。様々な観点でWeb検索を使って情報を収集するための計画をステップバイステップで考えてください。"
)

# Web Searcher エージェント
web_searcher = create_react_agent(
    llm,
    tools=[tavily_search_tool],
    name="web_searcher",
    prompt="あなたのタスクはクエリとして与えられた情報をWeb検索を使って収集することです。"
)

# Report Writer エージェント
report_writer = create_react_agent(
    llm,
    tools=[],
    name="report_writer",
    prompt="あなたは与えられた情報を参照し、それをレポートにまとめる役割を持っています。レポートにはアブストラクト/これまでの前提情報/現在の情報/今後の発展を含めてください。"
)


# ------
# ローカルツールの定義
# ------
@tool
async def get_current_time() -> dict[str, str]:
    """現在時刻（ISO 8601形式の文字列）を返すTool.

    Returns:
        dict[str, str]:
            - "current_time": 現在時刻（例: "2025-05-19T12:34:56.789123"）
    """
    now = datetime.datetime.now().isoformat()
    return {"current_time": now}


# -----------------
# supervisorの定義
# -----------------
def choose_supervisor(mode: str = "base", memory: str = "short", mcp_tools: list = None):

    supervisor_prompt_base = """
    あなたは以下のAgent達の管理を担当しています。ユーザーのクエリをAgentにタスクを与えることで解決してください。

    1. search_planner: 与えられたテーマに関するレポートを書くためにどのように情報をWeb検索を使って収集をしたらよいか、計画を立てる。
    2. web_searcher: Bing検索を使って情報を検索する
    3. report_writer: これまでに検索した情報をレポートにまとめ、出力する

    タスクをAgentに与えてください。複数のAgentを並行して呼び出してはいけません。
    最後にユーザーのクエリに対する回答を出力してください。ただし、あなた自身がいかなるタスクをこなしてはいけません。
    """

    if mode == "base":
        print("supervisor mode: base")
        supervisor = create_supervisor(
            agents=[search_planner, web_searcher, report_writer],
            model=llm,
            prompt=supervisor_prompt_base,
            output_mode="full_history"
        ).compile()

    elif mode == "tools":
        print("supervisor mode: tools")
        supervisor = create_supervisor(
            agents=[search_planner, web_searcher, report_writer],
            model=llm,
            tools=[get_current_time,],
            prompt=supervisor_prompt_base,
            output_mode="full_history"
        ).compile()

    elif mode == "mcp":
        print("supervisor mode: mcp")
        supervisor = create_supervisor(
            agents=[search_planner, web_searcher, report_writer],
            model=llm,
            tools=mcp_tools,
            prompt=supervisor_prompt_base,
            output_mode="full_history"
        ).compile()

    elif mode == "memory":
        namespace = ("memories", "user_name")
        mcp_tools.append(create_manage_memory_tool(namespace=namespace))
        mcp_tools.append(create_search_memory_tool(namespace=namespace))

        if memory == "short":
            print("supervisor mode: memory (short)")
            supervisor = create_supervisor(
                agents=[search_planner, web_searcher, report_writer],
                model=llm,
                tools=mcp_tools,
                prompt=supervisor_prompt_base,
                output_mode="full_history"
            ).compile(store=memory_store)

        else:
            print("supervisor mode: memory (long)")
            supervisor = create_supervisor(
                agents=[search_planner, web_searcher, report_writer],
                model=llm,
                tools=mcp_tools,
                prompt=supervisor_prompt_base,
                output_mode="full_history"
            ).compile(store=db_store)

    return supervisor


async def main():

    with open("mcp_config.json", "r") as f:
        config = json.load(f)

    client = MultiServerMCPClient(config["mcpServers"])

    mcp_tools = await client.get_tools()
    print(mcp_tools)

    # エージェントの実行
    config = {'configurable': {'thread_id': str(uuid.uuid4())},
            'recursion_limit': 50}

    # ------
    # supervisorの選択　ここで切り替える
    # ------
    mode = "base"
    mode = "tools"
    mode = "mcp"
    mode = "memory"
    memory = "short"
    memory = "long"

    supervisor = choose_supervisor(mode=mode, memory=memory, mcp_tools=mcp_tools)

    # タイトルの設定
    st.title("Agent Chat App" + " - " + mode + " - " + memory)

    # メッセージの初期化
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # メッセージの表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if "tools" in message:
                with st.expander("tool use proccess"):
                    for tool_output in message["tools"]:
                        st.markdown(tool_output)
            st.markdown(message["content"])

    # チャットボットとの対話
    if prompt := st.chat_input("What is up?"):
        # ユーザーのメッセージを表示
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # チャットボットの応答
        with st.chat_message("assistant"):

            expander = st.expander("tool use proccess")
            message_placeholder = st.empty()
            contents = ""
            tool_outputs = []

            async for event in supervisor.astream_events({"messages": st.session_state.messages}, config=config, stream_mode="values"):
                # メッセージの表示
                if event["event"] == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        contents += content
                        message_placeholder.markdown(contents)
                # ツール利用の開始
                elif event["event"] == "on_tool_start":
                    tmp = f"#### Start using the tool ： {event['name']}  \nInputs: {event['data'].get('input')}"
                    tool_outputs.append(tmp)
                    expander.markdown(tmp)
                # ツール利用の終了
                elif event["event"] == "on_tool_end":
                    tmp = f"#### Finish using the tool ： {event['name']}  \nOutput ： {event['data'].get('output')}"
                    tool_outputs.append(tmp)
                    expander.markdown(tmp)

            st.session_state.messages.append({"role": "assistant", "content": contents, "tools": tool_outputs})


if __name__ == "__main__":
    asyncio.run(main())

# 動作確認用シナリオ1
# base shortで起動する
# LangGraphについて教えてください

# 動作確認用シナリオ2
# base shortで起動する
# 本日の11時から30分以内に出たニュースの内容をまとめて表示してください
# 時刻が分から検索することを確認
# tools, shortで起動する
# 今から30分以内に出たニュースの内容をまとめて表示してください
# 時刻を取得していることを確認

# 動作確認用シナリオ4
# mcp short で起動する
# 私は田中です、4月1日に生まれました。今日の日付を教えてください。また、私の誕生日まであと何日かも教えてください。
# 私の名前と誕生日を覚えていますか？
# 覚えていないことを確認する
# memory short で起動する
# 私は田中です、4月1日に生まれました。今日の日付を教えてください。また、私の誕生日まであと何日かも教えてください。
# 私の名前と誕生日を覚えていますか？
# 覚えていることを確認する

# 動作確認用シナリオ5
# memory short で起動する
# 私は田中です、4月1日に生まれました。今日の日付を教えてください。また、私の誕生日まであと何日かも教えてください。
# 私の名前と誕生日を覚えていますか？
# 覚えていることを確認する
# プロセスダウン
# memory short で起動する
# 私の名前と誕生日を覚えていますか？
# 覚えていないことと確認する

# 動作確認用シナリオ6
# memory long で起動する
# 私は田中です、4月1日に生まれました。今日の日付を教えてください。また、私の誕生日まであと何日かも教えてください。
# 私の名前と誕生日を覚えていますか？
# 覚えていることを確認する
# プロセスダウン
# memory long で起動する
# 私の名前と誕生日を覚えていますか？
# 覚えていることを確認する
