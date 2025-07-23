"""
Root main.py for DigitalOcean buildpack detection
Delegates to the actual backend application
"""
import sys
import os

# Add backend to Python path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

# Import and expose the actual FastAPI app
try:
    from app.main import app
    
    # Export app for uvicorn
    __all__ = ['app']
    
except ImportError as e:
    print(f"Error importing backend app: {e}")
    print("Make sure backend/app/main.py exists and is valid")
    raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
