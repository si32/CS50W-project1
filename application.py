import os
import requests

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

# Path to directory to save covers of books
app.config["IMAGE_UPLOADS"] = "C:\CS50W\project1\static\pictures\covers"


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


"""
    Класс Book, как объект со всеми необходимыми свойствами, чтобы запросить один раз из базы и пользоваться
    """


class Book:
    def __init__(self, book_id):
        self.book_id = book_id
        book = db.execute(
            "SELECT * FROM books WHERE book_id=:book_id", {"book_id": self.book_id}
        ).fetchone()
        self.isbn = book["isbn"]
        self.title = book["title"]
        self.author = book["author"]
        self.year = book["year"]

        # Check if we have the cover
        filename = str(self.book_id) + ".png"
        for file in os.scandir(app.config["IMAGE_UPLOADS"]):
            if file.is_file():
                if file.name == filename:
                    self.cover = "/static/pictures/covers/" + filename
                    # Check all files in the directory and then upload it from google if it need
                    break
        else:
            url = "https://www.googleapis.com/books/v1/volumes?q=isbn:" + str(self.isbn)
            res = requests.get(url)
            if res.status_code != 200:
                raise Exception("ERROR: API request unsuccessful.")
            data = res.json()
            cover_link = data["items"][0]["volumeInfo"]["imageLinks"]["thumbnail"]
            pic = requests.get(cover_link)
            # save the image
            path = os.path.join(app.config["IMAGE_UPLOADS"], filename)
            out = open(path, "wb")
            out.write(pic.content)
            out.close()
            self.cover = "/static/pictures/covers/" + filename


@app.route("/")
@login_required
def index():
    user_id = session.get("user_id")
    username = db.execute(
        "SELECT username FROM users WHERE user_id = :user_id", {"user_id": user_id}
    ).fetchone()

    # choose the 5 top rated books

    book_ids = [3, 4, 5, 6, 7]

    # create 5 top rated books objects
    books = []
    for book_id in book_ids:
        books.append(Book(book_id))
    return render_template("index.html", books=books, username=username[0])


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
    valid = db.execute(
        "SELECT * FROM books WHERE book_id=:book_id", {"book_id": book_id}
    ).fetchone()
    if valid is None:
        return errors("No such book")
    book = Book(book_id, db)

    return render_template("book.html", book=book)


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
    # Если результат поиска один, то сразу на сраницу книги, в противном случае на страницу с результатами поиска
    return render_template("search.html")


# for testing fiatures
@app.route("/test")
@login_required
def test():

    return errors("test")
