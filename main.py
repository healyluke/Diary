
from flask import Flask, render_template, url_for, request, redirect,session,flash
from flask_wtf import FlaskForm
from wtforms import StringField,SubmitField,PasswordField,TextAreaField,FileField
from wtforms.validators import DataRequired
import os.path
from flask_sqlalchemy import SQLAlchemy
import flask_login
from flask_login import UserMixin,LoginManager,login_required,login_user,logout_user, current_user
from wtforms.widgets import TextArea
import datetime
from datetime import datetime
from sqlalchemy.orm import relationship
import docx
from waitress import serve



db = SQLAlchemy()
# create the app
app = Flask(__name__)
# change string to the name of your database; add path if necessary
db_name = 'DiaryInfo.db'
# note - path is necessary for a SQLite db!!!
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, db_name)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True

class User(db.Model, UserMixin):
    __tablename__ = 'Users'
    id = db.Column(db.Integer, primary_key=True)
    Username = db.Column(db.String, unique=True, nullable=False)
    Password = db.Column(db.String, unique=True, nullable=False)
    children = relationship("Entries", backref="Users")
    
    def __init__(self, Username, Password):
        self.Username = Username
        self.Password = Password

class Entries(db.Model):
    __tablename__ = 'Entries'
    id = db.Column(db.Integer, primary_key=True)
    Content = db.Column(db.String)
    Owner_id = db.Column(db.Integer, db.ForeignKey('Users.id'))
    Title = db.Column(db.String)
    Date_moddified = db.Column(db.DateTime, default=datetime.now())
    parent = relationship("User", backref="Entries", viewonly=True)
    def __init__(self, Content, Owner_id, Title):
        self.Content = Content
        self.Owner_id = Owner_id
        self.Title = Title
   
def readtxt(filename):
    doc = docx.Document(filename)
    fullText = []
    for para in doc.paragraphs:
        fullText.append(para.text)
    return '\n'.join(fullText)

app.config['SECRET_KEY'] = "superdupersecret"
db.init_app(app)

#Login Stuff
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
   return User.query.session.get(User,int(user_id))



class AccountForm(FlaskForm):
   name = StringField("Username", validators=[DataRequired()])
   password = PasswordField('Password', validators=[DataRequired()])
   submit = SubmitField("Login")

class EntryForm(FlaskForm):
    title = TextAreaField(u'Title', validators=[DataRequired()])
    body = TextAreaField(u'Text', validators=[DataRequired()])
    submit = SubmitField("Save")

class UploadForm(FlaskForm):
   file = FileField()

@app.route('/')
def home():
   home_is_current_page = True
   return render_template('index.html',
                          home_is_current_page = home_is_current_page,
                          logged_in = current_user.is_authenticated)


@app.route('/welcome',methods=['GET', 'POST'])
@login_required
def welcome():
   text = None
   form = EntryForm()
   file_form = UploadForm()
   name = None
   User_posts = []
   posts_preview = []
   if 'Current_id' in session:
      Current_id = session['Current_id']
   posts = Entries.query.filter(Entries.Owner_id==Current_id).order_by(Entries.Date_moddified.desc())
   current_date = datetime.now()
   if request.method == 'POST':   
      file = request.files["file"]   
      if file.filename.endswith("docx"):
         text = readtxt(file)
      elif file.filename.endswith("txt"):
         text = file.read()
      else:
         flash("Invalid file type")
         return(redirect("/welcome"))
      session['filler_text'] = text
      return (redirect("/new_diary"))  
   return render_template('welcome.html',
                          name = name,
                          User_posts = User_posts,
                          form = form,
                          posts = posts,
                          posts_preview = posts_preview,
                          logged_in = current_user.is_authenticated,
                          current_date = current_date,
                          file_form = file_form,
                          text = text)



@app.route('/login',methods=['GET', 'POST'])
def login():
   login_is_current_page = True
   form = AccountForm()
   if form.validate_on_submit():
      user = User.query.filter_by(Username = form.name.data).first()
      if user:
         if user.Password == form.password.data:
            login_user(user)
            Current_id = flask_login.current_user.id
            session['Current_id'] = Current_id
            return redirect(url_for('welcome'))
         else:
            flash("Wrong Password")
      else:
         flash("Username does not exist")
   return render_template('login.html',
                          form = form,
                          login_is_current_page = login_is_current_page,
                          logged_in = current_user.is_authenticated)

@app.route('/register',methods = ['GET','POST'])
def register():
   register_is_current_page = True
   name = None
   password = None
   form = AccountForm()
   form.submit.label.text = 'Create Account'
   if form.validate_on_submit():
      if User.query.filter_by(Username='form.name.data').count() < 1:
         name = form.name.data
         form.name.data = ""
         password = form.password.data
         form.password.data = ""
         record = User(name,password)
         db.session.add(record)
         db.session.commit()
         return(redirect(url_for("login")))
      else:
         flash("Username Taken")
         return render_template('register.html',
                          name = name,
                          password = password,
                          form = form,
                          register_is_current_page = register_is_current_page,
                          logged_in = current_user.is_authenticated)
   else:
      return render_template('register.html',
                          name = name,
                          password = password,
                          form = form,
                          register_is_current_page = register_is_current_page,
                          logged_in = current_user.is_authenticated)



@app.route("/welcome/<int:entry_id>", methods = ["Get",'Post'])
@login_required
def entry(entry_id):
   entry = Entries.query.filter_by(id = entry_id).first()
   form = EntryForm()
   if request.method == 'GET': 
      form.body.data = entry.Content
      form.title.data = entry.Title
   if form.validate_on_submit():
      entry.Content = form.body.data
      entry.Date_moddified = datetime.now()
      entry.Title = form.title.data
      form.body.data = ""
      db.session.add(entry)
      db.session.commit()
      return(redirect(url_for("welcome")))
   else:
      return render_template("entry.html",
                          logged_in = current_user.is_authenticated,
                          entry = entry,
                          form = form)

@app.route("/new_diary",methods=['GET', 'POST'])
@login_required
def new_diary():
   form = EntryForm()
   if 'filler_text' in session:
         filler = session['filler_text']
         form.body.data = filler
   if form.validate_on_submit():
      if 'Current_id' in session:
         Current_id = session['Current_id']
      content = form.body.data
      title = form.title.data
      new_post = Entries(content,Current_id,title)
      db.session.add(new_post)
      db.session.commit()
      form.body.data = ""
      return redirect(url_for("welcome"))
   return render_template("new_diary.html",
                          form = form,
                          logged_in = current_user.is_authenticated)


@app.route('/logout')
@login_required
def  logout():
   logout_user()
   return redirect(url_for('login'))

@app.route("/delete/<int:post_id>")
@login_required
def delete(post_id):
   entry=Entries.query.filter_by(id=post_id).first()
   db.session.delete(entry)
   db.session.commit()
   return redirect(url_for('welcome'))

if __name__ == '__main__':
   app.run(host="0.0.0.0", port=80, debug=True)