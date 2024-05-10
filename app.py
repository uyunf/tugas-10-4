from pymongo import MongoClient
import jwt
from datetime import datetime, timedelta
import hashlib
from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    redirect,
    url_for,
)
from werkzeug.utils import secure_filename

app = Flask (__name__)

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['UPLOAD_FOLDER'] = './static/profile_pics'

SECRET_KEY = 'SPARTA'

MONGODB_CONNECTION_STRING = 'mongodb+srv://test:sparta@cluster0.zfjim4j.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'

client = MongoClient(MONGODB_CONNECTION_STRING)

db = client.dbsparta_Plus_week5

TOKEN_KEY = 'mytoken'

@app.route('/', methods=['GET'])
def home():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.users.find_one({'username': payload.get('id')})

        return render_template('index.html', user_info=user_info)
    except jwt.ExpiredSignatureError:
        msg = 'YOUR TOKEN HAS EXPIRED'
        return redirect(url_for('login', msg=msg))
    except jwt.exceptions.DecodeError:
        msg = 'THERE WAS A PROBLEM LOGGING YOU IN'
        return redirect(url_for('login', msg=msg))
    
@app.route('/login', methods=['GET'])
def login():
    msg = request.args.get('msg')
    return render_template('login.html', msg=msg)

@app.route('/user/<username>', methods=['GET'])
def user(username):
    token_receive = request.cookies.get(TOKEN_KEY)
    try: 
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        status = username == payload.get('id')
        user_info = db.users.find_one(
            {'username': username},
            {'_id': False}
        )
        return render_template('user.html', user_info=user_info, status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))

@app.route("/sign_in", methods=["POST"])
def sign_in():
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    result = db.users.find_one(
        {
            "username": username_receive,
            "password": pw_hash,
        }
    )
    if result:
        payload = {
            "id": username_receive,
            "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify(
            {
                "result": "success",
                "token": token,
            }
        )
    else:
        return jsonify(
            {
                "result": "fail",
                "msg": "We could not find a user with that id/password combination",
            }
        )

@app.route("/sign_up/save", methods=["POST"])
def sign_up():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,                               # id
        "password": password_hash,                                  # password
        "profile_name": username_receive,                           # user's name is set to their id by default
        "profile_pic": "",                                          # profile image file name
        "profile_pic_real": "profile_pics/profile_placeholder.png", # a default profile image
        "profile_info": ""                                          # a profile description
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})

@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['username_give']
    exists = bool(db.users.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})

@app.route('/update_profile', methods=['POST'])
def update_profile():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        username = payload.get('id')
        name_receive = request.form.get('name_give')
        about_receive = request.form.get('about_give')

        new_doc = {
            'profile_name': name_receive,
            'profile_info': about_receive,    
        }
        if 'file_give' in request.files:
            file = request.files.get('file_give')
            filename = secure_filename(file.filename)
            extension = filename.split('.')[-1]
            file_path = f'profile_pics/{username}.{extension}'
            file.save('./static/' + file_path)
            new_doc['profile_pic'] = filename
            new_doc['profile_pic_real'] = file_path

        db.users.update_one(
            {'username': username},
            {'$set': new_doc}
        )
        return jsonify({
            'result': 'success',
            'msg':'Yor profile has been update'
        })
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))
    
@app.route('/posting', methods=['POST'])
def posting():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.users.find_one({"username": payload["id"]})
        comment_receive = request.form["comment_give"]
        date_receive = request.form["date_give"]
        doc = {
                "username": user_info["username"],
                "profile_name": user_info["profile_name"],
                "profile_pic_real": user_info["profile_pic_real"],
                "comment": comment_receive,
                "date": date_receive
               }
        db.posts.insert_one(doc) #membuat text dan tanggal yng diterima bersamaan data sesi user(id, nama, gambar)
        return jsonify({
            'result': 'success',
            'msg':'Posting successful'
        })
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))
    
@app.route("/get_posts", methods=["GET"])
def get_posts():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        # We should fetch the full list of posts here
        username_receive = request.args.get('username_give')
        if username_receive == '': 
            posts = list(db.posts.find({}).sort("date", -1).limit(20))
        else:
            posts = list(db.posts.find({'username': username_receive}).sort("date", -1).limit(20))
        for post in posts:
            post["_id"] = str(post["_id"])
            post["count_heart"] = db.likes.count_documents(
                {"post_id": post["_id"], "type": "heart"}
            )
            post["count_star"] = db.likes.count_documents(
                {"post_id": post["_id"], "type": "star"}
            )
            post["count_thumbsup"] = db.likes.count_documents(
                {"post_id": post["_id"], "type": "thumbsup"}
            )
            post["heart_by_me"] = bool(
                db.likes.find_one(
                    {"post_id": post["_id"], "type": "heart", "username": payload["id"]}
                )
            )
            post["star_by_me"] = bool(
                db.likes.find_one(
                    {"post_id": post["_id"], "type": "star", "username": payload["id"]}
                )
            )
            post["thumbsup_by_me"] = bool(
                db.likes.find_one(
                    {"post_id": post["_id"], "type": "thumbsup", "username": payload["id"]}
                )
            )
        return jsonify(
            {
                "result": "success",
                "msg": "Successful fetched all posts",
                "posts": posts,
            }
        )
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
    
@app.route("/update_like", methods=["POST"])
def update_like():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        # We should change the like count for the post here
        user_info = db.users.find_one({"username": payload["id"]})
        post_id_receive = request.form["post_id_give"]
        type_receive = request.form["type_give"]
        action_receive = request.form["action_give"]
        doc = {
            "post_id": post_id_receive,
            "username": user_info["username"],
            "type": type_receive,
        }
        if action_receive == "like":
            db.likes.insert_one(doc) #menambahkan kan like maka akan masuk ke database danbertambaha
        else:
            db.likes.delete_one(doc)
        count = db.likes.count_documents(
            {"post_id": post_id_receive, "type": type_receive}
        )
        return jsonify({"result": "success", "msg": "updated", "count": count})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
    
@app.route('/about', methods=['GET'])
def about():
    return render_template('about.html')
    # token_receive = request.cookies.get(TOKEN_KEY)
    # try:
    #     payload = jwt.decode(
    #         token_receive,
    #         SECRET_KEY,
    #         algorithms=['HS256']
    #     )
    #     return jsonify({
    #         'result': 'success',
    #         'msg':'Updated!'
    #     })
    # except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
    #     return redirect(url_for('home'))

@app.route('/secret', methods=['GET'])
def secret():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        ) #mencoba mengambiltoken dari cookies
        user_info = db.users.find_one({'username': payload.get('id')})
        return render_template('secret.html', user_info=user_info) #jika benar akan di render template
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home')) #jika error alihkan ke login
    

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
    