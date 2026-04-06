import socket
import threading
import curses
import time

PORT = int(input("port: "))
NAME = input("name: ")
PASSWORD = input("password: ")

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

def receive(client_socket, stdscr, input_win, chat_win, users_sidebar):
    global messages, clients

    while True:
        try:
            data = client_socket.recv(1024).decode()
            if not data: break

            if data.startswith("[users]"):

                clients = data[8:].split(",")
            else: messages.append(data)
            redraw(stdscr, input_win, chat_win, users_sidebar)
        except:
            break

def parse_emojis(text):
    for code, emoji in EMOJIS.items():
        text = text.replace(code, emoji)
    return text

def redraw(stdscr, input_win, chat_win, users_sidebar):
    chat_win.clear()
    users_sidebar.clear()
    chat_win.box()
    users_sidebar.box()

    max_y, max_x = chat_win.getmaxyx()
    start = max(0, len(messages) - max_y)

    visible_messages = messages[-(max_y - 2):]

    for i, msg in enumerate(visible_messages):
        chat_win.addstr(i + 1, 1, msg[:max_x - 1])
    
    for i, client in enumerate(clients):
        users_sidebar.addstr(i + 1, 1, client)

    chat_win.refresh()
    users_sidebar.refresh()

def main(stdscr):
    global messages
    max_y, max_x = stdscr.getmaxyx()

    chat_win = curses.newwin(max_y - 1, max_x - 15, 0, 0)
    input_win = curses.newwin(1, max_x - 15, max_y - 1, 0)
    users_sidebar = curses.newwin(max_y, 15, 0, max_x - 15)
    key = 0

    threading.Thread(target=receive, daemon=True, args=(client,stdscr,input_win,chat_win,users_sidebar,)).start()

    buffer = ""


    client.send(f"{NAME}\n{PASSWORD}\n".encode())
    time.sleep(0.5)
    client.send(f"--> {NAME} has joined\n".encode())

    while True:
        redraw(stdscr, input_win, chat_win, users_sidebar)

        key = input_win.getch()
        
        if key in (10, 13):
            if buffer == "/quit":
                client.send(f"<-- {NAME} has left".encode())
                exit()
            buffer = parse_emojis(buffer)

            client.send(f"{NAME}: {buffer}".encode())
            messages.append(f"{NAME}: {buffer}")
            buffer = ""
            messages = messages[-200:]
        elif key in (127, curses.KEY_BACKSPACE):
            buffer = buffer[:-1]
        else:
            buffer += chr(key)
        
        input_win.clear()
        input_win.addstr(0, 0, f"{NAME}: {buffer}")
        input_win.refresh()

if __name__ == "__main__":
    curses.wrapper(main)