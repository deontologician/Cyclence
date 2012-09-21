'''Creates the database from the model'''
import os

from sqlalchemy import create_engine

from cyclence.Calendaring import CyclenceBase


if __name__ == '__main__':
    engine = create_engine(os.getenv('CYCLENCE_DB_CONNECTION_STRING'), echo=True)
    CyclenceBase.metadata.create_all(engine)
