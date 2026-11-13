from sqlalchemy.orm import sessionmaker
from app.db.connection import create_database_engine

engine = create_database_engine()

sessionLocal = sessionmaker(bind=engine)

def get_db():
  db = sessionLocal()
  try:
    yield db
  finally: 
    db.close() 
    