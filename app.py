import streamlit as st
import pydeck as pdk
import os
import pandas as pd
import geopandas as gpd
from agent import agent_app

st.set_page_config(page_title="CityData AI Agent", layout="wide")

# 注入一点极简主义风格的 CSS
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏙️ 城市地理数据智能分析平台")
st.caption("基于 DeepSeek-Coder + LangGraph 的极简主义 GIS 助手")

# 侧边栏
with st.sidebar:
    st.header("数据上传")
    uploaded_file = st.file_uploader("上传 JSON 地理数据", type=['json'])
    
    if uploaded_file:
        # 确保 data 目录存在
        if not os.path.exists("data"):
            os.makedirs("data")
            
        file_path = os.path.join("data", uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"文件 {uploaded_file.name} 已加载")

# 主交互区
user_query = st.text_area("描述你的分析与可视化需求：", 
                         placeholder="例如：将数据中的 POI 按照热力图展示，使用黑白配色，并过滤掉价值为 0 的点。")

if st.button("生成可视化"):
    if not uploaded_file:
        st.error("请先上传一个 JSON 文件！")
    else:
        with st.spinner("Agent 正在思考、编写代码并调试..."):
            # 运行 LangGraph 工作流
            inputs = {
                "messages": [("user", user_query)],
                "file_path": file_path
            }
            # 获取最终结果
            result = agent_app.invoke(inputs)
            
            # 提取最后生成的代码
            final_code = result["generated_code"]
            
            # 展示生成的代码（可选，为了透明度）
            with st.expander("查看生成的 Python 代码"):
                st.code(final_code, language="python")
            
            # 执行代码以获取 result_layer
            exec_globals = {
                "pd": pd, "gpd": gpd, "pdk": pdk,
                "file_path": file_path, "result_layer": None
            }
            try:
                exec(final_code, {}, exec_globals)
                final_layer = exec_globals.get("result_layer")
                
                if final_layer:
                    # 渲染地图
                    # 自动根据数据定位初始视角（假设数据里有经纬度）
                    st.pydeck_chart(pdk.Deck(
                        map_style='mapbox://styles/mapbox/light-v10',
                        initial_view_state=pdk.ViewState(
                            latitude=31.23, # 默认上海，也可以让 Agent 计算中心点
                            longitude=121.47,
                            zoom=11,
                            pitch=45
                        ),
                        layers=[final_layer]
                    ))
                    st.success("可视化渲染完成！")
                else:
                    st.error("代码运行成功但未产生图层对象。")
            except Exception as e:
                st.error(f"渲染失败: {str(e)}")