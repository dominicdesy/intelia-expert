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

# Path to VERSION file
VERSION_FILE = Path(__file__).parent.parent.parent.parent.parent / "VERSION"


def get_app_version() -> str:
    """Read version from VERSION file"""
    try:
        if VERSION_FILE.exists():
            return VERSION_FILE.read_text().strip()
        return "1.4.1"  # Fallback
    except Exception:
        return "1.4.1"  # Fallback


@router.get("/version")
async def get_version():
    """
    Get application version information

    Returns:
        version: Application version (from VERSION file)
        build_date: Build timestamp (from env or current)
        commit: Git commit SHA (from env)
    """
    version = get_app_version()

    # Get build info from environment (injected by GitHub Actions)
    build_date = os.getenv("BUILD_DATE", datetime.utcnow().isoformat())
    commit_sha = os.getenv("COMMIT_SHA", "local")

    return {
        "version": version,
        "build_date": build_date,
        "commit": commit_sha[:7] if commit_sha != "local" else commit_sha
    }
