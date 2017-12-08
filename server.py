from flask import Flask, request, redirect, render_template, session, flash
from mysqlconnection import MySQLConnector
import md5

import re
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
NAME_REGEX = re.compile(r'^[a-zA-Z]*$')
PASS_REGEX = re.compile(r'^(?=.*[0-9])(?=.*[a-zA-Z])([a-zA-Z0-9]+)$')

app = Flask(__name__)
app.secret_key = 'KeepItSecretKeepItSafe'
mysql = MySQLConnector(app,"wall_db")

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/wall')
    else:
        session['login'] = False
    return render_template('index.html')

@app.route('/login')
def login():
    session['login'] = True
    return render_template('index.html')

@app.route('/auth', methods=['POST'])
def authenticate():
    errors = False
    if 'user_id' in session:
        del session['user_id']

    if 'first_name' in session:
        del session['first_name']

    #Validate Email
    if not EMAIL_REGEX.match(request.form['email']):
        flash("***Invalid Email Address!", "email_err")
        errors = True

    #Validate Password character count
    if len(request.form['password']) < 8:
        flash("***Password must be more than 8 characters.", "pass_err")
        errors = True

    #Validate Confirm Password
    if request.form['password_con'] != request.form['password']:
        flash("***Confirm password doesn't match!")
        errors = True

    if errors:
        session['login'] = True
        return render_template('index.html')
    else:
        password = request.form['password']
        hashed_password = md5.new(password).hexdigest()

        enteredEmail = request.form['email']
        try:
            userInfo = mysql.query_db("SELECT * FROM users WHERE email = '" + str(enteredEmail) +"'")
            userInfo = userInfo[0]

            if str(userInfo['password']) == str(hashed_password):
                session['user_id'] = userInfo['id']
                session['first_name'] = userInfo['first_name']
                print "USER ID: ", session['user_id']
                return redirect('/wall')
            else:
                flash("Email and/or Password does not match with system records")
                return render_template('index.html')
        except IndexError:
            flash("Email and/or Password does not match with system records")
            return render_template('index.html')

@app.route('/process', methods=['POST'])
def submit():
    errors = False
    #Validate Blank Fields
    if len(request.form['name_first']) < 1 or len(request.form['name_last']) < 1 or len(request.form['email']) < 1 or len(request.form['password']) < 1 or len(request.form['password_con']) < 1:
        flash("***All fields are mandatory and cannot be blank.", "all_err")
        errors = True

    #Validate Email
    if not EMAIL_REGEX.match(request.form['email']):
        flash("***Invalid Email Address!", "email_err")
        errors = True

    #Validate First and Last Names
    if len(request.form['name_first']) < 2 or len(request.form['name_last']) < 2:
        flash("Name must be at least 2 characters")
    elif not NAME_REGEX.match(request.form['name_first']) or not NAME_REGEX.match(request.form['name_last']):
        flash("***First Name or Last Name cannot contain any numbers", "name_err")
        errors = True

    #Validate Password character count
    if len(request.form['password']) < 8:
        flash("***Password must be more than 8 characters.", "pass_err")
        errors = True
    # elif not PASS_REGEX.match(request.form['password']):
    #     flash("***Password must contain at least 1 uppercase letter and 1 numeric value.")

    #Validate Confirm Password
    if request.form['password_con'] != request.form['password']:
        flash("***Confirm password doesn't match!")
        errors = True

    name_first = request.form['name_first']
    name_last = request.form['name_last']
    email = request.form['email']

    if errors:
        return redirect('/')
    else:
        password = request.form['password']
        hashed_password = md5.new(password).hexdigest()

        query = ("INSERT INTO users (first_name, last_name, email, password, created_at) VALUES (:first_name, :last_name, :email, :password, NOW())")

        data = {
            "first_name" : name_first,
            "last_name" : name_last,
            "email" : email,
            "password" : hashed_password
        }

        session['user_id'] = mysql.query_db(query, data)
        session['first_name'] = name_first
        print "USER ID: ", session['user_id']

        return redirect('/wall')

@app.route('/wall')
def success():

    allMessages = mysql.query_db("SELECT message, first_name, last_name, messages.created_at, messages.id FROM messages JOIN users ON users.id = messages.user_id")

    allComments = mysql.query_db("SELECT comment, users.id AS user_id, message, first_name, last_name, messages.created_at, messages.id AS message_id, comments.id AS comment_id FROM comments JOIN messages ON comments.message_id = messages.id JOIN users ON users.id = comments.user_id")

    # print allMessages
    return render_template('wall.html', messages = allMessages, comments = allComments)

@app.route('/post_message', methods=['POST'])
def post_message():

    message = request.form['message']
    errors = False

    if len(request.form['message']) < 1:
        flash("***Input cannot be empty!")
        errors = True

    if errors:
        return redirect('/wall')
    else:
        query = ("INSERT INTO messages (message, user_id, created_at, updated_at) VALUES (:message, :user_id, NOW(), NOW())")

        data = {
            "message" : message,
            "user_id" : session['user_id']
        }

        mysql.query_db(query, data)

        return redirect('/wall')

@app.route('/post_comment/<message_id>', methods=['POST'])
def post_comment(message_id):

    comment = request.form['comment']
    errors = False
    if len(request.form['comment']) < 1:
        flash("***Input cannot be empty")
        errors = True

    if errors:
        return redirect('/wall')
    else:
        query = ("INSERT INTO comments (comment, created_at, updated_at, message_id, user_id) VALUES (:comment, NOW(), NOW(), :message_id, :user_id)")

        data = {
            "comment" : comment,
            "message_id" : message_id,
            "user_id" : session['user_id']
        }

        mysql.query_db(query, data)

        return redirect('/wall')

@app.route('/delete/<comment_id>', methods=['POST'])
def delete_comment(comment_id):
    query = ("DELETE FROM comments WHERE id = :comment_id")

    data = {
        "comment_id" : comment_id,
    }
    print comment_id

    mysql.query_db(query, data)
    return redirect('/wall')

@app.route('/logout')
def logout():
    del session['user_id']
    del session['first_name']
    session['login'] = False
    return render_template('index.html')

app.run(debug=True)