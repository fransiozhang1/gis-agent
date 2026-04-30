import os
import json
import pandas as pd
import geopandas as gpd
from typing import Annotated, TypedDict, Union
from dotenv import load_dotenv

# LangGraph 相关
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# 加载环境变量
load_dotenv()

# --- 1. 定义状态 (State) ---
class AgentState(TypedDict):
    # 聊天记录，add_messages 会自动追加对话
    messages: Annotated[list, add_messages]
    # 上传的 JSON 文件路径
    file_path: str
    # 提取出的 JSON 字段信息
    schema_info: str
    # 当前生成的代码
    generated_code: str
    # 迭代次数，防止无限死循环
    retry_count: int

# --- 2. 初始化 DeepSeek 模型 ---
llm = ChatOpenAI(
    model='deepseek-coder', 
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_API_BASE"),
    temperature=0.1
)

# --- 3. 定义节点 (Nodes) ---

def analyzer_node(state: AgentState):
    """读取 JSON 文件并提取 Schema 信息"""
    path = state["file_path"]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 如果是列表，取第一项看结构；如果是字典，看键值
            sample = data[0] if isinstance(data, list) else data
            schema = f"数据字段包含: {list(sample.keys())}"
    except Exception as e:
        schema = f"无法解析文件结构: {str(e)}"
    
    return {"schema_info": schema, "retry_count": 0}

def coder_node(state: AgentState):
    """根据需求和 Schema 生成 Python 代码"""
    
    # 构建系统提示词，强制要求极简技术美学
    system_prompt = f"""你是一个 GIS 数据分析专家。
    已知地理数据路径: {state['file_path']}
    数据结构: {state['schema_info']}

    任务：编写一段 Python 代码进行数据处理。
    【强制要求】：
    1. 使用 pandas 或 geopandas 读取数据。
    2. 必须创建一个名为 'result_layer' 的 pydeck Layer 对象（例如 pdk.Layer(...)）。
    3. 视觉风格：极简技术线条美学，推荐使用单色系（如黑白灰或深蓝色调）。
    4. 仅仅输出代码，不要包含 ```python ``` 这样的 Markdown 标识符，不要有任何解释说明。
    5. 如果上一次尝试报错了，请根据错误信息进行修复。
    """
    
    response = llm.invoke([SystemMessage(content=system_prompt)] + state["messages"])
    return {"generated_code": response.content, "messages": [response]}

def executor_node(state: AgentState):
    """执行生成的代码，验证其正确性"""
    code = state["generated_code"]
    file_path = state["file_path"]
    
    # 准备执行环境
    exec_globals = {
        "pd": pd,
        "gpd": gpd,
        "pdk": __import__("pydeck"),
        "file_path": file_path,
        "result_layer": None
    }
    
    try:
        # 尝试执行
        exec(code, exec_globals)
        # 如果成功运行且产生了 result_layer
        if exec_globals.get("result_layer") is not None:
            return {"messages": [HumanMessage(content="SUCCESS: 代码运行成功。")]}
        else:
            return {"messages": [HumanMessage(content="ERROR: 代码运行成功但未定义 result_layer。")], "retry_count": state["retry_count"] + 1}
    except Exception as e:
        # 如果报错，记录错误信息返回给模型
        error_msg = f"ERROR: 代码运行失败。错误信息: {str(e)}"
        return {"messages": [HumanMessage(content=error_msg)], "retry_count": state["retry_count"] + 1}

# --- 4. 定义路由逻辑 (Conditional Edges) ---

def should_continue(state: AgentState):
    """判断是继续修复代码还是结束工作"""
    last_message = state["messages"][-1].content
    
    if "SUCCESS" in last_message:
        return END
    if state["retry_count"] > 3: # 最多尝试 3 次
        return END
    return "coder"

# --- 5. 构建图 (The Graph) ---

workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("analyzer", analyzer_node)
workflow.add_node("coder", coder_node)
workflow.add_node("executor", executor_node)

# 设置逻辑连线
workflow.add_edge(START, "analyzer")
workflow.add_edge("analyzer", "coder")
workflow.add_edge("coder", "executor")

# 条件分支：执行结果成功则结束，失败则回到 coder 重新修复
workflow.add_conditional_edges(
    "executor",
    should_continue,
    {
        "coder": "coder",
        END: END
    }
)

# 编译应用
agent_app = workflow.compile()