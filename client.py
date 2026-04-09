import socket
import threading
import curses
import time

PORT = int(input("port: "))
NAME = input("name: ")
PASSWORD = input("password: ")
scroll = 0
dirty = threading.Event()
buffer = ""

EMOJIS = {
    ":x:": "❌",
    ":check:": "✅",
    ":skull:": "💀",
    ":fire:": "🔥",
    ":thumbsup:": "👍",
    ":thumbsdown:": "👎",
    ":heart:": "❤️",
}

messages = []
clients = []

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("bore.pub", PORT))

def receive(client_socket):
    global messages, clients, dirty

    while True:
        try:
            data = client_socket.recv(1024).decode()
            if not data: break

            if data.startswith("[users]"): clients = data[8:].split(",")
            else: messages.append(data)
            dirty.set()
        except:
            break

def parse_emojis(text):
    for code, emoji in EMOJIS.items():
        text = text.replace(code, emoji)
    return text

def redraw(stdscr, input_win, chat_win, users_sidebar):
    global buffer
    chat_win.erase()
    users_sidebar.erase()
    chat_win.box()
    users_sidebar.box()

    max_y, max_x = chat_win.getmaxyx()
    start = -max(0, max_y - 2 - scroll)
    end = len(messages) - scroll

    visible_messages = messages[start:end]

    for i, msg in enumerate(visible_messages):
        chat_win.addstr(i + 1, 1, msg[:max_x - 1])
    
    for i, client in enumerate(clients):
        users_sidebar.addstr(i + 1, 1, client)
        
    input_win.erase()
    input_win.addstr(0, 0, f"{NAME}: {buffer}")
    input_win.refresh()

    chat_win.refresh()
    users_sidebar.refresh()

def clean(stdscr, input_win, chat_win, users_sidebar):
    global dirty
    while True:
        if dirty.is_set():
            redraw(stdscr, input_win, chat_win, users_sidebar)
            dirty.clear()
        time.sleep(0.1)

def main(stdscr):
    global messages, dirty, scroll, buffer
    max_y, max_x = stdscr.getmaxyx()

    chat_win = curses.newwin(max_y - 1, max_x - 15, 0, 0)
    input_win = curses.newwin(1, max_x - 15, max_y - 1, 0)
    users_sidebar = curses.newwin(max_y, 15, 0, max_x - 15)
    key = 0

    threading.Thread(target=receive, daemon=True, args=(client,)).start()
    threading.Thread(target=clean, daemon=True, args=(stdscr,input_win,chat_win,users_sidebar)).start()

    client.send(f"{NAME}\n{PASSWORD}\n".encode())
    time.sleep(0.5)
    client.send(f"--> {NAME} has joined\n".encode())

    while True:
        key = input_win.getch()
        
        if key in (10, 13):
            if buffer == "/quit":
                client.send(f"<-- {NAME} has left".encode())
                exit()
            elif buffer.startswith("/scroll"):
                scroll = int(buffer.split(" ")[1])
            else:
                buffer = parse_emojis(buffer)

                client.send(f"{NAME}: {buffer}".encode())
                messages.append(f"{NAME}: {buffer}")
            buffer = ""
            messages = messages[-200:]
        elif key in (127, curses.KEY_BACKSPACE):
            buffer = buffer[:-1]
        else:
            buffer += chr(key)
        
        dirty.set()

if __name__ == "__main__":
    curses.wrapper(main)