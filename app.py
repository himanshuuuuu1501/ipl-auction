from flask import Flask, render_template, request, redirect, session, jsonify
import psycopg2
import os

app = Flask(__name__)
app.secret_key = "ipl_auction_secret_2024"

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Force drop old table so stale string columns are gone
    cur.execute("DROP TABLE IF EXISTS players")
    cur.execute("""
        CREATE TABLE players (
            id           SERIAL PRIMARY KEY,
            name         TEXT    NOT NULL,
            role         TEXT    NOT NULL,
            base_price   BIGINT  NOT NULL,
            current_bid  BIGINT  NOT NULL,
            current_team TEXT    DEFAULT 'Unsold',
            nationality  TEXT    DEFAULT 'Indian',
            runs         INTEGER DEFAULT 0,
            wickets      INTEGER DEFAULT 0,
            strike_rate  FLOAT   DEFAULT 0,
            bowling_avg  FLOAT   DEFAULT 0,
            matches      INTEGER DEFAULT 0,
            image_url    TEXT    DEFAULT ''
        )
    """)

    players = [
        ("Virat Kohli",      "Batsman",      200000000, 200000000, "Unsold", "Indian",     7263, 4,   130.4, 92.0, 237, ""),
        ("Rohit Sharma",     "Batsman",      160000000, 160000000, "Unsold", "Indian",     6211, 15,  130.1, 32.0, 243, ""),
        ("MS Dhoni",         "Wicketkeeper", 120000000, 120000000, "Unsold", "Indian",     5082, 0,   137.0,  0.0, 264, ""),
        ("Hardik Pandya",    "All-Rounder",  150000000, 150000000, "Unsold", "Indian",     2309, 53,  145.2, 30.3, 115, ""),
        ("KL Rahul",         "Wicketkeeper", 170000000, 170000000, "Unsold", "Indian",     4163, 0,   134.8,  0.0, 132, ""),
        ("Jasprit Bumrah",   "Bowler",       180000000, 180000000, "Unsold", "Indian",       56, 165, 100.0, 23.1, 135, ""),
        ("Shubman Gill",     "Batsman",      130000000, 130000000, "Unsold", "Indian",     2687, 0,   132.3,  0.0,  89, ""),
        ("Suryakumar Yadav", "Batsman",      160000000, 160000000, "Unsold", "Indian",     3414, 0,   166.7,  0.0, 123, ""),
        ("Ravindra Jadeja",  "All-Rounder",  140000000, 140000000, "Unsold", "Indian",     2692, 132, 127.5, 29.5, 236, ""),
        ("Pat Cummins",      "Bowler",       200000000, 200000000, "Unsold", "Australian",  156, 95,   98.7, 26.2,  75, ""),
        ("Jos Buttler",      "Wicketkeeper", 150000000, 150000000, "Unsold", "English",    3582, 0,   149.4,  0.0, 104, ""),
        ("Rashid Khan",      "All-Rounder",  180000000, 180000000, "Unsold", "Afghan",      316, 112, 110.5, 20.9,  92, ""),
    ]
    cur.executemany("""
        INSERT INTO players
            (name, role, base_price, current_bid, current_team, nationality,
             runs, wickets, strike_rate, bowling_avg, matches, image_url)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, players)

    conn.commit()
    cur.close()
    conn.close()

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def login():
    return render_template("login.html")

@app.route("/enter", methods=["POST"])
def enter():
    session["username"] = request.form["username"]
    session["team"]     = request.form["team"]
    return redirect("/auction")

@app.route("/auction")
def auction():
    if "username" not in session:
        return redirect("/")
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM players ORDER BY id")
    players = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("index.html",
                           players=players,
                           username=session["username"],
                           team=session["team"])

@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect("/")
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM players ORDER BY id")
    players = cur.fetchall()
    cur.execute("""
        SELECT current_team, COUNT(*) as cnt, SUM(current_bid) as total
        FROM players
        WHERE current_team != 'Unsold'
        GROUP BY current_team
        ORDER BY total DESC
    """)
    team_stats = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("dashboard.html",
                           players=players,
                           team_stats=team_stats,
                           username=session["username"],
                           team=session["team"])

@app.route("/bid", methods=["POST"])
def bid():
    if "username" not in session:
        return redirect("/")
    player_id = int(request.form["player_id"])
    new_bid   = int(request.form["bid"])
    bidder    = session["team"]

    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("SELECT current_bid FROM players WHERE id=%s", (player_id,))
    row = cur.fetchone()
    if row and new_bid > int(row[0]):
        cur.execute(
            "UPDATE players SET current_bid=%s, current_team=%s WHERE id=%s",
            (new_bid, bidder, player_id)
        )
        conn.commit()
    cur.close()
    conn.close()
    return redirect("/auction")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/api/players")
def api_players():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("SELECT id, name, role, current_bid, current_team FROM players ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"id":r[0],"name":r[1],"role":r[2],"bid":int(r[3]),"team":r[4]} for r in rows])

# Runs at import time so gunicorn triggers it on every deploy
init_db()

if __name__ == "__main__":
    app.run(debug=True)
