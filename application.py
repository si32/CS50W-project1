import os
import requests

from flask import Flask, session, render_template, request, redirect, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

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

""" different help functions"""
# return username
def get_username():
    user_id = session.get("user_id")
    username = db.execute(
        "SELECT username FROM users WHERE user_id = :user_id", {"user_id": user_id}
    ).fetchone()
    return username.username


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

        # avg rating and count reviews
        review_count = db.execute(
            "SELECT COUNT(review) FROM reviews WHERE book_id=:book_id",
            {"book_id": book_id},
        ).fetchone()
        average_rating = db.execute(
            "SELECT ROUND(AVG(rating), 2) FROM reviews WHERE book_id=:book_id",
            {"book_id": book_id},
        ).fetchone()
        self.review_count = review_count[0]
        self.average_rating = str(average_rating[0])

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
            # Check if cover_link exist
            if len(data) < 3:
                self.cover = "/static/pictures/bookreviewer.png"
            else:
                cover_link = data["items"][0]["volumeInfo"]["imageLinks"]["thumbnail"]

                pic = requests.get(cover_link)
                # save the image
                path = os.path.join(app.config["IMAGE_UPLOADS"], filename)
                out = open(path, "wb")
                out.write(pic.content)
                out.close()
                self.cover = "/static/pictures/covers/" + filename


"""
    Класс Review, как объект со всеми необходимыми свойствами, чтобы запросить один раз из базы и пользоваться
    """


class Review:
    def __init__(self, rev_id):
        self.rev_id = rev_id
        review = db.execute(
            "SELECT * FROM reviews WHERE rev_id=:rev_id", {"rev_id": self.rev_id}
        ).fetchone()
        self.user_id = review["user_id"]
        self.book_id = review["book_id"]
        self.rev_data = review["rev_data"]
        self.review = review["review"]
        self.rating = review["rating"]
        user = db.execute(
            "SELECT username FROM users WHERE user_id=:user_id",
            {"user_id": self.user_id},
        ).fetchone()
        self.username = user.username


"""
Class for Goodreads reviews
"""


class GRinfo:
    def __init__(self, isbns):
        res = requests.get(
            "https://www.goodreads.com/book/review_counts.json",
            params={"key": "45htbBdXBx9GPVgNEW9fQ", "isbns": isbns},
        )
        if res.status_code != 200:
            raise Exception("ERROR: API request unsuccessful.")
        data = res.json()
        self.work_ratings_count = data["books"][0]["work_ratings_count"]
        self.average_rating = data["books"][0]["average_rating"]


@app.route("/")
@login_required
def index():
    username = get_username()

    # choose the 5 top rated books
    # надо сделать супер скл запрос
    # book_ids_sql = db.execute("SELECT book_id FROM reviews WHERE GROUP BY (rating AND COUNT(reviews)) LIMIT 5")
    # book_ids = может надо будет составить списо ид, надо смотреть что вернет запрос
    book_ids_res = db.execute(
        "SELECT book_id FROM reviews GROUP BY book_id HAVING COUNT(*) > 0 ORDER BY AVG(rating) DESC LIMIT 5"
    ).fetchall()
    book_ids = []
    for i in range(5):
        book_ids.append(book_ids_res[i][0])
    books = []
    for book_id in book_ids:
        books.append(Book(book_id))

    # TOP 5 latest reviewed
    # SELECT rev_id FROM reviews GROUP BU/sort BY rev_data LIMIT 5
    # или сделат просто и вывести еще и ласт ревьед и все. никаких сортировок
    # или прочитать в интернете как делать сортировки. Может это через ява скирпт и тогда отложить на потом точно.

    return render_template("index.html", books=books, username=username)


# Go to individual book page
@app.route("/books")
@login_required
def books():
    return redirect("/")


# Individual book page
@app.route("/books/<int:book_id>")
@login_required
def book(book_id):
    # get username
    username = get_username()
    # Make sure book exist
    valid = db.execute(
        "SELECT * FROM books WHERE book_id=:book_id", {"book_id": book_id}
    ).fetchone()
    if valid is None:
        return errors("No such book")
    book = Book(book_id)

    # choose all reviews from db
    rev_ids = db.execute(
        "SELECT rev_id FROM reviews WHERE book_id=:book_id ORDER BY rev_data DESC",
        {"book_id": book.book_id},
    ).fetchall()
    # check if user had already left review
    user_id = session.get("user_id")
    # aql order by, чтобы отсортировать список рквью по дате и передать в темплейт
    user_rev_id = db.execute(
        "SELECT rev_id FROM reviews WHERE user_id=:user_id AND book_id=:book_id",
        {"user_id": user_id, "book_id": book_id},
    ).fetchone()
    if user_rev_id:
        # передать в темплейт, что можно отображать поле для ревбю
        already_left_rev = "True"
        user_review = Review(user_rev_id.rev_id)
    else:
        already_left_rev = "False"
        user_review = None
    # create all reviews objects for the book
    reviews = []
    for rev_id in rev_ids:
        reviews.append(Review(rev_id.rev_id))

    # Make GRinfo class object to take iformation from goodreads API
    gr_info = GRinfo(book.isbn)

    # отсортировать список рквью по дате а потом передавать
    # или сортировать скл. Или в скл вывести тупл и сортировать тупл методами питона

    return render_template(
        "book.html",
        username=username,
        book=book,
        already_left_rev=already_left_rev,
        user_review=user_review,
        reviews=reviews,
        gr_info=gr_info,
    )


# if user leaves a reiew
@app.route("/submit_review", methods=["GET", "POST"])
@login_required
def submit_review():
    if request.method == "GET":
        return errors("Not alloyed method", 405)
    # получить всю необходимую инфо и загрузить в базу данных
    if request.method == "POST":
        # Ensure rating was submitted, user can to not submit review itself
        if not request.form.get("rating"):
            return errors("must provide rating", 403)

        user_id = session.get("user_id")
        book_id = request.form.get("hidden_book_id")
        rev_data = datetime.today().strftime("%d.%m.%Y")
        review = request.form.get("message")
        rating = request.form.get("rating")

        # # Chech if user has already left comment
        user_rev_id = db.execute(
            "SELECT user_id FROM reviews WHERE user_id=:user_id AND book_id=:book_id",
            {"user_id": user_id, "book_id": book_id},
        ).fetchone()
        if user_rev_id == None:
            db.execute(
                "INSERT INTO reviews (user_id, book_id, rev_data, review, rating) VALUES (:user_id, :book_id, :rev_data, :review, :rating)",
                {
                    "user_id": user_id,
                    "book_id": book_id,
                    "rev_data": rev_data,
                    "review": review,
                    "rating": rating,
                },
            )
            db.commit()
    return redirect(f"/books/{book_id}")


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
    else:
        username = user["username"]
        return render_template("user.html", user_id=user_id, username=username)


# for testing fiatures
@app.route("/test")
@login_required
def test():
    isbn = "9781632168146"
    gr_info = GRinfo(isbn)
    return errors(gr_info)


# make my own API
@app.route("/api/<isbn>")
@login_required
def api(isbn):
    # Make sure book exist
    book = db.execute("SELECT * FROM books WHERE isbn=:isbn", {"isbn": isbn}).fetchone()
    if book is None:
        return jsonify({"error": "No such book"}), 404
    else:
        review_count = db.execute(
            "SELECT COUNT(review) FROM reviews WHERE book_id=:book_id",
            {"book_id": book["book_id"]},
        ).fetchone()
        average_score = db.execute(
            "SELECT ROUND(AVG(rating), 2) FROM reviews WHERE book_id=:book_id",
            {"book_id": book["book_id"]},
        ).fetchone()

        return jsonify(
            {
                "title": book["title"],
                "author": book["author"],
                "year": book["year"],
                "isbn": book["isbn"],
                "review_count": review_count[0],
                "average_score": str(average_score[0]),
            }
        )


# Search results
@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    # Если результат поиска один, то сразу на сраницу книги,
    # в противном случае на страницу с результатами поиска
    if request.method == "GET":
        return errors("Not alloyed method", 405)
    # получить всю необходимую инфо и загрузить в базу данных
    if request.method == "POST":
        # Do something if query is exist
        if request.form.get("query"):
            query = request.form.get("query")
            # ask the database
            squery = "%" + str(query) + "%"
            results = db.execute(
                "SELECT * FROM books WHERE isbn LIKE :squery OR title LIKE :squery OR author LIKE :squery",
                {"squery": squery},
            ).fetchall()
    if not results:
        return errors("Sorry, we didn't find anything!")
    else:
        return render_template("search.html", results=results)
