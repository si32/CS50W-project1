import os
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# database engine object from SQLAlchemy that manages connections to the database
# DATABASE_URL is an environment variable that indicates where the database lives
engine = create_engine(os.getenv("DATABASE_URL"))
# Placeholders don't work without session
db = scoped_session(sessionmaker(bind=engine))

# read csv file
f = open("books.csv")
reader = csv.reader(f)

# read csv and insert data to db
for isbn, title, author, year in reader:
    db.execute(
        "INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
        {"isbn": isbn, "title": title, "author": author, "year": int(year)},
    )

# transactions are assumed, so close the transaction finished
db.commit()
