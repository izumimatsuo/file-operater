#!flask/bin/python

import os
import simplejson

from flask import Flask, request, render_template, redirect, flash, url_for, send_from_directory
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, current_user, login_user, logout_user, login_required, UserMixin
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from werkzeug import secure_filename

APP_NAME = os.getenv('APP_NAME', '/filebox')
DB_TABLE_NAME = 'user_accounts'

app = Flask(__name__, static_url_path = APP_NAME + '/static')
app.config['SECRET_KEY'] = 'hard to guess string'
app.config['UPLOAD_FOLDER'] = 'data/'
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', '5')) * 1024 * 1024
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///test.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "このサイトを利用するにはログインしてください"

bootstrap = Bootstrap(app)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

ALLOWED_EXTENSIONS = set(['txt', 'zip', 'xls', 'xlsx'])
IGNORED_FILES = set(['.gitignore'])


@app.route(APP_NAME + "/api/v1/files", methods = ['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        files = request.files['file']

        if files:
            filename = secure_filename(files.filename)
            filename = gen_file_name(filename)
            mime_type = files.content_type

            if not allowed_file(files.filename):
                result = uploadfile(name = filename, type = mime_type, size = 0, not_allowed_msg = "サポートされないファイルタイプです。")
            else:
                uploaded_file_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.companyid + '_' + filename)
                files.save(uploaded_file_path)
                size = os.path.getsize(uploaded_file_path)
                result = uploadfile(name = filename, type = mime_type, size = size)
            
            return simplejson.dumps({"files": [result.get_file()]})

    if request.method == 'GET':
        files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'],f)) and f not in IGNORED_FILES ]
        file_display = []

        for f in files:
            size = os.path.getsize(os.path.join(app.config['UPLOAD_FOLDER'], f))
            file_saved = uploadfile(name = f.replace(current_user.companyid + '_', ''), size = size)
            file_display.append(file_saved.get_file())

        return simplejson.dumps({"files": file_display})


@app.route(APP_NAME + "/api/v1/files/<string:filename>", methods=['DELETE'])
@login_required
def delete(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.companyid + '_' + filename)

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return simplejson.dumps({filename: 'True'})
        except:
            return simplejson.dumps({filename: 'False'})

    return simplejson.dumps({filename: 'False'})


@app.route(APP_NAME + "/api/v1/files/<string:filename>", methods = ['GET'])
@login_required
def get_file(filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER']), filename = current_user.companyid + '_' + filename)


@app.route(APP_NAME + '/login', methods = ['GET', 'POST'])
def login():
    if(request.method == "POST"):
        form = request.form
        user = User.query.filter_by(username = form["username"], companyid = form["companyid"]).first()

        if user and bcrypt.check_password_hash(user.password, form["password"]):
            login_user(user)
            return redirect(request.args.get("next") or url_for("index"))
        else:
            flash("企業IDまたはユーザ名かパスワードが誤りです。正しい情報を入力して下さい", "error")
            return render_template("login.html", companyid = form["companyid"], username = form["username"], password = form["password"])

    return render_template("login.html")


@app.route(APP_NAME + '/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route(APP_NAME + '/')
@login_required
def index():
    return render_template('index.html')


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def gen_file_name(filename):
    i = 1
    while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], current_user.companyid + '_' + filename)):
        name, extension = os.path.splitext(filename)
        filename = '%s_%s%s' % (name, str(i), extension)
        i += 1

    return filename


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@login_manager.request_loader
def load_user_from_request(request):
    auth = request.authorization
    if auth and auth.type == 'basic':
        user = User.query.filter_by(username = auth.username, companyid = request.args.get('companyid')).first()

        if user and bcrypt.check_password_hash(user.password, auth.password):
            return user

    return None


class User(db.Model, UserMixin):
    __tablename__ = DB_TABLE_NAME
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String)
    password = db.Column(db.String)
    companyid = db.Column(db.String)


class uploadfile():
    def __init__(self, name, type = None, size = None, not_allowed_msg = ''):
        self.name = name
        self.type = type
        self.size = size
        self.not_allowed_msg = not_allowed_msg
        self.url = "api/v1/files/%s" % name
        self.delete_url = "api/v1/files/%s" % name
        self.delete_type = "DELETE"


    def get_file(self):
        if self.type != None:
            # POST an normal file
            if self.not_allowed_msg == '':
                return {"name": self.name,
                        "type": self.type,
                        "size": self.size, 
                        "url": self.url, 
                        "deleteUrl": self.delete_url, 
                        "deleteType": self.delete_type,}

            # File type is not allowed
            else:
                return {"error": self.not_allowed_msg,
                        "name": self.name,
                        "type": self.type,
                        "size": self.size,}

        # GET normal file from disk
        else:
            return {"name": self.name,
                    "size": self.size, 
                    "url": self.url, 
                    "deleteUrl": self.delete_url, 
                    "deleteType": self.delete_type,}


if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 5000)
