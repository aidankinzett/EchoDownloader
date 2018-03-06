from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.sqlite import *
from sqlalchemy.orm import sessionmaker



engine = create_engine('sqlite:///orm.db')
Session = sessionmaker(bind=engine)

session = Session()


Base = declarative_base()

class Video(Base):
    __tablename__ = 'videos'

    URL = Column(Integer)
    SubjectCode = Column(String)
    Title = Column(String)
    Downloaded = Column(BOOLEAN)
    GUID = Column(String, primary_key=True)
    Watched = Column(BOOLEAN)


Base.metadata.create_all(engine)

ed_user = Video(URL='www.google.com',SubjectCode='IFB130',Title='suck',Downloaded=True,GUID='adfasdf',Watched=False)
session.add(ed_user)
session.commit()

for instance in session.query(Video).order_by(Video.Title):
    print(instance.URL, instance.SubjectCode)

