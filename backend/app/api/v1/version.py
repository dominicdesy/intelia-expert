"""
Version API - Return application version
Version: 1.4.1
Last modified: 2025-10-26
"""

import os
from pathlib import Path
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

# Path to VERSION file (for local development)
VERSION_FILE = Path(__file__).parent.parent.parent.parent.parent / "VERSION"


def get_app_version() -> str:
    """
    Read version from environment variable (production) or VERSION file (development)

    Priority:
    1. BUILD_VERSION env var (set by Docker build from GitHub Actions)
    2. VERSION file (local development)
    3. Fallback to "1.4.1"
    """
    # Try environment variable first (production)
    env_version = os.getenv("BUILD_VERSION")
    if env_version and env_version != "unknown":
        return env_version

    # Try VERSION file (local development)
    try:
        if VERSION_FILE.exists():
            return VERSION_FILE.read_text().strip()
    except Exception:
        pass

    # Fallback
    return "1.4.1"


@router.get("/version")
async def get_version():
    """
    Get application version information

    Returns:
        version: Application version (from BUILD_VERSION env or VERSION file)
        build_date: Build timestamp (from BUILD_DATE env or current time)
        commit: Git commit SHA (from COMMIT_SHA env or 'local')
    """
    version = get_app_version()

    # Get build info from environment (injected by GitHub Actions via Docker)
    build_date = os.getenv("BUILD_DATE", datetime.utcnow().isoformat())
    commit_sha = os.getenv("COMMIT_SHA", "local")

    return {
        "version": version,
        "build_date": build_date,
        "commit": commit_sha[:7] if commit_sha != "local" else commit_sha
    }
