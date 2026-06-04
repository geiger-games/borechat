import requests, time, threading
import tkinter as tk

room_ids = {
    "#general": "!tHofmdIslJQWtrRTVb:matrix.org",
    "#linux": "!anHvnEaFeEgyfqqsLu:matrix.org",
    "#gaming": "!hZkGxuwhBJdjZqAnQJ:matrix.org"
}

current_room = "#general"

messages = []
clients = []
dirty = threading.Event()
USER = input("Username (@user:example.org): ")
PASSWORD = input("Password: ")
HOME_SERVER = input("Homeserver (Leave empty for matrix.org): ")
if HOME_SERVER == "":
    HOME_SERVER = "matrix.org"
sync_token = ""

win = tk.Tk()
win.title("Borechat")
win.geometry("1080x720")

chat = tk.Text(win)
chat.pack(fill="both", expand=True)

entry = tk.Entry(win)
entry.pack(fill="x")

r = requests.post(
    f"https://{HOME_SERVER}/_matrix/client/v3/login",
    json={
        "type": "m.login.password",
        "identifier": {
            "type": "m.id.user",
            "user": USER
        },
        "password": PASSWORD
    }
)

data = r.json()
token = data["access_token"]

def recv_messages():
    global sync_token, room_ids, current_room

    while True:
        params = {
            "timeout": 30000
        }

        if sync_token:
            params["since"] = sync_token

        r = requests.get(
            f"https://{HOME_SERVER}/_matrix/client/v3/sync",
            headers={
                "Authorization": f"Bearer {token}"
            },
            params=params
        )

        data = r.json()
        sync_token = data["next_batch"]

        rooms = data.get("rooms", {}).get("join", {})

        for room, room_data in rooms.items():
            if room != room_ids[current_room]:
                continue

            for event in room_data.get("timeline", {}).get("events", []):
                if event.get("type") != "m.room.message":
                    continue

                sender = event.get("sender")
                body = event.get("content", {}).get("body", "")

                messages.append(f"{sender}: {body}")
                dirty.set()

def load_history(room_id):
    r = requests.get(
        f"https://{HOME_SERVER}/_matrix/client/v3/rooms/{room_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "dir": "b",
            "limit": 100
        }
    )

    data = r.json()

    msgs = []
    for event in data.get("chunk", []):
        if event.get("type") == "m.room.message":
            sender = event["sender"]
            body = event["content"]["body"]
            msgs.append(f"{sender}: {body}")

            dirty.set()

    return list(reversed(msgs))

def send(event=None):
    global current_room, room_ids, entry, messages

    msg = entry.get()

    if msg == "/quit":
        exit()
    elif msg == "/help":
        messages.extend(["/join - joins and adds you to a Borechat room", "/rooms - shows all available Borechat rooms"])
    elif msg == "/rooms":
        messages.append(" ".join(list(room_ids.keys())))
    elif msg.startswith("/join"):
        current_room = msg.split(" ")[1]
        requests.post(
            f"https://{HOME_SERVER}/_matrix/client/v3/rooms/{room_ids[current_room]}/join",
            headers={
                "Authorization": f"Bearer {token}"
            }
        )
        messages.clear()
        messages.extend(load_history(room_ids[current_room]))
    else:
        sendToRoom(msg)
    
    entry.delete(0, "end")

    dirty.set()

def sendToRoom(msg):
    global room_ids, current_room, token, entry
    url = f"https://{HOME_SERVER}/_matrix/client/v3/rooms/{room_ids[current_room]}/send/m.room.message/{int(time.time())}"

    r = requests.put(
        url,
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "msgtype": "m.text",
            "body": msg
        }
    )

    return r.json()

entry.bind("<Return>", send)

def render_chat():
    chat.config(state="normal")
    chat.delete("1.0", "end")
    chat.insert("end", "\n".join(messages))
    chat.see("end")
    chat.config(state="disabled")

def refresh_chat():
    while True:
        dirty.wait()
        dirty.clear()
        win.after(0, render_chat)

def main():
    threading.Thread(target=recv_messages, daemon=True).start()
    threading.Thread(target=refresh_chat, daemon=True).start()

    chat.config(state="disabled")

    win.mainloop()

if __name__ == "__main__":
    main()
