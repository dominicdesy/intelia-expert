from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

from app.config.settings import settings
from app.api.v1 import expert, auth, admin, system

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API for Intelia Expert - AI assistant for animal health and nutrition",
    debug=settings.DEBUG
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(expert.router, prefix=settings.API_V1_STR, tags=["expert"])
app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["auth"])
app.include_router(admin.router, prefix=settings.API_V1_STR, tags=["admin"])
app.include_router(system.router, prefix=settings.API_V1_STR, tags=["system"])

@app.get("/", response_class=HTMLResponse)
async def root():
    """API home page."""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Intelia Expert API</title>
        <style>
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                margin: 0; 
                padding: 40px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            .container { 
                max-width: 900px; 
                margin: 0 auto; 
                background: white; 
                padding: 40px; 
                border-radius: 15px; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }
            .logo { 
                color: #059669; 
                font-size: 3em; 
                font-weight: bold; 
                margin-bottom: 10px;
                text-align: center;
            }
            .subtitle {
                text-align: center;
                color: #666;
                font-size: 1.2em;
                margin-bottom: 30px;
            }
            .status { 
                padding: 15px; 
                margin: 20px 0; 
                border-radius: 8px; 
                background: #d1fae5; 
                color: #047857;
                text-align: center;
                font-weight: bold;
            }
            .section {
                margin: 30px 0;
            }
            .section h3 {
                color: #374151;
                border-bottom: 2px solid #e5e7eb;
                padding-bottom: 10px;
            }
            .endpoint-list {
                background: #f9fafb;
                padding: 20px;
                border-radius: 8px;
                margin: 15px 0;
            }
            .endpoint {
                display: flex;
                align-items: center;
                margin: 10px 0;
                padding: 10px;
                background: white;
                border-radius: 5px;
                border-left: 4px solid #059669;
            }
            .method {
                background: #059669;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.8em;
                font-weight: bold;
                margin-right: 15px;
                min-width: 50px;
                text-align: center;
            }
            .method.get { background: #10b981; }
            .method.post { background: #3b82f6; }
            a { 
                color: #059669; 
                text-decoration: none; 
                font-weight: 500;
            }
            a:hover { 
                text-decoration: underline; 
                color: #047857;
            }
            .docs-links {
                display: flex;
                gap: 20px;
                justify-content: center;
                margin: 25px 0;
            }
            .doc-link {
                background: #059669;
                color: white;
                padding: 12px 25px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: bold;
                transition: all 0.3s ease;
            }
            .doc-link:hover {
                background: #047857;
                transform: translateY(-2px);
                color: white;
                text-decoration: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">🐔 Intelia Expert API</div>
            <div class="subtitle">AI assistant for animal health and nutrition</div>
            
            <div class="status">✅ API Active - Version 1.0.0</div>
            
            <div class="section">
                <h3>📚 Documentation</h3>
                <div class="docs-links">
                    <a href="/docs" class="doc-link">Interactive Documentation (Swagger UI)</a>
                    <a href="/redoc" class="doc-link">Alternative Documentation (ReDoc)</a>
                </div>
            </div>
            
            <div class="section">
                <h3>🔗 Main Endpoints</h3>
                <div class="endpoint-list">
                    <div class="endpoint">
                        <span class="method post">POST</span>
                        <div>
                            <strong>/api/v1/expert/ask</strong><br>
                            <small>Ask expert question about broiler management</small>
                        </div>
                    </div>
                    <div class="endpoint">
                        <span class="method post">POST</span>
                        <div>
                            <strong>/api/v1/expert/feedback</strong><br>
                            <small>Submit feedback on responses</small>
                        </div>
                    </div>
                    <div class="endpoint">
                        <span class="method get">GET</span>
                        <div>
                            <strong>/api/v1/expert/topics</strong><br>
                            <small>Get suggested topics and questions</small>
                        </div>
                    </div>
                    <div class="endpoint">
                        <span class="method get">GET</span>
                        <div>
                            <strong>/api/v1/system/health</strong><br>
                            <small>Check system health and configuration</small>
                        </div>
                    </div>
                    <div class="endpoint">
                        <span class="method get">GET</span>
                        <div>
                            <strong>/api/v1/admin/dashboard</strong><br>
                            <small>Admin dashboard and metrics</small>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h3>🧪 Quick Test</h3>
                <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; font-family: monospace;">
                    <strong>curl -X POST "http://localhost:8000/api/v1/expert/ask"</strong><br>
                    &nbsp;&nbsp;&nbsp;&nbsp;<strong>-H "Content-Type: application/json"</strong><br>
                    &nbsp;&nbsp;&nbsp;&nbsp;<strong>-d '{"question": "Optimal temperature for Ross 308?", "language": "en"}'</strong>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.get("/health")
async def health_check():
    """Enhanced health check with detailed status."""
    try:
        from app.services.expert_service import expert_service
        
        # Get detailed status from expert service
        service_status = expert_service.get_status()
        
        return {
            "status": "healthy",
            "version": settings.VERSION,
            "timestamp": expert_service._get_timestamp(),
            "services": {
                "api": "running",
                "openai": "configured" if service_status["openai_configured"] else "not_configured",
                "secrets": "loaded" if service_status["secrets_loaded"] else "not_loaded",
                "rag": "available" if service_status["rag_available"] else "not_available"
            },
            "configuration": {
                "openai_configured": service_status["openai_configured"],
                "secrets_loaded": service_status["secrets_loaded"],
                "method": service_status["method"]
            }
        }
    except Exception as e:
        return {
            "status": "degraded",
            "version": settings.VERSION,
            "error": str(e),
            "services": {
                "api": "running",
                "openai": "unknown",
                "secrets": "unknown",
                "rag": "unknown"
            }
        }

@app.get("/status")
async def detailed_status():
    """Detailed system status."""
    try:
        from app.services.expert_service import expert_service
        
        return {
            "api_version": settings.VERSION,
            "status": "operational",
            "expert_service": expert_service.get_status(),
            "endpoints": {
                "expert_ask": "/api/v1/expert/ask",
                "expert_topics": "/api/v1/expert/topics", 
                "expert_feedback": "/api/v1/expert/feedback",
                "system_health": "/api/v1/system/health",
                "admin_dashboard": "/api/v1/admin/dashboard"
            },
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc"
            }
        }
    except Exception as e:
        return {
            "api_version": settings.VERSION,
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)