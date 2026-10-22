from flask import Flask, make_response

app = Flask(__name__)


@app.post("/login")
def login():
    response = make_response("ok")
    response.set_cookie("session", new_session_id(), secure=True, httponly=True, samesite="Strict")
    return response
