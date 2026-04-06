import socket, threading

PORT = int(input("Port: "))
PWD = input("Password: ")
MAX_CLIENTS = int(input("Maximum clients: "))

clients = []
clientNames = []

def recv_line(sock):
    data = b""
    while not data.endswith(b"\n"):
        chunk = sock.recv(1)
        if not chunk:
            return None
        data += chunk
    return data.decode().strip()

def broadcast(message, sender_socket):
    for client in clients:
        if client == sender_socket: continue
        try: client.send(message)
        except: pass


def handle_client(client_socket: socket.socket, client_name):
    password = recv_line(client_socket)
    if (password != PWD):
        clients.remove(client_socket)
        clientNames.remove(client_name)
        client_socket.close()
        return

    while True:
        try:
            message = client_socket.recv(1024)
            if not message: break
            broadcast(message, client_socket)
        except: break
    
    clients.remove(client_socket)
    clientNames.remove(client_name)
    client_socket.close()
    broadcast(f"[users] {",".join(clientNames)}".encode(), None)

def main():
    host = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host.bind(("0.0.0.0", PORT))
    host.listen()

    while True:
        client, _ = host.accept()
        clients.append(client)
        clientName = recv_line(client)
        clientNames.append(clientName)
        broadcast(f"[users] {",".join(clientNames)}".encode(), None)

        threading.Thread(target=handle_client, args=(client,clientName,)).start()

if __name__ == "__main__":
    main()