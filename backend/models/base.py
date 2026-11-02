from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import METADATA_DATABASE_URL

connect_args = {"check_same_thread": False} if METADATA_DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(METADATA_DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
Base = declarative_base()


def init_db() -> None:
    import models.analysis  # noqa: F401
    import models.conversation  # noqa: F401
    import models.dataset  # noqa: F401

    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
