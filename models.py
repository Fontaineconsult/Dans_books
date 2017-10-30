from sqlalchemy import Column,Integer,String, ForeignKey, DateTime

from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine

from passlib.apps import custom_app_context as pwd_context

import random, string, datetime
from itsdangerous import(TimedJSONWebSignatureSerializer as Serializer,
						 BadSignature, SignatureExpired)


Base = declarative_base()

secret_key = ''.join(random.choice(string.ascii_uppercase + string.digits)
					 for x in range(32))


class User(Base):
	__tablename__ = 'user'
	id = Column(Integer, primary_key=True)
	username = Column(String(32), index = True)
	picture = Column(String)
	email = Column(String, index=True)
	password_hash = Column(String(64))

	def hash_password(self, password):
		self.password_hash = pwd_context.encrypt(password)

	def verify_password(self, password):
		return pwd_context.verify(password, self.password_hash)

class Book(Base):
	__tablename__ = 'books'
	id = Column(Integer, primary_key=True)
	isbn = Column(String(13))
	title = Column(String)
	author = Column(String)
	publisher = Column(String)
	cover_photo_url = Column(String)
	edition = Column(Integer)
	date = Column(String)
	file_type = Column(String)
	date_added = Column(DateTime, default=datetime.datetime.utcnow())
	user_id = Column(Integer, ForeignKey('user.id'))
	user = relationship(User)
	holdings = relationship('Holding', backref="books")



class Holding(Base):
	__tablename__ = 'holding'
	id = Column(Integer, primary_key=True)
	holding_type = Column(String)
	added_by = Column(Integer, ForeignKey('user.id'))
	user = relationship(User)
	book_id = Column(Integer, ForeignKey('books.id'))
	book = relationship(Book)
	holding_notes = Column(String)




engine = create_engine('sqlite:///books.db')
 

Base.metadata.create_all(engine)
