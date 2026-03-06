from flask import Flask, render_template, request, redirect, session, jsonify
import psycopg2
import os
import time

app = Flask(__name__)
app.secret_key = "ipl_auction_secret_2024"

DATABASE_URL = os.environ.get("DATABASE_URL")
AUCTIONEER_PASSWORD = "iplauctioneer2024"

def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS auction_state")
    cur.execute("DROP TABLE IF EXISTS players")

    cur.execute("""
        CREATE TABLE players (
            id           SERIAL PRIMARY KEY,
            name         TEXT    NOT NULL,
            role         TEXT    NOT NULL,
            base_price   FLOAT   NOT NULL,
            current_bid  FLOAT   NOT NULL,
            current_team TEXT    DEFAULT 'Unsold',
            nationality  TEXT    DEFAULT 'Indian',
            runs         INTEGER DEFAULT 0,
            wickets      INTEGER DEFAULT 0,
            strike_rate  FLOAT   DEFAULT 0,
            bowling_avg  FLOAT   DEFAULT 0,
            matches      INTEGER DEFAULT 0,
            status       TEXT    DEFAULT 'pending'
        )
    """)

    # auction_state holds which player is currently live + timer deadline
    cur.execute("""
        CREATE TABLE auction_state (
            id            INTEGER PRIMARY KEY DEFAULT 1,
            active_player INTEGER DEFAULT NULL,
            timer_end     FLOAT   DEFAULT NULL,
            is_active     BOOLEAN DEFAULT FALSE
        )
    """)
    cur.execute("INSERT INTO auction_state (id) VALUES (1)")

    players = [
        ("Virat Kohli",      "Batsman",      20.0, 20.0, "Unsold", "Indian",     7263, 4,   130.4, 92.0, 237),
        ("Rohit Sharma",     "Batsman",      16.0, 16.0, "Unsold", "Indian",     6211, 15,  130.1, 32.0, 243),
        ("MS Dhoni",         "Wicketkeeper", 12.0, 12.0, "Unsold", "Indian",     5082, 0,   137.0,  0.0, 264),
        ("Hardik Pandya",    "All-Rounder",  15.0, 15.0, "Unsold", "Indian",     2309, 53,  145.2, 30.3, 115),
        ("KL Rahul",         "Wicketkeeper", 17.0, 17.0, "Unsold", "Indian",     4163, 0,   134.8,  0.0, 132),
        ("Jasprit Bumrah",   "Bowler",       18.0, 18.0, "Unsold", "Indian",       56, 165, 100.0, 23.1, 135),
        ("Shubman Gill",     "Batsman",      13.0, 13.0, "Unsold", "Indian",     2687, 0,   132.3,  0.0,  89),
        ("Suryakumar Yadav", "Batsman",      16.0, 16.0, "Unsold", "Indian",     3414, 0,   166.7,  0.0, 123),
        ("Ravindra Jadeja",  "All-Rounder",  14.0, 14.0, "Unsold", "Indian",     2692, 132, 127.5, 29.5, 236),
        ("Pat Cummins",      "Bowler",       20.0, 20.0, "Unsold", "Australian",  156, 95,   98.7, 26.2,  75),
        ("Jos Buttler",      "Wicketkeeper", 15.0, 15.0, "Unsold", "English",    3582, 0,   149.4,  0.0, 104),
        ("Rashid Khan",      "All-Rounder",  18.0, 18.0, "Unsold", "Afghan",      316, 112, 110.5, 20.9,  92),
    ]
    cur.executemany("""
        INSERT INTO players
            (name, role, base_price, current_bid, current_team, nationality,
             runs, wickets, strike_rate, bowling_avg, matches)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, players)

    conn.commit()
    cur.close()
    conn.close()

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_auction_state(cur):
    cur.execute("SELECT active_player, timer_end, is_active FROM auction_state WHERE id=1")
    return cur.fetchone()

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def login():
    return render_template("login.html")

@app.route("/enter", methods=["POST"])
def enter():
    session["username"] = request.form["username"]
    session["team"]     = request.form["team"]
    return redirect("/auction")

# ── AUCTIONEER ────────────────────────────────────────────────────────────────

@app.route("/auctioneer")
def auctioneer_login():
    return render_template("auctioneer_login.html")

@app.route("/auctioneer/enter", methods=["POST"])
def auctioneer_enter():
    if request.form.get("password") == AUCTIONEER_PASSWORD:
        session["is_auctioneer"] = True
        return redirect("/auctioneer/panel")
    return render_template("auctioneer_login.html", error="Wrong password!")

@app.route("/auctioneer/panel")
def auctioneer_panel():
    if not session.get("is_auctioneer"):
        return redirect("/auctioneer")
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM players ORDER BY id")
    players = cur.fetchall()
    state = get_auction_state(cur)
    cur.close()
    conn.close()
    return render_template("auctioneer.html", players=players, state=state, now=time.time())

@app.route("/auctioneer/start/<int:player_id>", methods=["POST"])
def start_auction(player_id):
    if not session.get("is_auctioneer"):
        return redirect("/auctioneer")
    conn = get_conn()
    cur  = conn.cursor()
    # Reset player bid to base price
    cur.execute("UPDATE players SET current_team='Unsold', status='live', current_bid=base_price WHERE id=%s", (player_id,))
    # Set all others back to pending if they were live
    cur.execute("UPDATE players SET status='pending' WHERE id!=%s AND status='live'", (player_id,))
    timer_end = time.time() + 10
    cur.execute("UPDATE auction_state SET active_player=%s, timer_end=%s, is_active=TRUE WHERE id=1",
                (player_id, timer_end))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/auctioneer/panel")

@app.route("/auctioneer/sold", methods=["POST"])
def sell_player():
    if not session.get("is_auctioneer"):
        return redirect("/auctioneer")
    conn = get_conn()
    cur  = conn.cursor()
    state = get_auction_state(cur)
    if state and state[2]:  # is_active
        cur.execute("UPDATE players SET status='sold' WHERE id=%s", (state[0],))
        cur.execute("UPDATE auction_state SET is_active=FALSE, active_player=NULL, timer_end=NULL WHERE id=1")
        conn.commit()
    cur.close()
    conn.close()
    return redirect("/auctioneer/panel")

@app.route("/auctioneer/unsold", methods=["POST"])
def mark_unsold():
    if not session.get("is_auctioneer"):
        return redirect("/auctioneer")
    conn = get_conn()
    cur  = conn.cursor()
    state = get_auction_state(cur)
    if state and state[2]:
        cur.execute("UPDATE players SET status='unsold', current_team='Unsold' WHERE id=%s", (state[0],))
        cur.execute("UPDATE auction_state SET is_active=FALSE, active_player=NULL, timer_end=NULL WHERE id=1")
        conn.commit()
    cur.close()
    conn.close()
    return redirect("/auctioneer/panel")

@app.route("/auctioneer/reset", methods=["POST"])
def reset_auction():
    if not session.get("is_auctioneer"):
        return redirect("/auctioneer")
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("UPDATE players SET current_bid=base_price, current_team='Unsold', status='pending'")
    cur.execute("UPDATE auction_state SET is_active=FALSE, active_player=NULL, timer_end=NULL WHERE id=1")
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/auctioneer/panel")

# ── BIDDING ───────────────────────────────────────────────────────────────────

@app.route("/auction")
def auction():
    if "username" not in session:
        return redirect("/")
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM players ORDER BY id")
    players = cur.fetchall()
    state = get_auction_state(cur)
    cur.close()
    conn.close()
    return render_template("index.html",
                           players=players,
                           state=state,
                           now=time.time(),
                           username=session["username"],
                           team=session["team"])

@app.route("/bid", methods=["POST"])
def bid():
    if "username" not in session:
        return redirect("/")
    player_id = int(request.form["player_id"])
    # Input is in Crores, store as Crores (float)
    new_bid   = float(request.form["bid"])
    bidder    = session["team"]

    conn = get_conn()
    cur  = conn.cursor()

    # Check auction is live for this player and timer hasn't expired
    state = get_auction_state(cur)
    if not state or not state[2] or state[0] != player_id:
        cur.close(); conn.close()
        return redirect("/auction?status=notlive")

    if state[1] and time.time() > state[1]:
        cur.close(); conn.close()
        return redirect("/auction?status=expired")

    cur.execute("SELECT current_bid FROM players WHERE id=%s", (player_id,))
    row = cur.fetchone()
    if row and new_bid > float(row[0]):
        # Reset timer by 30s on each new bid
        new_timer = time.time() + 10
        cur.execute("UPDATE players SET current_bid=%s, current_team=%s WHERE id=%s",
                    (new_bid, bidder, player_id))
        cur.execute("UPDATE auction_state SET timer_end=%s WHERE id=1", (new_timer,))
        conn.commit()
        cur.close(); conn.close()
        return redirect("/auction?status=success")

    cur.close(); conn.close()
    return redirect("/auction?status=low")

# ── DASHBOARD ─────────────────────────────────────────────────────────────────

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
        FROM players WHERE current_team != 'Unsold'
        GROUP BY current_team ORDER BY total DESC
    """)
    team_stats = cur.fetchall()
    cur.close(); conn.close()
    return render_template("dashboard.html",
                           players=players,
                           team_stats=team_stats,
                           username=session["username"],
                           team=session["team"])

# ── API (for live polling) ────────────────────────────────────────────────────

@app.route("/api/state")
def api_state():
    conn = get_conn()
    cur  = conn.cursor()
    state = get_auction_state(cur)
    player = None
    if state and state[0]:
        cur.execute("SELECT id,name,role,current_bid,current_team,base_price FROM players WHERE id=%s", (state[0],))
        p = cur.fetchone()
        if p:
            player = {"id":p[0],"name":p[1],"role":p[2],"bid":float(p[3]),"team":p[4],"base":float(p[5])}
    cur.close(); conn.close()
    return jsonify({
        "is_active": state[2] if state else False,
        "timer_end": state[1] if state else None,
        "server_time": time.time(),
        "player": player
    })

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# Run init_db once after the server is ready, not at import time
_db_initialized = False

@app.before_request
def setup():
    global _db_initialized
    if not _db_initialized:
        init_db()
        _db_initialized = True

if __name__ == "__main__":
    app.run(debug=True)
