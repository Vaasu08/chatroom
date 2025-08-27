from flask import Flask, session, request, render_template, redirect, url_for
from string import ascii_uppercase
import random
from flask_socketio import SocketIO, join_room, leave_room, send
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "abcdefghijk"

# Allow all origins for deployment
socketio = SocketIO(app, cors_allowed_origins="*")

rooms = {}

def generate_unique_code(length=4):
    while True:
        code = ''.join(random.choice(ascii_uppercase) for _ in range(length))
        if code not in rooms:
            return code

@app.route("/", methods=["GET", "POST"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("home.html", error="Please enter a name", code=code, name=name)
        if join and not code:
            return render_template("home.html", error="Please enter a room code", code=code, name=name)

        if create:
            room = generate_unique_code()
            rooms[room] = {"members": 0, "messages": []}
        else:
            room = code
            if room not in rooms:
                return render_template("home.html", error="Room does not exist", code=code, name=name)

        session["name"] = name
        session["room"] = room
        return redirect(url_for("room"))
    return render_template("home.html")

@app.route("/room")
def room():
    room = session.get("room")
    name = session.get("name")
    if not room or not name or room not in rooms:
        return redirect(url_for("home"))
    return render_template("room.html", code=room, messages=rooms[room]["messages"], name=name)

# ---------- Socket.IO events ----------

@socketio.on("connect")
def connect(auth):
    name = auth.get("name")
    room = auth.get("room")
    if not name or not room or room not in rooms:
        return False  # reject connection
    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    # We don't have session info here, so we rely on previous join to set room/name
    # If you want, you can track connected users in a dict
    print("A user disconnected")  # optional for debugging

@socketio.on("message")
def handle_message(data):
    name = data.get("name")
    room = data.get("room")
    msg = data.get("data")
    if not room or room not in rooms or not name or not msg:
        return
    content = {"name": name, "message": msg}
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{name} said: {msg}")

# ---------- Run ----------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
