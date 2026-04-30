import pandas as pd
import geopandas as gpd
from langchain_core.tools import tool

@tool
def code_executor(code: str, file_path: str):
    """
    执行 Python 代码来处理地理 JSON 数据。
    输入: code (模型生成的代码), file_path (数据路径)。
    输出: 必须返回一个包含 pydeck 图层对象的变量。
    """
    # 定义执行环境，注入必要的库
    local_vars = {
        "pd": pd,
        "gpd": gpd,
        "file_path": file_path,
        "result_layer": None
    }
    
    try:
        # 在沙盒环境中执行生成的代码
        exec(code, {}, local_vars)
        return local_vars.get("result_layer")
    except Exception as e:
        return f"代码执行出错: {str(e)}"