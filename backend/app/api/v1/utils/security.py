"""
Utilitaires de sécurité pour la protection des données personnelles (RGPD)
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Utilitaires de sécurité pour la protection des données personnelles (RGPD)
"""
import hashlib
import re
from typing import Optional


def mask_email(email: str, mask_char: str = "*", preserve_chars: int = 3) -> str:
    """
    Masque un email pour les logs en conformité RGPD Article 32

    Args:
        email: L'adresse email à masquer
        mask_char: Le caractère utilisé pour masquer (par défaut: *)
        preserve_chars: Nombre de caractères à préserver au début (par défaut: 3)

    Returns:
        Email masqué (ex: "joh***@example.com")

    Examples:
        >>> mask_email("john.doe@example.com")
        'joh***@example.com'
        >>> mask_email("a@test.com")
        'a***@test.com'
        >>> mask_email("contact@intelia.com", preserve_chars=5)
        'conta***@intelia.com'
    """
    if not email or not isinstance(email, str):
        return "***@***"

    # Validation basique du format email
    if "@" not in email:
        return mask_char * 8

    try:
        local, domain = email.split("@", 1)

        # Si la partie locale est courte, préserver moins de caractères
        preserve = min(preserve_chars, len(local))

        # Masquer la partie locale
        if len(local) <= preserve:
            masked_local = local[0] + mask_char * 3
        else:
            masked_local = local[:preserve] + mask_char * 3

        return f"{masked_local}@{domain}"

    except Exception:
        # En cas d'erreur, masquer complètement
        return f"{mask_char * 8}@{mask_char * 8}"


def hash_email(email: str, salt: Optional[str] = None) -> str:
    """
    Hash un email de manière irréversible pour les logs d'audit

    Args:
        email: L'adresse email à hasher
        salt: Sel optionnel pour le hash (recommandé)

    Returns:
        Hash SHA256 de l'email (hex)

    Examples:
        >>> hash_email("test@example.com")
        '973dfe463ec85785f5f95af5ba3906eedb2d931c24e69824a89ea65dba4e813b'
    """
    if not email or not isinstance(email, str):
        return "invalid_email"

    email_lower = email.lower().strip()

    if salt:
        email_with_salt = f"{email_lower}{salt}"
    else:
        email_with_salt = email_lower

    return hashlib.sha256(email_with_salt.encode()).hexdigest()


def mask_phone(phone: str, mask_char: str = "*", preserve_last: int = 2) -> str:
    """
    Masque un numéro de téléphone pour les logs

    Args:
        phone: Le numéro de téléphone à masquer
        mask_char: Le caractère utilisé pour masquer
        preserve_last: Nombre de chiffres à préserver à la fin

    Returns:
        Numéro masqué (ex: "+33******89")

    Examples:
        >>> mask_phone("+33612345678")
        '+33******78'
        >>> mask_phone("0612345678")
        '******78'
    """
    if not phone or not isinstance(phone, str):
        return mask_char * 10

    # Extraire uniquement les chiffres et le +
    digits_and_plus = re.sub(r'[^\d+]', '', phone)

    if len(digits_and_plus) < preserve_last + 1:
        return mask_char * 10

    # Préserver le + initial si présent
    if digits_and_plus.startswith("+"):
        prefix = "+" + digits_and_plus[1:3]  # +33, +1, etc.
        remaining = digits_and_plus[3:]
    else:
        prefix = ""
        remaining = digits_and_plus

    # Masquer le milieu, garder les derniers chiffres
    if len(remaining) <= preserve_last:
        masked = mask_char * 6 + remaining
    else:
        masked = mask_char * 6 + remaining[-preserve_last:]

    return prefix + masked


def mask_ip(ip: str, mask_last_octet: bool = True) -> str:
    """
    Masque une adresse IP pour la pseudonymisation

    Args:
        ip: L'adresse IP à masquer
        mask_last_octet: Si True, masque le dernier octet (IPv4) ou segment (IPv6)

    Returns:
        IP masquée (ex: "192.168.1.***")

    Examples:
        >>> mask_ip("192.168.1.42")
        '192.168.1.***'
        >>> mask_ip("2001:0db8:85a3:0000:0000:8a2e:0370:7334")
        '2001:0db8:85a3:0000:0000:8a2e:0370:***'
    """
    if not ip or not isinstance(ip, str):
        return "***.***.***.***"

    # IPv4
    if "." in ip and ":" not in ip:
        parts = ip.split(".")
        if len(parts) == 4 and mask_last_octet:
            return f"{'.'.join(parts[:3])}.***"
        return ip

    # IPv6
    if ":" in ip:
        parts = ip.split(":")
        if len(parts) >= 2 and mask_last_octet:
            return f"{':'.join(parts[:-1])}:***"
        return ip

    return "***.***.***.***"


def sanitize_for_logging(data: dict, sensitive_keys: Optional[list] = None) -> dict:
    """
    Sanitise un dictionnaire de données en masquant les champs sensibles

    Args:
        data: Dictionnaire à sanitiser
        sensitive_keys: Liste des clés sensibles (par défaut: email, password, token, etc.)

    Returns:
        Dictionnaire avec les données sensibles masquées

    Examples:
        >>> sanitize_for_logging({"email": "test@example.com", "name": "John"})
        {'email': 'tes***@example.com', 'name': 'John'}
    """
    if sensitive_keys is None:
        sensitive_keys = [
            "email", "password", "token", "secret", "api_key",
            "phone", "phone_number", "credit_card", "ssn",
            "access_token", "refresh_token", "jwt", "authorization"
        ]

    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()

        # Masquer les valeurs des clés sensibles
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            if isinstance(value, str):
                if "@" in value:
                    sanitized[key] = mask_email(value)
                elif "password" in key_lower or "secret" in key_lower or "token" in key_lower:
                    sanitized[key] = "***REDACTED***"
                elif any(char.isdigit() for char in value) and len(value) > 5:
                    # Probablement un numéro
                    sanitized[key] = mask_phone(value)
                else:
                    sanitized[key] = "***"
            else:
                sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            # Récursif pour les dictionnaires imbriqués
            sanitized[key] = sanitize_for_logging(value, sensitive_keys)
        else:
            sanitized[key] = value

    return sanitized
