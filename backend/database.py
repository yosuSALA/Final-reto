"""
Configuración de la base de datos SQLite con SQLAlchemy.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DB_PATH = os.environ.get(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(__file__), "auditor.db"),
)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

from sqlalchemy import event


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── ID del perfil por defecto (datos pre-existentes) ───────────────────────────
DEFAULT_PROFILE_ID = "00000000-0000-0000-0000-000000000001"

# Contraseña por defecto asignada a perfiles legados sin clave configurada.
LEGACY_DEFAULT_PASSWORD = "demo"


def init_db():
    """Crear todas las tablas + migración liviana de columnas nuevas."""
    from backend.models import (
        Profile, Siniestro, Workshop, Invoice, InvoiceItem,
        TariffItem, AuditResult, AuditFinding,
        Poliza, AseguradoSintetico, Vehiculo, Documento, AuditLog,
    )
    Base.metadata.create_all(bind=engine)
    _migrate_columns()
    _ensure_default_profile()
    _ensure_admin_profile()
    _assign_default_passwords()


def _migrate_columns():
    """SQLite: añade columnas nuevas si faltan en tablas existentes."""
    from sqlalchemy import text

    migrations = [
        # columnas legadas
        ("invoices", "siniestro_id", "INTEGER"),
        ("invoices", "is_test", "INTEGER DEFAULT 0"),
        ("audit_results", "is_test", "INTEGER DEFAULT 0"),
        ("audit_results", "audit_engine", "VARCHAR(20) DEFAULT 'rules'"),
        # columnas de aislamiento por perfil
        ("profiles", "token_secret", "VARCHAR(64)"),
        ("profiles", "role", "VARCHAR(50) DEFAULT 'analista'"),
        # columnas de autenticación con clave
        ("profiles", "password_hash", "VARCHAR(128)"),
        ("profiles", "password_salt", "VARCHAR(32)"),
        ("workshops", "profile_id", f"VARCHAR(36) REFERENCES profiles(id)"),
        ("asegurados_sinteticos", "profile_id", f"VARCHAR(36) REFERENCES profiles(id)"),
        ("polizas", "profile_id", f"VARCHAR(36) REFERENCES profiles(id)"),
        ("siniestros", "profile_id", f"VARCHAR(36) REFERENCES profiles(id)"),
        ("invoices", "profile_id", f"VARCHAR(36) REFERENCES profiles(id)"),
        ("tariff_items", "profile_id", f"VARCHAR(36) REFERENCES profiles(id)"),
        ("audit_results", "profile_id", f"VARCHAR(36) REFERENCES profiles(id)"),
    ]

    with engine.begin() as conn:
        for table, col, decl in migrations:
            try:
                cols = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            except Exception:
                continue
            existing = {c[1] for c in cols}
            if col not in existing:
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {decl}"))
                except Exception:
                    pass


def _ensure_default_profile():
    """
    Crea el perfil por defecto si no existe y asigna todos los datos
    huérfanos (sin profile_id) a ese perfil.
    """
    from sqlalchemy import text
    from backend.auth import new_token_secret

    db = SessionLocal()
    try:
        from backend.models import Profile

        existing = db.query(Profile).filter(Profile.id == DEFAULT_PROFILE_ID).first()
        if existing and (not existing.role or existing.role == "analista"):
            try:
                db.execute(text("UPDATE profiles SET role = 'demo_jurado' WHERE id = :pid"), {"pid": DEFAULT_PROFILE_ID})
                db.commit()
            except Exception:
                pass
        if not existing:
            secret = new_token_secret()
            default_profile = Profile(
                id=DEFAULT_PROFILE_ID,
                name="demo_jurado",
                display_name="Demo Principal",
                role="demo_jurado",
                token_secret=secret,
                is_active=1,
            )
            db.add(default_profile)
            db.commit()

        pid = DEFAULT_PROFILE_ID

        # Asigna datos pre-existentes al perfil por defecto
        for table in (
            "workshops",
            "asegurados_sinteticos",
            "polizas",
            "siniestros",
            "invoices",
            "tariff_items",
            "audit_results",
        ):
            try:
                db.execute(
                    text(
                        f"UPDATE {table} SET profile_id = :pid "
                        f"WHERE profile_id IS NULL"
                    ),
                    {"pid": pid},
                )
            except Exception:
                pass
        db.commit()
    finally:
        db.close()


def _ensure_admin_profile():
    """Crea (o repara) el perfil admin con la clave maestra del entorno."""
    from backend.auth import (
        new_token_secret, set_profile_password, admin_master_password,
        ADMIN_PROFILE_ID, ADMIN_PROFILE_NAME,
    )
    from backend.models import Profile

    db = SessionLocal()
    try:
        admin = db.query(Profile).filter(Profile.id == ADMIN_PROFILE_ID).first()
        master = admin_master_password()
        if not admin:
            admin = Profile(
                id=ADMIN_PROFILE_ID,
                name=ADMIN_PROFILE_NAME,
                display_name="Administrador",
                role="admin",
                token_secret=new_token_secret(),
                is_active=1,
            )
            set_profile_password(admin, master)
            db.add(admin)
            db.commit()
        else:
            # Si el rol cambió o falta hash, re-aplicar
            admin.role = "admin"
            admin.is_active = 1
            if not admin.token_secret:
                admin.token_secret = new_token_secret()
            # Re-aplica siempre la contraseña maestra del env para que ADMIN_PASSWORD
            # sea autoritativa entre arranques.
            set_profile_password(admin, master)
            db.commit()
    finally:
        db.close()


def _assign_default_passwords():
    """A perfiles existentes sin password_hash, les asigna 'demo' como clave."""
    from backend.auth import set_profile_password
    from backend.models import Profile

    db = SessionLocal()
    try:
        legacy = db.query(Profile).filter(
            (Profile.password_hash.is_(None)) | (Profile.password_hash == ""),
            Profile.role != "admin",
        ).all()
        for p in legacy:
            set_profile_password(p, LEGACY_DEFAULT_PASSWORD)
        if legacy:
            db.commit()
    finally:
        db.close()
