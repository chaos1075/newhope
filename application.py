import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, usd
from datetime import datetime
import time

# configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure cs50 library to use SQLite database
db = SQL("sqlite:///newhope.db")

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """show user's dashboard"""
    # current date and time
    today = datetime.today().strftime('%Y-%m-%d')
    dt = datetime.today().strftime('%Y-%m-%d %H:%M:%S')

    if request.method == "GET":
        user = db.execute("SELECT * FROM person WHERE user_id=:id", id=session['user_id'])
        last_login = db.execute("SELECT login_time FROM login WHERE user_id=:id", id=session['user_id'])
        login_lasttime = '1900-01-01 00:00:00'
        print(last_login)
        if last_login:
            login_lasttime = last_login[0]['login_time']
        myGroups = db.execute("SELECT * FROM groups WHERE user_id=:id GROUP BY group_id", id=session['user_id'])
        myEvents = db.execute("SELECT * FROM events WHERE event_id IN (SELECT event_id FROM events_roster WHERE user_id=:id)", id=session['user_id'])
        myGivings = db.execute("SELECT SUM(amount) FROM givings WHERE date LIKE '2020%' and user_id=:id", id=session['user_id'])
        family = db.execute("SELECT * FROM family WHERE family_id IN (SELECT family_id FROM person WHERE user_id=:id)", id=session['user_id'])
        myspGivings = db.execute("SELECT SUM(amount) FROM givings WHERE date LIKE '2020%' and user_id IN (SELECT user_id FROM person WHERE family_id=:family_id and user_id <>:user_id)", family_id=family[0]['family_id'], user_id=session['user_id'])
        print(last_login)
        familyGivings = usd(myGivings[0]['SUM(amount)'] if myGivings[0]['SUM(amount)'] is not None else 0.0 + myspGivings[0]['SUM(amount)'] if myspGivings[0]['SUM(amount)'] is not None else 0.0)
        # posts = db.execute("SELECT * FROM posts WHERE group_id IN (SELECT group_id FROM groups WHERE user_id=:id)", id=session['user_id'])
        posts = db.execute("SELECT posts.sender, posts.content, posts.datetime, groups.group_name FROM posts JOIN groups ON posts.group_id = groups.group_id WHERE groups.user_id=:id ORDER BY posts.datetime DESC", id=session['user_id'])
        newposts = db.execute("SELECT COUNT(posts.content), groups.group_name FROM posts JOIN groups ON posts.group_id = groups.group_id WHERE groups.user_id=:id and posts.datetime >:last_login GROUP BY groups.group_id", id=session['user_id'], last_login=login_lasttime)
        post_group = []
        # post_count = []
        for group in myGroups:
            current = next((item for item in newposts if item['group_name'] == group['group_name']), None)
            if current is None:
                post_group.append({'group_name': group['group_name'], 'COUNT(posts.content)': 0})
            else:
                post_group.append(current)
        if last_login:
            db.execute("UPDATE login SET login_time=:login_time WHERE user_id=:user_id",
                        login_time=dt, user_id=session['user_id'])
        else:
            db.execute("INSERT INTO login (user_id, login_time) VALUES(?, ?)", session['user_id'], dt)

        return render_template("index.html", myGroups=myGroups, user=user[0]['first_name'], myEvents=myEvents, familyGivings=familyGivings, posts=posts, post_group=post_group)
    sender = request.form.get("sender")
    message = request.form.get("message")
    group = request.form.get("group")
    group_id = db.execute("SELECT group_id FROM groups WHERE group_name=:group_name", group_name=group)
    db.execute("INSERT INTO posts (sender, content, datetime, group_id) VALUES(?, ?, ?, ?)", sender, message, dt, group_id[0]['group_id'])
    return redirect("/")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # current date and time
    today = datetime.today().strftime('%Y-%m-%d')
    dt = datetime.today().strftime('%Y-%m-%d %H:%M:%S')

    session.clear()
    if request.method == "POST":
        if not request.form.get("username"):
            flash("Username is missing.")
            return render_template('login.html')
        elif not request.form.get("password"):
            flash("Password is missing.")
            return render_template('login.html')
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("invalid username and/or password")
            return render_template('login.html')
        session["user_id"] = rows[0]["id"]
        last_login = db.execute("SELECT * FROM login WHERE user_id=:id", id=session['user_id'])
        # if last_login:
        #     db.execute("UPDATE login SET login_time=:login_time WHERE user_id=:user_id",
        #                 login_time=dt, user_id=session['user_id'])
        # else:
        #     db.execute("INSERT INTO login (user_id, login_time) VALUES(?, ?)", session['user_id'], dt)
        return redirect("/")
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    # inputs, including username and pw, are required from register html page. if not, it will be null.
    firstName = request.form.get("firstname")
    lastName = request.form.get("lastname")
    gender = request.form.get("gender")
    birthday = request.form.get("birthday")
    phoneNo = request.form.get("phoneNo")
    email = request.form.get("email")
    spfirstName = request.form.get("spfirstname")
    splastName = request.form.get("splastname")
    spgender = request.form.get("spgender")
    spbirthday = request.form.get("spbirthday")
    address1 = request.form.get("address1")
    address2 = request.form.get("address2")
    city = request.form.get("city")
    state = request.form.get("state")
    zipcode = request.form.get("zipcode")

    # check whether there is record for the user before
    rows1 = db.execute("SELECT * FROM person WHERE first_name=:firstname and last_name=:lastname and gender=:gender and birthday=:birthday",
                        firstname=firstName, lastname=lastName, gender=gender, birthday=birthday)
    # check whether there is record for the spouse before
    rows2 = db.execute("SELECT * FROM person WHERE first_name=:firstname and last_name=:lastname and gender=:gender and birthday=:birthday",
                        firstname=spfirstName, lastname=splastName, gender=spgender, birthday=spbirthday)
    # if user record is found and user also has user_id, meaning the user has an account already, direct the user to log in.
    if len(rows1) == 1 and rows1[0]['user_id']:
        rows1user = db.execute("SELECT username FROM users WHERE id=:id", id=rows1[0]['user_id'])
        if rows1user[0]['username']:
            flash("You have registered before. Please go to Log In.")
            return render_template('register.html')
    # check whether the username has been used.
    username = request.form.get("username")
    rowsuser = db.execute("SELECT * FROM users WHERE username=:username",
                        username=username)
    if len(rowsuser) == 1:
        flash("This username already exists!")
        return render_template('register.html')
    # check if the passwords typed match with each other.
    pw = request.form.get("password")
    repw = request.form.get("confirmation")
    if pw != repw:
        flash("The passwords provided don't match!")
        return render_template('register.html')
    hashpw = generate_password_hash(pw)

    # if user record is found and no username is found, meaning there is record as a spouse before but no account set up for the user
    if len(rows1) == 1:
        familyID = rows1[0]['family_id']
        # use = db.execute("SELECT MAX(id) FROM users")
        # userID = use[0]['MAX(id)'] + 1
        userID = rows1[0]['user_id']
        # db.execute("UPDATE person SET user_id=:id, phone=:phone, email=:email WHERE first_name=:firstname and last_name=:lastname and gender=:gender and birthday=:birthday",
        #         id=userID, phone=phoneNo, email=email, firstname=firstName, lastname=lastName, gender=gender, birthday=birthday)
        db.execute("UPDATE users SET username=:username, hash=:hash WHERE id=:id",
                    username=username, hash=hashpw, id=userID)
        db.execute("UPDATE person SET phone=:phone, email=:email WHERE id=:id",
                    phone=phoneNo, email=email, id=userID)
    # else there is no record for the user
    else:
        fam = db.execute("SELECT MAX(family_id) FROM family")
        familyID = 1 if fam[0]['MAX(family_id)'] is None else fam[0]['MAX(family_id)'] + 1
        db.execute("INSERT INTO family (family_id, addr_street, addr2, city, zipcode, state) VALUES(?, ?, ?, ?, ?, ?)",
                    familyID, address1, address2, city, zipcode, state)
                    # familyID, address1 if address1 else '', address2 if address2 else '', city if city else '', zipcode if zipcode else '', state if state else '')
        db.execute("INSERT INTO person (first_name, last_name, gender, phone, email, birthday, family_id) VALUES(?, ?, ?, ?, ?, ?, ?)",
                firstName, lastName, gender, phoneNo, email, birthday,familyID)
        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hashpw)
    if len(rows2) == 0 and spfirstName and splastName and spgender and spbirthday:
        db.execute("INSERT INTO person (first_name, last_name, gender, birthday, family_id) VALUES(?, ?, ?, ?, ?)",
                spfirstName, splastName, spgender, spbirthday,familyID)
        db.execute("INSERT INTO users (username, hash) VALUES(NULL, NULL)")
    flash("You have registered an account. You may login now.")
    return redirect("/")




@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """user profile"""
    user = db.execute("SELECT * FROM users WHERE id=:id", id=session["user_id"])
    person = db.execute("SELECT * FROM person WHERE user_id=:id", id=session['user_id'])
    family = db.execute("SELECT * FROM family WHERE family_id IN (SELECT family_id FROM person WHERE user_id=:id)", id=session['user_id'])
    spouseInfo = db.execute("SELECT * FROM person WHERE family_id=:family_id and user_id <>:user_id", family_id=family[0]['family_id'], user_id=session['user_id'])
    print(spouseInfo)
    if not spouseInfo:
        spouse = {'first_name': '', 'last_name': '', 'gender': '', 'birthday': '', 'phone': '', 'email': ''}
    else:
        for key in spouseInfo[0]:
            if spouseInfo[0][key] is None:
                spouseInfo[0][key] = ''
        spouse = spouseInfo[0]
    if request.method == "GET":
        info = {**user[0], **person[0], **family[0]}
        return render_template("profile.html", info=info, spouse=spouse)
    # any changes will be updated in the database
    firstName = request.form.get("firstname")
    lastName = request.form.get("lastname")
    gender = request.form.get("gender")
    birthday = request.form.get("birthday")
    phoneNo = request.form.get("phoneNo")
    email = request.form.get("email")
    spfirstName = request.form.get("spfirstname")
    splastName = request.form.get("splastname")
    spgender = request.form.get("spgender")
    spbirthday = request.form.get("spbirthday")
    spphoneNo = request.form.get("spphoneNo")
    spemail = request.form.get("spemail")
    address1 = request.form.get("address1")
    address2 = request.form.get("address2")
    city = request.form.get("city")
    state = request.form.get("state")
    zipcode = request.form.get("zipcode")
    db.execute("UPDATE person SET first_name=:firstname, last_name=:lastname, gender=:gender, phone=:phone, email=:email, birthday=:birthday WHERE user_id=:id",
                firstname=firstName, lastname=lastName, gender=gender, phone=phoneNo, email=email, birthday=birthday, id=session['user_id'])
    db.execute("UPDATE person SET first_name=:firstname, last_name=:lastname, gender=:gender, phone=:phone, email=:email, birthday=:birthday WHERE family_id=:family_id and user_id <>:user_id",
            firstname=spfirstName, lastname=splastName, gender=spgender, phone=spphoneNo, email=spemail, birthday=spbirthday, family_id=family[0]['family_id'], user_id=session['user_id'])
    if not spouseInfo:
        db.execute("INSERT INTO person (first_name, last_name, gender, birthday, phone, email, family_id) VALUES(?, ?, ?, ?, ?, ?, ?)",
                spfirstName, splastName, spgender, spbirthday, spphoneNo, spemail, family[0]['family_id'])
        db.execute("INSERT INTO users (username, hash) VALUES(NULL, NULL)")
    flash("Information change is saved.")
    return redirect("/")

@app.route("/createGroup", methods=["POST"])
@login_required
def createGroup():
    groups = db.execute("SELECT DISTINCT group_id, group_name FROM groups")
    groupName = request.form.get("groupname")
    if groups:
        for group in groups:
            if groupName == group['group_name']:
                flash("Group name already exists. Please select another name!")
                return render_template("groups.html")
    description = request.form.get("description")
    if not groupName:
        flash("Please provide a name for the group you would like to create!")
        return render_template("groups.html")
    db.execute("INSERT INTO groups (group_name, description, user_id) VALUES(?, ?, ?)",
                groupName, description, session['user_id'])
    flash(f"Group '{groupName}' has been created.")
    return render_template("groups.html")

@app.route("/group", methods=["GET", "POST"])
@login_required
def group():
    groups = db.execute("SELECT DISTINCT group_id, group_name, description FROM groups")
    # myGroups = db.execute("SELECT * FROM groups WHERE user_id=:id", id=session['user_id'])
    if request.method == "GET":
        return render_template("groups.html", groups=groups)
    groupjoin = request.form.get("group")
    for group in groups:
        if group['group_name'] == groupjoin:
            group_id = group['group_id']
            break
    db.execute("INSERT INTO groups (group_id, group_name, user_id) VALUES(?, ?, ?)", group_id, groupjoin, session['user_id'])
    flash(f"You have successfully joined Group '{groupjoin}'.")
    return render_template("groups.html")

@app.route("/events", methods=["GET", "POST"])
@login_required
def events():
    # events = db.execute("SELECT DISTINCT subject FROM events WHERE event_id IN (SELECT event_id FROM events_roster WHERE user_id <>:id)", id=session['user_id'])
    events = db.execute("SELECT * FROM events WHERE status='active'")
    if request.method == "GET":
        return render_template("events.html", events=events)
    event = request.form.get("event")
    if not event:
        flash("Please choose an event from the list.")
        return render_template("events.html")
    eventsAttended = db.execute("SELECT * FROM events WHERE subject=:subject and event_id IN (SELECT event_id FROM events_roster WHERE user_id =:id)", subject=event, id=session['user_id'])
    if len(eventsAttended) != 0:
        flash(f"You have already joined the event '{event}'")
        return render_template("events.html")
    sel = db.execute("SELECT event_id FROM events WHERE subject=:subject", subject=event)
    db.execute("INSERT INTO events_roster (event_id, user_id) VALUES(?, ?)", sel[0]['event_id'], session['user_id'])
    flash(f"You have joined '{event}' successfully.")
    return render_template("events.html")

@app.route("/createEvent", methods=["POST"])
@login_required
def createEvent():
    today = datetime.today().strftime('%Y-%m-%d')
    dt = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    sender = request.form.get("sender")
    subject = request.form.get("subject")
    message = request.form.get("message")
    start = request.form.get("start")
    end = request.form.get("end")
    startDate = datetime.strptime(start, "%Y-%m-%d")
    endDate = datetime.strptime(end, "%Y-%m-%d")
    cnt = db.execute("SELECT * FROM events WHERE subject=:subject", subject=subject)
    if len(cnt) != 0:
        flash("This subject already exists. Please advise to another one.")
        return render_template("events.html")
    if startDate > endDate:
        flash("The starting date is after the end date.")
        return render_template("events.html")
    status = "active"
    if endDate < datetime.today():
        status = "inactive"
    db.execute("INSERT INTO events (sender, subject, message, sentDate, start, end, status) VALUES(?, ?, ?, ?, ?, ?, ?)",
            sender, subject, message, today, start, end, status)
    flash(f"The event '{subject}' has been created and the notification is pushed to all the members.")
    return render_template("events.html")

@app.route("/giving", methods=["GET", "POST"])
@login_required
def giving():
    today = datetime.today().strftime('%Y-%m-%d')
    dt = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    if request.method == "GET":
        return render_template("giving.html")
    amount = request.form.get("amount")
    db.execute("INSERT INTO givings (user_id, amount, date) VALUES(?, ?, ?)", session['user_id'], amount, today)
    flash("Your donation has been processed and highly appreciated!")
    return render_template("giving.html")

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)