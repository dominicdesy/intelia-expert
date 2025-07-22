#!/bin/bash

# Intelia Expert API - Quick Deployment Script
# Run this script to deploy your API to DigitalOcean

set -e

echo "🚀 INTELIA EXPERT API - QUICK DEPLOYMENT"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if required tools are installed
check_requirements() {
    echo -e "${BLUE}📋 Checking requirements...${NC}"
    
    if ! command -v git &> /dev/null; then
        echo -e "${RED}❌ Git is required but not installed${NC}"
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        echo -e "${YELLOW}⚠️ Docker not found - will use GitHub Actions for build${NC}"
    fi
    
    echo -e "${GREEN}✅ Requirements check complete${NC}"
}

# Setup GitHub repository
setup_github() {
    echo -e "${BLUE}📂 Setting up GitHub repository...${NC}"
    
    # Create .github/workflows directory
    mkdir -p .github/workflows
    
    # Check if we're in a git repository
    if [ ! -d ".git" ]; then
        echo -e "${YELLOW}⚠️ Not a git repository. Initializing...${NC}"
        git init
        git add .
        git commit -m "Initial commit: Intelia Expert API"
    fi
    
    echo -e "${GREEN}✅ GitHub setup complete${NC}"
}

# Create deployment files
create_deployment_files() {
    echo -e "${BLUE}📝 Creating deployment files...${NC}"
    
    # Create .dockerignore
    cat > .dockerignore << 'EOF'
.git
.github
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
pip-log.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.DS_Store
README.md
.gitignore
.dockerignore
EOF
    
    # Create production requirements
    cat > backend/requirements.prod.txt << 'EOF'
# Production requirements for Intelia Expert API
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
pydantic==2.5.0
python-dotenv==1.0.0
httpx==0.25.2
aiofiles==23.2.1
toml>=0.10.2
openai>=1.0.0
sentence-transformers>=2.2.0
faiss-cpu>=1.7.0
streamlit>=1.28.0
pandas>=2.0.0
numpy>=1.24.0
python-dateutil>=2.8.0
gunicorn==21.2.0
EOF
    
    echo -e "${GREEN}✅ Deployment files created${NC}"
}

# Instructions for DigitalOcean setup
show_digitalocean_instructions() {
    echo -e "${BLUE}🌊 DigitalOcean Setup Instructions${NC}"
    echo "=================================="
    echo ""
    echo "1. Go to: https://cloud.digitalocean.com/apps"
    echo "2. Click 'Create App'"
    echo "3. Choose 'GitHub' as source"
    echo "4. Select your repository: 'intelia-expert'"
    echo "5. Choose branch: 'main'"
    echo "6. App configuration:"
    echo "   - App name: intelia-expert-api"
    echo "   - Region: New York (NYC1)"
    echo "   - Plan: Basic ($12/month)"
    echo ""
    echo "7. Environment Variables (REQUIRED):"
    echo "   - OPENAI_API_KEY=your-openai-key"
    echo "   - SECRET_KEY=your-secret-key"
    echo "   - PORT=8000"
    echo "   - RAG_ENABLED=true"
    echo ""
    echo "8. GitHub Secrets (for CI/CD):"
    echo "   Go to: GitHub Settings > Secrets and variables > Actions"
    echo "   Add:"
    echo "   - DIGITALOCEAN_ACCESS_TOKEN"
    echo "   - OPENAI_API_KEY"
    echo ""
}

# Main deployment function
main() {
    echo -e "${GREEN}Starting Intelia Expert API deployment...${NC}"
    echo ""
    
    check_requirements
    setup_github
    create_deployment_files
    
    echo ""
    echo -e "${GREEN}✅ LOCAL SETUP COMPLETE!${NC}"
    echo ""
    
    show_digitalocean_instructions
    
    echo ""
    echo -e "${YELLOW}📋 Next Steps:${NC}"
    echo "1. Push your code to GitHub:"
    echo "   git add ."
    echo "   git commit -m 'feat: Add deployment configuration'"
    echo "   git push origin main"
    echo ""
    echo "2. Follow the DigitalOcean instructions above"
    echo ""
    echo "3. Your API will be live at:"
    echo "   https://intelia-expert-api-{random}.ondigitalocean.app"
    echo ""
    echo -e "${GREEN}🚀 Happy deploying!${NC}"
}

# Run main function
main "$@"