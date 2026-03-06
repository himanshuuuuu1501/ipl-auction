from flask import Flask, render_template, request
import psycopg2
import os

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

# ---- CREATE TABLE IF NOT EXISTS ----
cur.execute("""
CREATE TABLE IF NOT EXISTS players (
id SERIAL PRIMARY KEY,
name TEXT,
base_price INT,
highest_bid INT,
highest_bidder TEXT
)
""")

conn.commit()

# ---- INSERT PLAYERS IF TABLE EMPTY ----
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


@app.route("/")
def home():
    cur = conn.cursor()
    cur.execute("SELECT * FROM players ORDER BY id")
    players = cur.fetchall()
    return render_template("index.html", players=players)


@app.route("/bid", methods=["POST"])
def bid():

    player_id = request.form["player_id"]
    bidder = request.form["bidder"]
    bid = int(request.form["bid"])

    cur = conn.cursor()

    cur.execute(
        "SELECT base_price, highest_bid FROM players WHERE id=%s",
        (player_id,)
    )

    base_price, highest_bid = cur.fetchone()

    if bid < base_price:
        return "Bid lower than base price"

    if bid <= highest_bid:
        return "Someone already bid higher"

    cur.execute(
        "UPDATE players SET highest_bid=%s, highest_bidder=%s WHERE id=%s",
        (bid, bidder, player_id)
    )

    conn.commit()

    return "Bid accepted <br><a href='/'>Back</a>"


if __name__ == "__main__":
    app.run()