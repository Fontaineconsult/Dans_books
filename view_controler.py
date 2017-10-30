from flask import Flask, render_template, request, \
    redirect, url_for, flash, jsonify, abort
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, exc
from models import Base, Book, User, Holding

from flask import session as login_session
from flask import make_response, Blueprint
from flask_paginate import Pagination, get_page_parameter, get_page_args
import random, string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from cgi import escape
import  requests

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']




app = Flask(__name__)
app.jinja_env.add_extension('jinja2.ext.do')
engine = create_engine('sqlite:///books.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

def getUserID(email):
    try:
        user = session.query(User).filter_by(email = email).first()
        return  user.id
    except exc.NoResultFound:
        return None

def getUserInfo(user_id):
    user = session.query(User).filter_by(id = user_id).one()
    return user


def createUser(login_session):
    newUser = User(username = login_session['username'], email = login_session['email'],
                   picture = login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email = login_session['email']).one()
    return user.id


def get_book(id_num):
    try:
        book = session.query(Book).filter_by(id=id_num).one()
        return book
    except exc.NoResultFound:
        print "Tried to get book: Not found"
        return None

def get_holding(id_num):
    try:
        holding = session.query(Holding).filter_by(id=id_num).one()
        return holding
    except exc.NoResultFound:
        print "Tried to get holding: Not found"
        return None

def check_object_owner(query_object):
    if query_object is not None:
        try:
            if query_object.user.username == login_session['username']:
                return True
            else:
                flash('Invalid User')
                return False

        except KeyError:
            flash('No User Logged In')
            return False
    return False

def username():
    if 'username' in login_session:
        return login_session['username']
    else:
        return None

@app.route('/logout/')
def logout():

    if 'gplus_id' in login_session:
        return redirect((url_for('gdisconnect')))
    else:
        login_session.clear()
        return redirect(url_for('mainpage'))


@app.route('/add_user/', methods=['GET', 'POST'])
def add_user():

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        if username == "" or password == "" or email == "":
            flash("Missing item.")
            return redirect(url_for('add_user'))
        user_check = session.query(User).filter_by(username = username).first()
        email_check = session.query(User).filter_by(email = email).first()
        if user_check or email_check:
            print user_check
            flash("This username or email already exists")
            return redirect(url_for('add_user'))

        user = User(username = username, email = email,
                    picture = "http://camtech.must.ac.ug/wp-content/"
                              "uploads/2013/11/default-pic.png")
        user.hash_password(password)
        session.add(user)
        session.commit()
        user_id = getUserID(email)
        user_info = getUserInfo(user_id)
        login_session['username'] = user_info.username
        login_session['picture'] = user_info.picture
        login_session['email'] = user_info.email

        return redirect(url_for('mainpage'))
    else:
        return render_template('add_user.html')


@app.route('/login/', methods=['GET', 'POST'])
def showLogin():

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            user = session.query(User).filter_by(username = username).one()
        except exc.NoResultFound:
            flash('User Not Found')
            return redirect(url_for('showLogin'))

        if user.verify_password(password):
            login_session['username'] = user.username
            login_session['picture'] = user.picture
            login_session['email'] = user.email
            print "Access Granted"
            return redirect(url_for('mainpage'))
        else:
            flash('Username or Password Incorrect')
            return redirect(url_for('showLogin'))
    if 'username' not in login_session:
        state= ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
        login_session['state'] = state
        return render_template('login.html', STATE=state, username='Home')
    else:
        flash('Already logged in. Logging Out')
        redirect(url_for('logout'))

@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()
    user_check = getUserID(data['email'])
    print data
    if user_check is None:
        guser_info = {'username':data['name'],'email':data['email'],
                      'picture':data['picture']}

        user = getUserInfo(createUser(guser_info))
        login_session['username'] = user.username
        login_session['picture'] = user.picture
        login_session['email'] = user.email
    else:
        user = getUserInfo(user_check)
        login_session['username'] = user.username
        login_session['picture'] = user.picture
        login_session['email'] = user.email

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        flash("Successfully Logged Out")
        return redirect(url_for('mainpage'))
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

@app.route('/')
@app.route('/main/')
def mainpage():
    books = session.query(Book).order_by(desc(Book.id)).limit(10)
    return render_template('main.html', books=books, username=username())


@app.route('/listall')
def listitems():
    books = session.query(Book).join(Book.holdings).order_by(desc(Book.id)).all()
    print login_session.get('access_token')
    if 'username' not in login_session:
        login_session['username'] = None
    return render_template('item_views.html', books=books, username =login_session['username'])

@app.route('/book/search/result/', defaults={'page': 1})
@app.route('/book/', defaults={'page': 1})
@app.route('/book/page/<int:page>')

def pagified_items(page):
    page, per_page, offset = get_page_args()

    title_query = request.args.get('search_title')
    isbn_query = request.args.get('search_isbn')
    if title_query or isbn_query:
        if title_query:
            count = session.query(Book).filter(Book.title.like("%" + title_query + "%")).count()
            books = session.query(Book).filter(Book.title.like("%" + title_query + "%")).offset(offset).limit(per_page)
        if isbn_query:
            count = session.query(Book).filter(Book.isbn.like("%" + isbn_query + "%")).count()
            books = session.query(Book).filter(Book.isbn.like("%" + isbn_query + "%")).offset(offset).limit(per_page)
        if isbn_query and title_query:
            count = session.query(Book).filter_by(isbn=isbn_query, title=title_query).count()
            books = session.query(Book).filter_by(isbn=isbn_query, title=title_query).offset(offset).limit(per_page)
    else:
        count = session.query(Book).count()
        books = session.query(Book).order_by(desc(Book.id)).offset(offset).limit(per_page)
    if session.query(Book).order_by(desc(Book.id)).offset(offset).limit(per_page).count() == 0:
        return redirect(url_for('mainpage'))

    pagination = Pagination(page=page,
                            total=count,
                            record_name='books',
                            format_total=True)
    if 'username'  not in login_session:
        login_session['username'] = None
    return render_template('paginated.html',
                           books=books,
                           pagination=pagination,
                           username =login_session['username'])


@app.route('/book/search/')
def search_book():
    return render_template('item_search.html')

@app.route('/book/search/result')
def search_result():
    title_query = request.args.get('search_title')
    isbn_query = request.args.get('search_isbn')

    if title_query:
        title_search = session.query(Book).filter(Book.title.like("%" + title_query + "%")).all()
        flash(str(len(title_search)) + " results found")
        if title_search:
            return render_template('item_views.html', books = title_search)
        else:
            flash('No Item Found')
            return render_template('item_views.html')
    if isbn_query:
        isbn_search = session.query(Book).filter(Book.isbn.like("%" + isbn_query + "%")).all()
        flash(str(len(isbn_search)) + " results found")
        if isbn_query:
            return render_template('item_views.html', books = isbn_search)
        else:
            flash('No Item Found')
            return render_template('item_views.html')
    if title_query and isbn_query:
        multi_search = session.query(Book).filter_by(isbn=isbn_query, title=title_query).all()
        if multi_search:
            return render_template('item_views.html', books = multi_search)
        else:
            flash('No Item Found')
            return render_template('item_views.html')

@app.route('/addbook', methods=['GET','POST'])
def  addbook():
    if 'username' in login_session:
        if request.method == 'POST':
            title = request.form['title']
            isbn = request.form['ISBN']
            author = request.form['author']
            publisher = request.form['publisher']
            edition = request.form['edition']
            date = request.form['date']
            add_book = Book(isbn = isbn, title = title, author = author,
                publisher = publisher, edition = edition, date=date,
                            user_id = getUserID(login_session['email']))
            session.add(add_book)
            session.commit()
            return redirect((url_for('mainpage')))
        else:
            return render_template('add_book.html', username=username())
    else:
        response = make_response('User Not Found',300)
        response.headers['Content-Type'] = 'text/html'
        return redirect(url_for('showLogin'))

@app.route('/book/<int:id_num>/', methods=['GET', 'POST'])
def view_book(id_num):
    book = get_book(id_num)
    if book:
        if request.method == 'POST':
            add_holding = Holding(holding_type = request.form['holding_type'],
                                  holding_notes = request.form['holding_notes'],
                                  added_by = request.form['added_by'])
            session.add(add_holding)
            session.commit()
            return render_template('book_view.html', item=book, username=login_session['username'])
        else:
            return render_template('book_view.html', item=book, username =login_session['username'])
    else:
        flash("Item not found")
        return redirect(url_for('mainpage'))

@app.route('/book/isbn/<int:isbn>/')
def view_book_isbn(isbn):
    items = session.query(Book).filter_by(isbn=isbn).all()
    return render_template('item_views.html', books=items)

@app.route('/book/<int:id_num>/delete', methods=['GET', 'POST'])
def delete_book(id_num):
    book_to_delete = get_book(id_num)
    if check_object_owner(book_to_delete):
        if request.method == 'POST':
            if book_to_delete:
                session.delete(book_to_delete)
                session.commit()
                flash(book_to_delete.title + " deleted")
                return redirect(url_for('mainpage'))
            else:
                flash("Item not found")
                return redirect(url_for('mainpage'))
        else:
            if book_to_delete:
                return render_template('item_delete.html', book=book_to_delete)
            else:
                flash("Item not found")
                return redirect(url_for('mainpage'))
    else:
        flash('Action Denied')
        return redirect(url_for('mainpage'))

@app.route('/book/<int:id_num>/edit', methods=['GET', 'POST'])
def edit_book(id_num):
    book_to_edit = get_book(id_num)
    if check_object_owner(book_to_edit):
        if request.method == 'POST':
            if book_to_edit:
                book_to_edit.title = request.form['title']
                book_to_edit.ISBN = request.form['ISBN']
                book_to_edit.author = request.form['author']
                book_to_edit.publisher = request.form['publisher']
                book_to_edit.edition = request.form['edition']
                book_to_edit.date = request.form['date']
                session.commit()
                return redirect(url_for('mainpage'))
            else:
                flash("Item not found")
                return redirect(url_for('mainpage'))
        else:
            if book_to_edit:
                return render_template('item_edit.html', book=book_to_edit)
            else:
                flash("Item not found")
                return redirect(url_for('mainpage'))
    else:
        flash("Action Denied")
        return redirect(url_for('mainpage'))

@app.route('/holding/<int:holding_id_num>/edit', methods=['GET', 'POST'])
def edit_holding(holding_id_num):
    holding = get_holding(holding_id_num)
    if check_object_owner(holding):
        if request.method == 'POST':
            if holding:
                if request.form['edit_del_submit'] == "Edit":
                    holding.holding_type = request.form['holding_type']
                    holding.holding_notes = request.form['holding_notes']
                    session.commit()
                    flash('Holding edited')
                if request.form['edit_del_submit'] == 'Delete':
                    session.delete(holding)
                    session.commit()
                    flash('Holding deleted')
                return redirect(url_for('mainpage'))
            else:
                flash('Item not found')
                return redirect(url_for('mainpage'))
        else:
            if holding:
                print holding.holding_type
                print holding.book.title
                return render_template('edit_holding.html', holding=holding)
            else:
                flash('Item not found')
                return redirect(url_for('mainpage'))
    else:
        flash('Action Denied')
        return redirect(url_for('mainpage'))




if __name__ == '__main__':
    app.secret_key = "Super Secret Key"
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
