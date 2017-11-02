from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Book
import time
import codecs
import csv

engine = create_engine('sqlite:///books.db')
engine.connect().connection.text_factory = str
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession() 

def add_books():
	with codecs.open("print media.csv", "r", encoding='utf-8') as f:
		reader = csv.reader(f)
		count = 0
		for row in reader:
			try:
				print row[1]
				book = Book(isbn = row[1], title = row[2], author = row[3],
					publisher = row[6], edition = row[4], date=row[5], user_id = 1)
				session.add(book)
				session.commit()

				time.sleep(0.05)
				count += 1
				print count
			except UnicodeEncodeError:
				print("Error")


def change_book_owner():
	books=session.query(Book).all()
	for book in books:
		book.user_id = 3
		session.commit()

change_book_owner()