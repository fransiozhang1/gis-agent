import gradio as gr
import pydeck as pdk
import os
import pandas as pd
from agent import agent_app # 确保你仓库里还有那个 agent.py

def run_agent(json_file, query):
    if json_file is None: return "请先上传文件", None
    
    # 1. 运行 Agent 逻辑
    inputs = {"messages": [("user", query)], "file_path": json_file.name}
    result = agent_app.invoke(inputs)
    
    # 2. 提取代码并生成地图 (这里假设 Agent 返回了符合要求的 pydeck 代码)
    generated_code = result["generated_code"]
    
    # 3. 渲染地图（简化逻辑：直接显示生成的代码，并尝试生成一个基础底图）
    # 既然你追求极简美学，我们默认使用 Mapbox 的 Dark 样式
    view_state = pdk.ViewState(latitude=31.23, longitude=121.47, zoom=10, pitch=45)
    deck = pdk.Deck(map_style='mapbox://styles/mapbox/dark-v10', initial_view_state=view_state)
    
    return generated_code, deck.to_html(as_string=True)

# 构造极简黑白界面
with gr.Blocks(theme=gr.themes.Soft(primary_hue="slate")) as demo:
    gr.Markdown("# 🏙️ URBAN_INTELLIGENCE_AGENT // CUD")
    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(label="Upload GeoJSON")
            query_input = gr.Textbox(label="Prompt Logic", placeholder="输入你的空间可视化逻辑...")
            run_btn = gr.Button("EXECUTE_LOGIC", variant="primary")
        with gr.Column(scale=2):
            code_output = gr.Code(label="Generated Python Code", language="python")
            map_output = gr.HTML(label="Spatial Visualization")

    run_btn.click(run_agent, [file_input, query_input], [code_output, map_output])

demo.launch()