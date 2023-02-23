from flask import Flask, render_template, redirect, url_for, g
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_security import UserMixin, RoleMixin, roles_accepted, Security, SQLAlchemySessionUserDatastore
from flask_login import LoginManager, login_manager, login_user
# import 'request' to request data from html
from flask import request
from flask_migrate import Migrate
from flask_assets import Bundle, Environment
from flask_babel import *

# https://testdriven.io/blog/flask-htmx-tailwind/?ref=morioh.com&utm_source=morioh.com


app = Flask(__name__)

assets = Environment(app)
css = Bundle("src/main.css", output="dist/main.css")
js = Bundle("src/*.js", output="dist/main.js")
assets.register("css", css)
assets.register("js", js)
css.build()
js.build()
# path to sqlite database
# this will create the db file in instance
# if database not present already

DB_URL = 'postgresql+psycopg2://{user}:{pw}@{url}/{db}'.format(user='postgres', pw='wPexSfG2ZhGrkBSbXrSf',
                                                               url='containers-us-west-176.railway.app:7481',
                                                               db='railway')
app.config.from_pyfile('settings.cfg')
babel = Babel(app)


@babel.localeselector
def get_locale():
    # if a user is logged in, use the locale from the user settings
    user = getattr(g, 'user', None)
    if user is not None:
        return user.locale
    # otherwise try to guess the language from the user accept
    # header the browser transmits.  We support de/fr/en in this
    # example.  The best match wins.
    return request.accept_languages.best_match(['lt', 'en', 'de'])


@babel.timezoneselector
def get_timezone():
    user = getattr(g, 'user', None)
    if user is not None:
        return user.timezone


@app.route('/test')
def test():
    current_language = request.accept_languages.best
    title = gettext("title")
    sub_title = gettext("sub_title")
    translation = gettext("translation")
    country = gettext("country")
    Taiwan = gettext("Taiwan")
    Japan = gettext("japan")
    US = gettext("US")
    test = gettext("<b>我會變亂碼</b>")
    return render_template("test.html", **locals())


app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
# needed for session cookies
app.config['SECRET_KEY'] = 'MY_SECRET'
# hashes the password and then stores in the databse
app.config['SECURITY_PASSWORD_SALT'] = "MY_SECRET"
# allows new registrations to application
app.config['SECURITY_REGISTERABLE'] = True
# to send automatic registration email to user
app.config['SECURITY_SEND_REGISTER_EMAIL'] = False
db = SQLAlchemy()
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)
db.init_app(app)
# runs the app instance
app.app_context().push()
roles_users = db.Table('roles_users',
                       db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
                       db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))


# create table in database for storing users
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    email = db.Column(db.String, unique=True)
    password = db.Column(db.String(255), nullable=False, server_default='')
    active = db.Column(db.Boolean())
    # backreferences the user_id from roles_users table
    roles = db.relationship('Role', secondary=roles_users, backref='roled')


def __init__(self, email, active, password):
    self.email = email
    self.active = active
    self.password = bcrypt.generate_password_hash(password).decode('UTF-8')


# create table in database for storing roles
class Role(db.Model, RoleMixin):
    __tablename__ = 'role'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)


# creates all database tables
with app.app_context():
    db.create_all()

user_datastore = SQLAlchemySessionUserDatastore(db.session, User, Role)
security = Security(app, user_datastore)


@app.route('/')
def index():  # put application's code here
    return render_template('index.html')


@app.route('/about')
def about():  # put application's code here
    return render_template('about.html')


@app.route('/contact')
def contact():  # put application's code here
    return render_template('contacts.html')


# signup page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    msg = ""
    # if the form is submitted
    if request.method == 'POST':
        # check if user already exists
        user = User.query.filter_by(email=request.form['email']).first()
        msg = ""
        # if user already exists render the msg
        if user:
            msg = "User already exist"
            # render signup.html if user exists
            return render_template('signup.html', msg=msg)

            # if user doesn't exist

            # store the user to database
        hashed_password = bcrypt.generate_password_hash(request.form['password']).decode('UTF-8')
        user = User(email=request.form['email'], active=1, password=hashed_password)

        # user = User(email=request.form['email'], active=1, password=pw_hash)

        # store the role
        role = Role.query.filter_by(id=request.form['options']).first()
        user.roles.append(role)

        # commit the changes to database
        db.session.add(user)
        db.session.commit()

        # login the user to the app
        # this user is current user
        login_user(user)
        # redirect to index page
        return redirect(url_for('index'))

    # case other than submitting form, like loading the page itself
    else:
        return render_template("signup.html", msg=msg)


# signin page
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    msg = ""
    if request.method == 'POST':
        # search user in database
        user = User.query.filter_by(email=request.form['email']).first()
        # if exist check password

        check_password = bcrypt.check_password_hash(user.password, request.form['password'])  # returns True

        if user:
            if check_password:
                # if password matches, login the user
                login_user(user)
                return redirect(url_for('index'))
            # if password doesn't match
            else:
                msg = "Wrong password"

        # if user does not exist
        else:
            msg = "User doesn't exist"
        return render_template('signin.html', msg=msg)

    else:
        return render_template("signin.html", msg=msg)


# for teachers page
@app.route('/teachers')
# only Admin can access the page
@roles_accepted('Admin')
def teachers():
    teachers = []
    # query for role Teacher that is role_id=2
    role_teachers = db.session.query(roles_users).filter_by(role_id=2)
    # query for the users' details using user_id
    for teacher in role_teachers:
        user = User.query.filter_by(id=teacher.user_id).first()
        teachers.append(user)
    # return the teachers list
    return render_template("teachers.html", teachers=teachers)


# for staff page current
@app.route('/staff')
# only Admin and Teacher can access the page
@roles_accepted('Admin', 'Teacher')
def staff():
    staff = []
    role_staff = db.session.query(roles_users).filter_by(role_id=3)
    for staf in role_staff:
        user = User.query.filter_by(id=staf.user_id).first()
        staff.append(user)
    return render_template("staff.html", staff=staff)


# for student page
@app.route('/students')
# only Admin, Teacher and Staff can access the page
@roles_accepted('Admin', 'Teacher', 'Staff')
def students():
    students = []
    role_students = db.session.query(roles_users).filter_by(role_id=4)
    for student in role_students:
        user = User.query.filter_by(id=student.user_id).first()
        students.append(user)
    return render_template("students.html", students=students)


# for details page
@app.route('/mydetails')
# Admin, Teacher, Staff and Student can access the page
@roles_accepted('Admin', 'Teacher', 'Staff', 'Student')
def mydetails():
    return render_template("mydetails.html")


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
