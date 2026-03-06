from flask import Flask, render_template, request, redirect, session
import psycopg2
import os

app = Flask(__name__)
app.secret_key = "secret123"

DATABASE_URL = os.environ.get("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")


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


# DASHBOARD
@app.route("/dashboard")
def dashboard():

    if "username" not in session:
        return redirect("/")

    return render_template(
        "dashboard.html",
        username=session["username"],
        team=session["team"]
    )


if __name__ == "__main__":
    app.run()
