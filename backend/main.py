# Fichier minimal pour que DigitalOcean détecte Python
from fastapi import FastAPI

app = FastAPI(title="Intelia Expert API")

@app.get("/")
def read_root():
    return {"message": "Intelia Expert API - En développement"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
