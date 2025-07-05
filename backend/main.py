# Intelia Expert API - Version minimale pour setup infrastructure
from fastapi import FastAPI

app = FastAPI(
    title="Intelia Expert API",
    description="Assistant IA spécialisé en santé et nutrition animale",
    version="0.1.0"
)

@app.get("/")
def read_root():
    return {
        "message": "Intelia Expert API",
        "status": "En développement - Phase 1",
        "version": "0.1.0"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "backend"}

@app.get("/api/v1/system/health")
def system_health():
    return {
        "status": "ok",
        "service": "intelia-expert-api",
        "environment": "development"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
