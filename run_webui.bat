@echo off
rem 设置端口号 (你可以修改下面的数字来更换端口)
set PORT=8501

echo Installing requirements...
pip install -r requirements.txt
echo Starting WebUI on port %PORT%...
streamlit run dataset_tool_webui.py --server.port %PORT%
pause
