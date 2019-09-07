#!flask/bin/python

import os
import simplejson

from flask import Flask, request, render_template, redirect, flash, url_for, send_from_directory
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin
from werkzeug import secure_filename
from collections import defaultdict


app = Flask(__name__)
app.config['SECRET_KEY'] = 'hard to guess string'
app.config['UPLOAD_FOLDER'] = 'data/'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "このサイトを利用するにはログインしてください"

ALLOWED_EXTENSIONS = set(['txt', 'zip', 'xls', 'xlsx'])
IGNORED_FILES = set(['.gitignore'])

bootstrap = Bootstrap(app)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def gen_file_name(filename):
    i = 1
    while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
        name, extension = os.path.splitext(filename)
        filename = '%s_%s%s' % (name, str(i), extension)
        i += 1

    return filename


@app.route("/upload", methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        files = request.files['file']

        if files:
            filename = secure_filename(files.filename)
            filename = gen_file_name(filename)
            mime_type = files.content_type

            if not allowed_file(files.filename):
                result = uploadfile(name=filename, type=mime_type, size=0, not_allowed_msg="サポートされないファイルタイプです。")

            else:
                # save file to disk
                uploaded_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                files.save(uploaded_file_path)

                # get file size after saving
                size = os.path.getsize(uploaded_file_path)

                # return json for js call back
                result = uploadfile(name=filename, type=mime_type, size=size)
            
            return simplejson.dumps({"files": [result.get_file()]})

    if request.method == 'GET':
        # get all file in ./data directory
        files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'],f)) and f not in IGNORED_FILES ]
        
        file_display = []

        for f in files:
            size = os.path.getsize(os.path.join(app.config['UPLOAD_FOLDER'], f))
            file_saved = uploadfile(name=f, size=size)
            file_display.append(file_saved.get_file())

        return simplejson.dumps({"files": file_display})

    return redirect(url_for('index'))


@app.route("/delete/<string:filename>", methods=['DELETE'])
@login_required
def delete(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return simplejson.dumps({filename: 'True'})
        except:
            return simplejson.dumps({filename: 'False'})


@app.route("/data/<string:filename>", methods=['GET'])
@login_required
def get_file(filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER']), filename=filename)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        if(request.form["username"] in user_check and request.form["password"] == user_check[request.form["username"]]["password"]):
            login_user(users.get(user_check[request.form["username"]]["id"]))
            return redirect(request.args.get("next") or url_for("index"))
        else:
            flash("ログインするには正しい情報を入力して下さい", "error")
            return redirect(url_for("login"))

    if request.method == 'GET':
        return render_template("login.html")


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    return render_template('index.html')


@login_manager.user_loader
def load_user(user_id):
    return users.get(int(user_id))


class User(UserMixin):
    def __init__(self, id, name, password):
        self.id = id
        self.name = name
        self.password = password


users = {
    1: User(1, "user1", "password"),
    2: User(2, "user2", "password")
}


nested_dict = lambda: defaultdict(nested_dict)
user_check = nested_dict()
for i in users.values():
    user_check[i.name]["password"] = i.password
    user_check[i.name]["id"] = i.id


class uploadfile():
    def __init__(self, name, type=None, size=None, not_allowed_msg=''):
        self.name = name
        self.type = type
        self.size = size
        self.not_allowed_msg = not_allowed_msg
        self.url = "data/%s" % name
        self.delete_url = "delete/%s" % name
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
    app.run(host='0.0.0.0', port=5000)
