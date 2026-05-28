"""
Autenticación de perfiles sin contraseña.
Cada perfil tiene un token_secret almacenado en BD.
Token: "{profile_id}:{HMAC-SHA256(profile_id, token_secret)}"
El cliente no puede falsificar tokens de otros perfiles sin conocer su secret.
"""
import hmac
import hashlib
import secrets


def new_token_secret() -> str:
    return secrets.token_hex(32)


def generate_profile_token(profile_id: str, token_secret: str) -> str:
    sig = hmac.new(
        token_secret.encode(),
        msg=profile_id.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"{profile_id}:{sig}"


def verify_profile_token(token: str, db):
    """Valida el token y retorna el Profile activo, o None si es inválido."""
    from backend.models import Profile

    if not token or ":" not in token:
        return None

    try:
        profile_id, sig = token.rsplit(":", 1)
    except ValueError:
        return None

    profile = (
        db.query(Profile)
        .filter(Profile.id == profile_id, Profile.is_active == 1)
        .first()
    )
    if not profile:
        return None

    expected = hmac.new(
        profile.token_secret.encode(),
        msg=profile_id.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if hmac.compare_digest(expected, sig):
        return profile
    return None
