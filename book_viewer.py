from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Book, Holding


engine = create_engine('sqlite:///books.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


books = session.query(Book).all()
for x in books:
    print "__"
    for y in x.holdings:
        print y




