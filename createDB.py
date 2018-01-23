from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.sqlite import *
from sqlalchemy.orm import sessionmaker
import yaml
import os

# open the configuration file and save config as constants
with open("config.json", 'r') as ymlfile:
    CONFIG = yaml.load(ymlfile)

DOWNLOAD_DIRECTORY = os.path.join('static','videos')
DB_PATH = os.path.join(DOWNLOAD_DIRECTORY, 'echodownloader.db')

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