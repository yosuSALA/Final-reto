"""
Autenticación de perfiles.
Cada perfil tiene un token_secret (HMAC para el token de sesión) y opcionalmente
un password_hash + password_salt (PBKDF2-HMAC-SHA256) para login con clave.

Token de sesión: "{profile_id}:{HMAC-SHA256(profile_id, token_secret)}"

El perfil 'admin' funciona como clave maestra: su contraseña proviene del env
ADMIN_PASSWORD (default 'admin'). Una sesión admin puede emitir tokens para
otros perfiles sin requerir la clave de cada uno (modo testing).
"""
import hmac
import hashlib
import secrets
import os


# ── HMAC tokens ────────────────────────────────────────────────────────────────

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


# ── Contraseñas (PBKDF2-HMAC-SHA256) ──────────────────────────────────────────

PBKDF2_ITERATIONS = 200_000


def new_salt() -> str:
    return secrets.token_hex(16)


def hash_password(plain: str, salt: str) -> str:
    """Devuelve hex(PBKDF2-HMAC-SHA256(plain, salt))."""
    if plain is None:
        plain = ""
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        plain.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return derived.hex()


def verify_password(plain: str, expected_hash: str, salt: str) -> bool:
    if not expected_hash or not salt:
        return False
    candidate = hash_password(plain or "", salt)
    return hmac.compare_digest(candidate, expected_hash)


def set_profile_password(profile, plain: str) -> None:
    """Asigna contraseña a un Profile (genera salt nuevo)."""
    salt = new_salt()
    profile.password_salt = salt
    profile.password_hash = hash_password(plain or "", salt)


# ── Admin master key ──────────────────────────────────────────────────────────

ADMIN_PROFILE_ID = "00000000-0000-0000-0000-0000000000ad"
ADMIN_PROFILE_NAME = "admin"


def admin_master_password() -> str:
    """Clave maestra del perfil admin. Default 'admin' (configurable vía env)."""
    return os.environ.get("ADMIN_PASSWORD") or "admin"


def is_admin_profile(profile) -> bool:
    if profile is None:
        return False
    return (profile.role or "").lower() == "admin"
