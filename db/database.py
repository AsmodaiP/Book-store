from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from db.models import Base, User

from contextlib import contextmanager

from config import settings

engine = create_engine(url=settings.DATABASE_URL)
SessionLocal = scoped_session(sessionmaker(autocommit=False, bind=engine))

def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    return SessionLocal()


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:session.close()
