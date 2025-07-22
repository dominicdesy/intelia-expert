# Intelia Expert API

## Quick Start

1. Configure environment:
   `
   cd backend
   copy .env.template .env
   # Edit .env with your OpenAI API key
   `

2. Install dependencies:
   `
   pip install -r requirements.txt
   `

3. Start API:
   `
   python -m uvicorn app.main:app --reload
   `

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

## Main Endpoints

- POST /api/v1/expert/ask - Ask expert question
- GET /api/v1/expert/topics - Get suggested topics
- GET /api/v1/system/health - System health

## Quick Test

`ash
curl -X POST "http://localhost:8000/api/v1/expert/ask" \
     -H "Content-Type: application/json" \
     -d '{"question": "Optimal temperature for Ross 308?", "language": "en"}'
`
