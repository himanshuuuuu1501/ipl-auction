from flask import Flask, render_template, request, redirect, session
import psycopg2
import os

app = Flask(__name__)
app.secret_key = "secret123"

DATABASE_URL = os.environ.get("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")

cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS players(
id SERIAL PRIMARY KEY,
name TEXT,
base_price INT,
highest_bid INT,
highest_bidder TEXT
)
""")

conn.commit()


cur.execute("SELECT COUNT(*) FROM players")
count = cur.fetchone()[0]

if count == 0:

    cur.execute("""
    INSERT INTO players (name, base_price, highest_bid, highest_bidder)
    VALUES
    ('Virat Kohli',100,100,'None'),
    ('Rohit Sharma',120,120,'None'),
    ('MS Dhoni',150,150,'None'),
    ('Hardik Pandya',110,110,'None'),
    ('KL Rahul',100,100,'None'),
    ('Jasprit Bumrah',130,130,'None')
    """)
    
    conn.commit()

# LOGIN PAGE
@app.route("/")
def login():
    return render_template("login.html")


# HANDLE LOGIN
@app.route("/enter", methods=["POST"])
def enter():

    username = request.form["username"]
    team = request.form["team"]

    session["username"] = username
    session["team"] = team

    return redirect("/dashboard")


@app.route("/dashboard")
def dashboard():

    if "username" not in session:
        return redirect("/")

    cur = conn.cursor()
    cur.execute("SELECT * FROM players")
    players = cur.fetchall()

    return render_template(
        "dashboard.html",
        username=session["username"],
        team=session["team"],
        players=players
    )


if __name__ == "__main__":
    app.run()


