# app/api/v1/logging_models.py
# -*- coding: utf-8 -*-
"""
🎯 MODÈLES ET ENUMS POUR LE SYSTÈME DE LOGGING
📊 Enums, classes et constantes utilisées dans le système d'analytics
"""
from enum import Enum
from typing import Dict, List


class LogLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ResponseSource(str, Enum):
    RAG = "rag"
    OPENAI_FALLBACK = "openai_fallback"
    TABLE_LOOKUP = "table_lookup"
    VALIDATION_REJECTED = "validation_rejected"
    QUOTA_EXCEEDED = "quota_exceeded"


class UserRole(str, Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class Permission(str, Enum):
    VIEW_OWN_ANALYTICS = "view_own_analytics"
    VIEW_ALL_ANALYTICS = "view_all_analytics"
    VIEW_OPENAI_COSTS = "view_openai_costs"
    VIEW_SERVER_PERFORMANCE = "view_server_performance"
    MANAGE_SYSTEM = "manage_system"
    ADMIN_DASHBOARD = "admin_dashboard"


# 🔐 SYSTÈME DE PERMISSIONS PAR RÔLE
ROLE_PERMISSIONS: Dict[UserRole, List[Permission]] = {
    UserRole.USER: [
        Permission.VIEW_OWN_ANALYTICS,
        Permission.VIEW_OPENAI_COSTS
    ],
    UserRole.MODERATOR: [
        Permission.VIEW_OWN_ANALYTICS,
        Permission.VIEW_OPENAI_COSTS,
        Permission.VIEW_ALL_ANALYTICS
    ],
    UserRole.ADMIN: [
        Permission.VIEW_OWN_ANALYTICS,
        Permission.VIEW_ALL_ANALYTICS,
        Permission.VIEW_OPENAI_COSTS,
        Permission.VIEW_SERVER_PERFORMANCE,
        Permission.ADMIN_DASHBOARD
    ],
    UserRole.SUPER_ADMIN: [
        Permission.VIEW_OWN_ANALYTICS,
        Permission.VIEW_ALL_ANALYTICS,
        Permission.VIEW_OPENAI_COSTS,
        Permission.VIEW_SERVER_PERFORMANCE,
        Permission.ADMIN_DASHBOARD,
        Permission.MANAGE_SYSTEM
    ]
}