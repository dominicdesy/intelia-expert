# -*- coding: utf-8 -*-
"""
Version tracking for deployment verification
Simple hardcoded version that increments with each deployment
"""

# HARDCODED VERSION - INCREMENT THIS NUMBER WITH EACH DEPLOYMENT
VERSION = "2.1.2"

import subprocess
import os
from datetime import datetime

def get_version_info():
    """
    Get version information from git commit

    Returns:
        dict: Version information including commit SHA, timestamp, and build ID
    """
    try:
        # Get short commit SHA (first 8 characters)
        commit_sha = subprocess.check_output(
            ['git', 'rev-parse', '--short=8', 'HEAD'],
            cwd=os.path.dirname(__file__),
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()

        # Get commit timestamp
        commit_time = subprocess.check_output(
            ['git', 'log', '-1', '--format=%ci'],
            cwd=os.path.dirname(__file__),
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()

        # Get branch name
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=os.path.dirname(__file__),
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()

        build_id = f"v{VERSION}-{commit_sha}"

        return {
            'version': VERSION,
            'build_id': build_id,
            'commit_sha': commit_sha,
            'commit_time': commit_time,
            'branch': branch,
            'deployed_at': datetime.utcnow().isoformat(),
        }
    except Exception as e:
        # Fallback if git is not available
        return {
            'version': VERSION,
            'build_id': f"v{VERSION}",
            'commit_sha': 'unknown',
            'commit_time': 'unknown',
            'branch': 'unknown',
            'deployed_at': datetime.utcnow().isoformat(),
            'error': str(e)
        }

# Generate version info at module load time
VERSION_INFO = get_version_info()
BUILD_ID = VERSION_INFO['build_id']
COMMIT_SHA = VERSION_INFO['commit_sha']

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
