"""
backend/database.py — VIGIL SQLAlchemy Database Configuration & Initialization
=============================================================================
Manages:
  - SQLite database engine by default (`vigil.db`) with PostgreSQL override support
  - Thread-safe scoped session factory
  - Dependency generator for FastAPI routes (`get_db`)
  - Automatic table creation and default seed data initialization
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "vigil.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# SQLite requires check_same_thread=False for FastAPI multi-threaded requests
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency for yielding transactional database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables and seed baseline records if empty."""
    import backend.models.db_models as models
    from backend.services.auth_service import hash_password

    Base.metadata.create_all(bind=engine)

    # Auto-migration for SQLite new columns
    if DATABASE_URL.startswith("sqlite"):
        from sqlalchemy import text
        with engine.connect() as conn:
            try:
                res = conn.execute(text("PRAGMA table_info(incidents)"))
                cols = [row[1] for row in res.fetchall()]
                if cols:
                    if "notes" not in cols:
                        conn.execute(text("ALTER TABLE incidents ADD COLUMN notes TEXT"))
                    if "supporting_evidence" not in cols:
                        conn.execute(text("ALTER TABLE incidents ADD COLUMN supporting_evidence TEXT"))
                conn.commit()
            except Exception:
                pass

            try:
                res = conn.execute(text("PRAGMA table_info(evidence)"))
                cols = [row[1] for row in res.fetchall()]
                if cols:
                    if "checksum_sha256" not in cols:
                        conn.execute(text("ALTER TABLE evidence ADD COLUMN checksum_sha256 VARCHAR(64)"))
                conn.commit()
            except Exception:
                pass


    db = SessionLocal()
    try:
        # 1. Seed Default Admin User if no users exist
        admin_user = db.query(models.User).filter_by(username="admin").first()
        if not admin_user:
            admin_user = models.User(
                username="admin",
                email="admin@vigil.system",
                hashed_password=hash_password("admin123"),
                role="admin",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            print("[Database] Initialized default admin user ('admin' / 'admin123').")

        # 2. Seed Default Intersection & CCTV Cameras if empty
        if db.query(models.Camera).count() == 0:
            default_cameras = [
                models.Camera(
                    id="CAM_NORTH_01",
                    name="Junction 04 - North Approach",
                    location="Grand Ave Northbound",
                    stream_url="assets/videos/north.mp4",
                    camera_type="traffic",
                    status="online",
                    is_active=True
                ),
                models.Camera(
                    id="CAM_SOUTH_01",
                    name="Junction 04 - South Approach",
                    location="Grand Ave Southbound",
                    stream_url="assets/videos/south.mp4",
                    camera_type="traffic",
                    status="online",
                    is_active=True
                ),
                models.Camera(
                    id="CAM_EAST_01",
                    name="Junction 04 - East Approach",
                    location="5th St Eastbound",
                    stream_url="assets/videos/east.mp4",
                    camera_type="traffic",
                    status="online",
                    is_active=True
                ),
                models.Camera(
                    id="CAM_WEST_01",
                    name="Junction 04 - West Corridor",
                    location="5th St Westbound (Emergency Route)",
                    stream_url="assets/videos/west1.mp4",
                    camera_type="traffic",
                    status="online",
                    is_active=True
                ),
                models.Camera(
                    id="CAM_SEC_01",
                    name="Pedestrian Plaza CCTV",
                    location="Central Square Walkway",
                    stream_url="assets/videos/north.mp4",
                    camera_type="security",
                    status="online",
                    is_active=True
                )
            ]
            db.add_all(default_cameras)
            db.commit()
            print("[Database] Initialized 5 default traffic and security camera configurations.")
    finally:
        db.close()
