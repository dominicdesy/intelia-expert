# app/api/v1/logging_permissions.py
# -*- coding: utf-8 -*-
"""
🔐 SYSTÈME DE PERMISSIONS POUR LE LOGGING
🛡️ Gestion des rôles et autorisations d'accès aux analytics
"""
from typing import Dict, Any
from functools import wraps
from fastapi import HTTPException

from .logging_models import UserRole, Permission, ROLE_PERMISSIONS


def has_permission(user: Dict[str, Any], permission: Permission) -> bool:
    """Vérifie si un utilisateur a une permission spécifique"""
    user_type = user.get("user_type", "user")
    
    # Rétrocompatibilité : si is_admin=True, donner permissions admin
    if user.get("is_admin", False) and user_type == "user":
        user_type = "admin"
    
    try:
        role = UserRole(user_type)
        return permission in ROLE_PERMISSIONS.get(role, [])
    except ValueError:
        # Si user_type inconnu, traiter comme user normal
        return permission in ROLE_PERMISSIONS.get(UserRole.USER, [])


def require_permission(permission: Permission):
    """Décorateur pour vérifier les permissions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Récupérer current_user des kwargs ou args
            current_user = kwargs.get('current_user')
            if not current_user:
                # Chercher dans les args (cas des dépendances FastAPI)
                for arg in args:
                    if isinstance(arg, dict) and 'user_id' in arg:
                        current_user = arg
                        break
            
            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            if not has_permission(current_user, permission):
                raise HTTPException(
                    status_code=403, 
                    detail=f"Permission '{permission.value}' required. Your role: {current_user.get('user_type', 'unknown')}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def is_admin_user(user: Dict[str, Any]) -> bool:
    """Vérifie si un utilisateur est admin (rétrocompatibilité)"""
    return (
        user.get("is_admin", False) or 
        user.get("user_type") in ["admin", "super_admin"]
    )
