# user_model.py – SQLite tables (Ensure the engine variable is correctly named/exported)
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./medimate.db"
# Change 'engine' to 'Engine' to match what backend_service.py is importing
Engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=Engine)
Base = declarative_base()

class User(Base):
    # ... (rest of User class) ...
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    email = Column(String, nullable=True, unique=True, index=True)

class HealthRecord(Base):
    # ... (rest of HealthRecord class) ...
    __tablename__ = "health_records"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    diagnosis = Column(String)
    severity = Column(String)
    raw_ehr_text = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

def create_db_tables():
    Base.metadata.create_all(bind=Engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Note: By changing the local variable name to 'Engine' (with a capital E), 
# it becomes available for import by backend_service.py.