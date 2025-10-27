# -*- coding: utf-8 -*-
"""
rag_postgresql_config.py - Configuration PostgreSQL
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
rag_postgresql_config.py - Configuration PostgreSQL
"""

import os

# PostgreSQL configuration
POSTGRESQL_CONFIG = {
    "user": os.getenv("DB_USER", "doadmin"),
    "password": os.getenv("DB_PASSWORD", ""),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 25060)),
    "database": os.getenv("DB_NAME", "defaultdb"),
    "ssl": os.getenv("DB_SSL", "require"),
}

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"

# Import availability checks
try:
    import asyncpg

    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    asyncpg = None

try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None
