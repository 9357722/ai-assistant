@echo off
cd /d D:\python\AI_Projects
call ai_env\Scripts\activate
uvicorn api_server:app --reload
pause