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
    connect_args={"check_same_thread": False}
)

# Enable foreign key enforcement for SQLite
from sqlalchemy import event

@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency para obtener sesión de BD en endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Crear todas las tablas en la BD + migración liviana de columnas nuevas."""
    from backend.models import (
        Siniestro, Workshop, Invoice, InvoiceItem,
        TariffItem, AuditResult, AuditFinding,
        Poliza, AseguradoSintetico, Vehiculo, Documento
    )
    Base.metadata.create_all(bind=engine)
    _migrate_columns()


def _migrate_columns():
    """SQLite: añade columnas nuevas si faltan en tablas existentes."""
    from sqlalchemy import text
    migrations = [
        ("invoices", "siniestro_id", "INTEGER"),
        ("invoices", "is_test", "INTEGER DEFAULT 0"),
        ("audit_results", "is_test", "INTEGER DEFAULT 0"),
        ("audit_results", "audit_engine", "VARCHAR(20) DEFAULT 'rules'"),
    ]
    with engine.begin() as conn:
        for table, col, decl in migrations:
            cols = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            existing = {c[1] for c in cols}
            if col not in existing:
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {decl}"))
                except Exception:
                    pass
