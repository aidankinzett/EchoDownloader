from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.sqlite import *
from sqlalchemy.orm import sessionmaker

DB_PATH = 'echodownloader.db'

Base = declarative_base()


class Video(Base):
    __tablename__ = 'videos'

    url = Column(Integer)
    subject_code = Column(String)
    title = Column(String)
    downloaded = Column(Integer)
    guid = Column(String, primary_key=True)
    watched = Column(BOOLEAN)


def createDatabase():
    engine = create_engine('sqlite:///' + DB_PATH)
    Base.metadata.create_all(engine)


def createSession():
    engine = create_engine('sqlite:///' + DB_PATH)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session