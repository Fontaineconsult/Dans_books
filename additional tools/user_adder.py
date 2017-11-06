from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Book, User


engine = create_engine('sqlite:///C:\\Users\\913678186\\Box Sync\\'
                       'Udacity_Nanodegree\\Item Catelogue Project\\books.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

def add_user():
    user = User(username="Farty McFarterson", email="Dudelovesdick@yourmom.com",
                picture='http://i0.kym-cdn.com/entries/icons/original/000/006/907/ugly.jpg')
    session.add(user)
    session.commit()


def edit_user_email(search_email, new_email ):
    user = session.query(User).filter_by(email = search_email).one()
    user.email = new_email
    session.commit()

def edit_user_name(id, name):
    user = session.query(User).filter_by(id = id).one()
    user.username = name
    session.commit()

def view_user_data():
    users = session.query(User).all()

    for user in users:

        print "id: %s" % user.id
        print "username: %s" % user.username
        print "email: %s" % user.email
        print "P_hash: %s" % user.password_hash

edit_user_email('Dudelovesdick@yourmom.com', "123@abc.xyz")
