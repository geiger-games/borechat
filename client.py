import requests, time, threading, curses

room_ids = {
    "#general": "!tHofmdIslJQWtrRTVb:matrix.org",
    "#linux": "!anHvnEaFeEgyfqqsLu:matrix.org",
    "#gaming": "!hZkGxuwhBJdjZqAnQJ:matrix.org"
}

current_room = "#general"

messages = []
clients = []
dirty = threading.Event()
buffer = ""
USER = input("Username (@user:matrix.org): ")
PASSWORD = input("Password: ")
sync_token = ""

r = requests.post(
    "https://matrix.org/_matrix/client/v3/login",
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
            "https://matrix.org/_matrix/client/v3/sync",
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
        f"https://matrix.org/_matrix/client/v3/rooms/{room_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "dir": "b",
            "limit": 30
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

def send(msg):
    global room_ids, current_room, token
    url = f"https://matrix.org/_matrix/client/v3/rooms/{room_ids[current_room]}/send/m.room.message/{int(time.time())}"

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

def redraw(stdscr, input_win, chat_win, users_sidebar):
    global buffer
    chat_win.erase()
    users_sidebar.erase()
    chat_win.box()
    users_sidebar.box()

    max_y, max_x = chat_win.getmaxyx()
    start = -max(0, max_y - 2)
    end = len(messages)

    visible_messages = messages[start:end]

    for i, msg in enumerate(visible_messages):
        chat_win.addstr(i + 1, 1, msg[:max_x - 1])
        
    input_win.erase()
    input_win.addstr(0, 0, buffer)
    input_win.refresh()

    chat_win.refresh()
    users_sidebar.refresh()

def clean(stdscr, input_win, chat_win, users_sidebar):
    global dirty
    while True:
        if dirty.is_set():
            redraw(stdscr, input_win, chat_win, users_sidebar)
            dirty.clear()
        time.sleep(0.001)

def main(stdscr):
    global messages, dirty, scroll, buffer, current_room, sync_token
    max_y, max_x = stdscr.getmaxyx()

    chat_win = curses.newwin(max_y - 1, max_x - 15, 0, 0)
    input_win = curses.newwin(1, max_x - 15, max_y - 1, 0)
    users_sidebar = curses.newwin(max_y, 15, 0, max_x - 15)
    key = 0

    dirty.set()

    threading.Thread(target=recv_messages, daemon=True).start()
    threading.Thread(target=clean, daemon=True, args=(stdscr,input_win,chat_win,users_sidebar)).start()

    while True:
        key = input_win.getch()
        
        if key in (10, 13):
            if buffer == "/quit":
                exit()
            elif buffer == "/help":
                messages.extend(["/join - joins and adds you to a Borechat room", "/rooms - shows all available Borechat rooms"])
            elif buffer == "/rooms":
                messages.append(" ".join(list(room_ids.keys())))
            elif buffer.startswith("/join"):
                current_room = buffer.split(" ")[1]
                messages = load_history(room_ids[current_room])
                requests.post(
                    f"https://matrix.org/_matrix/client/v3/rooms/{room_ids[current_room]}/join",
                    headers={
                        "Authorization": f"Bearer {token}"
                    }
                )
                sync_token = ""
            else:
                send(buffer)
            buffer = ""
        elif key in (127, curses.KEY_BACKSPACE):
            buffer = buffer[:-1]
        else:
            buffer += chr(key)
        
        dirty.set()

if __name__ == "__main__":
    curses.wrapper(main)