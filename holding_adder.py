from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Holding
import random
import time
import string
engine = create_engine('sqlite:///books.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

def build_holdings():
    for x in range(1, 747):
        random_num = random.randint(1,747)
        holding_selector = random.choice(['pdf', 'physical copy', 'epub',
                                         'ms word', 'braille', 'DAISY',
                                         'MOBI'])
        holding = Holding(holding_type=holding_selector, added_by=1, book_id=random_num,
                          holding_notes = ''.join(random.choice(string.ascii_letters) for x in range(15)))
        session.add(holding)
        session.commit()
        time.sleep(0.05)



def edit_holding():
        holding = session.query(Holding).all()
        for x in holding:
            x.added_by = 3
            session.commit()

build_holdings()