#!/usr/bin/env python3
"""
Script to rename all ai-service references to rag across the codebase
"""

import re
from pathlib import Path

# Files to update with their specific replacements
FILES_TO_UPDATE = {
    # Backend
    "backend/app/api/v1/monitoring.py": [
        ("AI_SERVICE_INTERNAL_URL", "RAG_INTERNAL_URL"),
        ("AI_SERVICE_URL", "RAG_URL"),
        ("check_ai_service_health", "check_rag_service_health"),
        ('"url": ai_service_url', '"url": rag_service_url'),
        ("ai_service_url", "rag_service_url"),
    ],
    "backend/app/api/v1/whatsapp_webhooks.py": [
        ("AI_SERVICE_URL", "RAG_URL"),
        ("ai_service_available", "rag_service_available"),
        ('"ai_service_url"', '"rag_service_url"'),
        ('"ai_service_available"', '"rag_service_available"'),
    ],
    # Frontend
    "frontend/app/api/llm/[...path]/route.ts": [
        ("[ai-service-proxy]", "[rag-service-proxy]"),
        ("Service AI", "Service RAG"),
    ],
    "frontend/app/chat/components/MonitoringTab.tsx": [
        ('value="ai-service"', 'value="rag"'),
        ('>AI Service<', '>RAG Service<'),
    ],
    # RAG
    "rag/api/monitoring_routes.py": [
        ('"ai-service"', '"rag"'),
    ],
    # GitHub Workflows
    ".github/workflows/deploy.yml": [
        ("Cleanup old ai-service tags", "Cleanup old rag tags"),
        ("ai-service tags", "rag tags"),
        ("/ai-service", "/rag"),
    ],
}

def update_file(file_path: Path, replacements: list):
    """Update a file with given replacements"""
    if not file_path.exists():
        print(f"[SKIP] {file_path} (file not found)")
        return False

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content
        for old, new in replacements:
            content = content.replace(old, new)

        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[OK] Updated {file_path}")
            return True
        else:
            print(f"[SKIP] {file_path} (no changes needed)")
            return False
    except Exception as e:
        print(f"[ERROR] {file_path}: {e}")
        return False

def main():
    """Main function"""
    root = Path(__file__).parent

    print("=" * 60)
    print("Renaming ai-service to rag across codebase")
    print("=" * 60)
    print()

    updated_count = 0

    for relative_path, replacements in FILES_TO_UPDATE.items():
        file_path = root / relative_path
        if update_file(file_path, replacements):
            updated_count += 1

    print()
    print("=" * 60)
    print(f"Summary: {updated_count} files updated")
    print("=" * 60)

if __name__ == '__main__':
    main()
