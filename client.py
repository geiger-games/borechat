import sys
import threading
import time
from getpass import *

import requests
from textual import events
from textual.app import App, ComposeResult
from textual.widgets import Button, Input, Static

room_ids = {
    "#general": "!tHofmdIslJQWtrRTVb:matrix.org",
    "#linux": "!anHvnEaFeEgyfqqsLu:matrix.org",
    "#gaming": "!hZkGxuwhBJdjZqAnQJ:matrix.org"
}

current_room = "#general"

messages = []
clients = []
dirty = threading.Event()
login = threading.Event()
sync_token = ""

def recv_messages():
    global sync_token

    while True:
        params = {
            "timeout": 30000
        }

        if sync_token:
            params["since"] = sync_token

        r = requests.get(
            f"https://{HOMESERVER}/_matrix/client/v3/sync",
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

                name, server = event["sender"].split(":")
                sender = name.replace("@", "") + f" @ {server}"
                body = event.get("content", {}).get("body", "")

                messages.append(f"[{sender}] {body}")
                dirty.set()

def load_history(room_id):
    r = requests.get(
        f"https://{HOMESERVER}/_matrix/client/v3/rooms/{room_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "dir": "b",
            "limit": 75
        }
    )

    data = r.json()

    msgs = []
    for event in data.get("chunk", []):
        if event.get("type") == "m.room.message":
            content = event.get("content", {})
            body = content.get("body")
            # Redacted Matrix events may retain the message type while their
            # content (including the body) has been removed.
            if not isinstance(body, str):
                continue

            name, server = event["sender"].split(":", 1)
            sender = name.replace("@", "") + f" @ {server}"
            msgs.append(f"[{sender}] {body}")

            dirty.set()

    return list(reversed(msgs))

def send(event=None, msg=None):
    global current_room

    if msg is None:
        return

    if msg == "/quit":
        sys.exit(0)
    elif msg == "/help":
        messages.extend(["/join - joins and adds you to a Borechat room", "/rooms - shows all available Borechat rooms"])
    elif msg == "/rooms":
        messages.append(" ".join(list(room_ids.keys())))
    elif msg.startswith("/join"):
        parts = msg.split()
        if len(parts) != 2 or parts[1] not in room_ids:
            messages.append("Usage: /join <room> (available: " + " ".join(room_ids) + ")")
            dirty.set()
            return

        current_room = parts[1]
        requests.post(
            f"https://{HOMESERVER}/_matrix/client/v3/rooms/{room_ids[current_room]}/join",
            headers={
                "Authorization": f"Bearer {token}"
            }
        )
        messages.clear()
        messages.extend(load_history(room_ids[current_room]))
    else:
        sendToRoom(msg)

    dirty.set()


def sendToRoom(msg):
    url = f"https://{HOMESERVER}/_matrix/client/v3/rooms/{room_ids[current_room]}/send/m.room.message/{int(time.time())}"

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


def render_chat(chat):
    text = ""
    for msg in messages:
        if msg.startswith("["):
            sender, body = msg.split("]", 1)
            text += sender + "]" + body + "\n"
        else:
            text += msg + "\n"
    chat.update(text)

class LoginApp(App):
    CSS = """
    Screen {
        align: center middle;
    }
    Button {
        align: center middle;
    }
    Input {
        align: center middle;
    }
    """

    def __init__(self):
        super().__init__()
        self.input = Input(placeholder="@user:example.org")
        self.password_input = Input(password=True, placeholder="Password")
        self.login_button = Button("Login")
    
    def compose(self) -> ComposeResult:
        yield self.input
        yield self.password_input
        yield self.login_button

    def on_mount(self) -> None:
        self.input.border_title = "Username"
        self.password_input.border_title = "Password"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        global USER, PASSWORD, HOMESERVER, token

        USER = self.input.value.split(":", 1)[0].replace("@", "")
        HOMESERVER = self.input.value.split(":", 1)[1]

        PASSWORD = self.password_input.value

        r = requests.post(
            f"https://{HOMESERVER}/_matrix/client/v3/login",
            json={
                "type": "m.login.password",
                "identifier": {"type": "m.id.user", "user": USER},
                "password": PASSWORD,
            },
        )
        data = r.json()
        token = data["access_token"]

        login.set()
        self.exit()




class ChatApp(App):
    CSS = """
    Input {
        align: center bottom;
    }
    Static {
        height: 1fr;
        width: 100%;
        border: round $accent;
        padding: 1 2;
        overflow: auto;
    }
    """

    def __init__(self):
        super().__init__()
        self.input = Input(placeholder="Type something...")
        self.chat = Static("")

    def compose(self) -> ComposeResult:
        yield self.chat
        yield self.input

    def on_mount(self) -> None:
        self.chat.border_title = f"Current Room: {current_room}"
        self.input.border_title = "Input (Press Enter to send)"
        self.chat.loading = True
        threading.Thread(target=recv_messages, daemon=True).start()
        dirty.wait()
        messages.clear()
        messages.extend(load_history(room_ids[current_room]))
        self.chat.loading = False
        self.set_interval(0.25, self.refresh_chat)

    def refresh_chat(self) -> None:
        if dirty.is_set():
            dirty.clear()
            render_chat(self.chat)

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            send(msg=self.input.value)
            self.input.value = ""

def main(app):
    app.run()
    

if __name__ == "__main__":
    login_app = LoginApp()
    main(login_app)
    login.wait()
    main(ChatApp())