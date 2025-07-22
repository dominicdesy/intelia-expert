@echo off
echo Starting Intelia Expert API
echo ==========================

cd backend

if not exist ".env" (
    echo Missing .env file, creating from template...
    copy .env.template .env
    echo .env file created - configure your API keys
    pause
)

echo Installing dependencies...
pip install -r requirements.txt

echo Starting server...
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
