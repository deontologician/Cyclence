import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def session():
    engine = create_engine(os.getenv('CYCLENCE_DB_CONNECTION_STRING'), echo=True)
    return sessionmaker(bind=engine)()
