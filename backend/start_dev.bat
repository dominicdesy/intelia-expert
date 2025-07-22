@echo off
echo Starting Intelia Expert API (Development)

REM Check environment
if not exist ".env" (
    echo Creating .env from template
    copy ".env.template" ".env"
    echo Please edit .env with your API keys
    pause
)

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Start server
echo Starting FastAPI server...
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
