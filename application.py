import os

from flask import Flask, session, render_template, request, redirect
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import errors, login_required

app = Flask(__name__)
# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return errors("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return errors("must provide password", 403)

        # Query database for username
        username = request.form.get("username")
        rows = db.execute(
            "SELECT * FROM users WHERE username = :username", {"username": username}
        ).fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash_password"], request.form.get("password")
        ):
            return errors("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["user_id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return render_template("/logout.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return errors("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return errors("must provide password", 403)

        # Ensure confirmed password was submitted
        elif not request.form.get("confirmation"):
            return errors("must confirm password", 403)

        # Ensure password and confirmed password are equal
        elif request.form.get("password") != request.form.get("confirmation"):
            return errors("password and confirmed password must be equal!", 403)

        # Hash password
        password = request.form.get("password")
        hash_password = generate_password_hash(
            password, method="pbkdf2:sha256", salt_length=8
        )

        # Try to find user (user_id) in db
        username = request.form.get("username")
        result = db.execute(
            "SELECT * FROM users WHERE username = :username", {"username": username}
        ).fetchall()

        if not result:
            db.execute(
                "INSERT INTO users (username, hash_password) VALUES (:username, :hash_password)",
                {"username": username, "hash_password": hash_password},
            )
            # Надо закомитить, а то не сохраняет в базу
            db.commit()
            # log in registred user automaticly
            rows = db.execute(
                "SELECT * FROM users WHERE username = :username", {"username": username}
            ).fetchall()
            session["user_id"] = rows[0]["user_id"]

            # Redirect user to home page
            return redirect("/")
        else:
            return errors("HEY! The User with this name is already exist!")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/")
@login_required
def index():
    user_id = session.get("user_id")
    username = db.execute(
        "SELECT username FROM users WHERE user_id = :user_id", {"user_id": user_id}
    ).fetchone()
    return render_template("index.html", text=user_id, username=username[0])


# Go to individual book page
@app.route("/books")
@login_required
def books():
    return redirect("/")


# Individual book page
@app.route("/books/<int:book_id>")
@login_required
def book(book_id):
    # Make sure book exist
    book = db.execute(
        "SELECT * FROM books WHERE book_id=:book_id", {"book_id": book_id}
    ).fetchone()
    if book is None:
        return errors("No such book")


# Go to personal user page
@app.route("/users")
@login_required
def users():
    user_id = session.get("user_id")
    return redirect(f"/users/{user_id}")


# Personal user page
@app.route("/users/<int:user_id>")
@login_required
def user(user_id):
    # Make sure user exist
    user = db.execute(
        "SELECT * FROM users WHERE user_id=:user_id", {"user_id": user_id}
    ).fetchone()
    if user is None:
        return errors("No such user")


# Search results
@app.route("/search")
@login_required
def search():

    return render_template("search.html")
