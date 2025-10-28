# -*- coding: utf-8 -*-
"""
Version tracking for deployment verification
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Version tracking for deployment verification
Reads from BUILD_VERSION env var (production) or VERSION file (development)
"""

import subprocess  # noqa: E402
import os  # noqa: E402
from datetime import datetime  # noqa: E402
from pathlib import Path  # noqa: E402


def get_app_version() -> str:
    """
    Read version from environment variable (production) or VERSION file (development)

    Priority:
    1. BUILD_VERSION env var (set by Docker build from GitHub Actions)
    2. VERSION file in project root (local development)
    3. Fallback to "1.4.1"
    """
    # Try environment variable first (production)
    env_version = os.getenv("BUILD_VERSION")
    if env_version and env_version != "unknown":
        return env_version

    # Try VERSION file (local development)
    try:
        version_file = Path(__file__).parent.parent / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
    except Exception:
        pass

    # Fallback
    return "1.4.1"


# Get version from environment or file
VERSION = get_app_version()


def get_version_info():
    """
    Get version information from environment variables (production) or git (development)

    Priority:
    1. Environment variables (BUILD_DATE, COMMIT_SHA) - set by Docker in production
    2. Git commands - for local development
    3. Fallback values

    Returns:
        dict: Version information including commit SHA, timestamp, and build ID
    """
    # Check if we have environment variables from Docker build (production)
    env_commit_sha = os.getenv("COMMIT_SHA")
    env_build_date = os.getenv("BUILD_DATE")

    if env_commit_sha and env_commit_sha != "unknown":
        # Production: use environment variables from GitHub Actions
        commit_sha = env_commit_sha[:8]  # Short SHA (first 8 characters)
        commit_time = (
            env_build_date
            if env_build_date != "unknown"
            else datetime.utcnow().isoformat()
        )
        branch = "main"  # Production is always main branch

        return {
            "version": VERSION,
            "build_id": f"v{VERSION}-{commit_sha}",
            "commit_sha": commit_sha,
            "commit_time": commit_time,
            "branch": branch,
            "deployed_at": commit_time,
        }

    # Development: try git commands
    try:
        # Get short commit SHA (first 8 characters)
        commit_sha = (
            subprocess.check_output(
                ["git", "rev-parse", "--short=8", "HEAD"],
                cwd=os.path.dirname(__file__),
                stderr=subprocess.DEVNULL,
            )
            .decode("utf-8")
            .strip()
        )

        # Get commit timestamp
        commit_time = (
            subprocess.check_output(
                ["git", "log", "-1", "--format=%ci"],
                cwd=os.path.dirname(__file__),
                stderr=subprocess.DEVNULL,
            )
            .decode("utf-8")
            .strip()
        )

        # Get branch name
        branch = (
            subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=os.path.dirname(__file__),
                stderr=subprocess.DEVNULL,
            )
            .decode("utf-8")
            .strip()
        )

        build_id = f"v{VERSION}-{commit_sha}"

        return {
            "version": VERSION,
            "build_id": build_id,
            "commit_sha": commit_sha,
            "commit_time": commit_time,
            "branch": branch,
            "deployed_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        # Fallback if git is not available
        return {
            "version": VERSION,
            "build_id": f"v{VERSION}",
            "commit_sha": "local",
            "commit_time": "unknown",
            "branch": "local",
            "deployed_at": datetime.utcnow().isoformat(),
            "error": str(e),
        }


# Generate version info at module load time
VERSION_INFO = get_version_info()
BUILD_ID = VERSION_INFO["build_id"]
COMMIT_SHA = VERSION_INFO["commit_sha"]


def get_build_id():
    """Get the current build ID (branch-sha)"""
    return BUILD_ID


def get_version_string():
    """Get a formatted version string for logging"""
    return (
        f"BUILD_ID={VERSION_INFO['build_id']} | "
        f"COMMIT={VERSION_INFO['commit_sha']} | "
        f"BRANCH={VERSION_INFO['branch']} | "
        f"DEPLOYED={VERSION_INFO['deployed_at']}"
    )
