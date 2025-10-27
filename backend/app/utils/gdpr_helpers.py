"""
GDPR Helper Functions
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
GDPR Helper Functions
Utilities for GDPR compliance (masking PII, anonymization, etc.)
"""


def mask_email(email: str) -> str:
    """
    Masque un email pour les logs (GDPR - minimisation des données)

    Args:
        email: Email à masquer (ex: "john.doe@example.com")

    Returns:
        Email masqué (ex: "j***e@e***.com")

    Examples:
        >>> mask_email("john.doe@example.com")
        'j***e@e***.com'

        >>> mask_email("a@b.com")
        'a***@b***.com'

        >>> mask_email("invalid")
        '***'

        >>> mask_email("")
        '***'

        >>> mask_email(None)
        '***'
    """
    if not email or not isinstance(email, str) or "@" not in email:
        return "***"

    try:
        local, domain = email.split("@", 1)

        # Masquer la partie locale (avant @)
        if len(local) <= 1:
            masked_local = f"{local}***"
        else:
            masked_local = f"{local[0]}***{local[-1]}"

        # Masquer le domaine (après @)
        if "." not in domain:
            masked_domain = f"{domain[0]}***" if domain else "***"
        else:
            domain_parts = domain.rsplit(".", 1)  # ["example", "com"]
            domain_name = domain_parts[0]
            domain_ext = domain_parts[1]

            if len(domain_name) <= 1:
                masked_domain = f"{domain_name[0]}***.{domain_ext}"
            else:
                masked_domain = f"{domain_name[0]}***.{domain_ext}"

        return f"{masked_local}@{masked_domain}"

    except Exception:
        # En cas d'erreur, masquer complètement
        return "***@***.***"


def mask_user_id(user_id: str) -> str:
    """
    Masque un UUID pour les logs

    Args:
        user_id: UUID à masquer

    Returns:
        UUID partiellement masqué (premiers 8 caractères)

    Examples:
        >>> mask_user_id("123e4567-e89b-12d3-a456-426614174000")
        '123e4567-****'
    """
    if not user_id or not isinstance(user_id, str):
        return "****"

    if len(user_id) >= 8:
        return f"{user_id[:8]}-****"

    return "****"


def mask_phone(phone: str) -> str:
    """
    Masque un numéro de téléphone

    Args:
        phone: Numéro à masquer

    Returns:
        Téléphone masqué

    Examples:
        >>> mask_phone("+33612345678")
        '+33***678'
    """
    if not phone or not isinstance(phone, str):
        return "***"

    if len(phone) <= 6:
        return "***"

    # Garder préfixe (3 chars) et fin (3 chars)
    return f"{phone[:3]}***{phone[-3:]}"


# Pour faciliter l'import
__all__ = ["mask_email", "mask_user_id", "mask_phone"]
