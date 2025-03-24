import socket
import threading
import json

class ChatServer:
    def __init__(self, host='0.0.0.0', port=9000):
        """Initialize the chat server."""
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {} # {client_socket: {"nickname": nickname, "channel": channel}}
        self.channels = {"general": set()} # Default channel
        self.lock = threading.Lock() # For thread-safe operations on shared data

    def start(self):
        """Start the server and listen for connections."""
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5) # Max 5 connections in the queue
            print(f"Server started on {self.host}:{self.port}")

            while True:
                client_socket, client_address = self.server_socket.accept()
                print(f"New connection from {client_address}")

                # Create and start a new thread for the client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
            
        except KeyboardInterrupt:
            print("Server shutting down...")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.server_socket.close()

    def handle_client(self, client_socket, client_address):
        """Handle a client connection."""
        try:
            # Wait for the client to send their nickname
            nickname_data = client_socket.recv(1024).decode('utf-8')
            nickname_json = json.loads(nickname_data)
            nickname = nickname_json.get("nickname", f"User-{client_address[0]}")

            # Register the client
            with self.lock:
                self.clients[client_socket] = {
                    "nickname": nickname,
                    "channel": "general"
                }
                self.channels["general"].add(client_socket)

            # Send welcome message
            self.send_message_to_client(client_socket, {
                "type": "server_message",
                "content": f"Welcome to the chat, {nickname}!"
            })
            print(f"Client {nickname} connected from {client_address}")

            # Notify others
            self.broadcast_message({
                "type": "server_message",
                "content": f"{nickname} has joined the channel."
            }, exclude=client_socket, channel="general")
            print(f"Broadcasted join message to channel general")

            # Main loop to receive messages
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break

                try:
                    message = json.loads(data)
                    self.process_message(client_socket, message)
                    print(f"Received message from {nickname}: {message}")
                except json.JSONDecodeError:
                    self.send_message_to_client(client_socket, {
                        "type": "server_message",
                        "content": "Invalid message format."
                    })
                    print(f"Invalid message format from {nickname}: {data}")
                
        except ConnectionError:
            print(f"Connection error with {client_address}")
            pass  # Client disconnected
        finally:
            self.handle_client_disconnect(client_socket)

    def process_message(self, client_socket, message):
        """Process a message from a client."""
        message_type = message.get("type", "")
        sender = self.clients[client_socket]["nickname"]
        current_channel = self.clients[client_socket]["channel"]

        if message_type == "chat":
            content = message.get("content", "")
            self.broadcast_message({
                "type": "chat",
                "sender": sender,
                "content": content
            }, channel=current_channel)
        
        elif message_type == "private":
            recipient = message.get("recipient", "")
            content = message.get("content", "")
            self.send_private_message(client_socket, recipient, content)
        
        elif message_type == "join_channel":
            new_channel = message.get("channel", "")
            self.join_channel(client_socket, new_channel)

        elif message_type == "list_channels":
            self.list_channels(client_socket)

        elif message_type == "list_users":
            channel = message.get("channel", current_channel)
            self.list_users(client_socket, channel)
        
        else:
            self.send_message_to_client(client_socket, {
                "type": "error",
                "content": "Unknown message type."
            })
            print(f"Unknown message type from {sender}: {message_type}")

    def send_message_to_client(self, client_socket, message):
        """Send a message to a specific client."""
        try:
            client_socket.send(json.dumps(message).encode('utf-8'))
            print(f"Sent message to {self.clients[client_socket]['nickname']}: {message}")
        except Exception as e:
            print(f"Error sending message: {e}")

    def broadcast_message(self, message, exclude=None, channel=None):
        """Broadcast a message to all clients in a channel."""
        with self.lock:
            recipients = self.channels.get(channel, set()) if channel else set(self.clients.keys())
            for client_socket in recipients:
                if client_socket != exclude and client_socket in self.clients:
                    self.send_message_to_client(client_socket, message)
                    print(f"Sent message to {self.clients[client_socket]['nickname']} in channel {channel}")

    def send_private_message(self, sender_socket, recipient_name, content):
        """Send a private message to a specific user."""
        sender_name = self.clients[sender_socket]["nickname"]
        recipient_socket = None

        with self.lock:
            for socket, info in self.clients.items():
                if info["nickname"] == recipient_name:
                    recipient_socket = socket
                    break
        
        if recipient_socket:
            # Send to recipient
            self.send_message_to_client(recipient_socket, {
                "type": "private",
                "sender": sender_name,
                "content": content
            })
            print(f"Private message sent from {sender_name} to {recipient_name}: {content}")

            # Send confirmation to sender
            self.send_message_to_client(sender_socket, {
                "type": "private_sent",
                "recipient": recipient_name,
                "content": content
            })
            print(f"Private message confirmation sent to {sender_name}")
        else:
            self.send_message_to_client(sender_socket, {
                "type": "server_message",
                "content": f"User {recipient_name} not found."
            })
            print(f"Private message failed: User {recipient_name} not found")
    
    def join_channel(self, client_socket, channel):
        """Move a client to a different channel."""
        client_info = self.clients[client_socket]
        old_channel = client_info["channel"]

        with self.lock:
            # Create the channel if it doesn't exist
            if channel not in self.channels:
                self.channels[channel] = set()
                print(f"Channel {channel} created")

            # Remove from old channel
            if old_channel in self.channels:
                self.channels[old_channel].discard(client_socket)

            # Add to new channel
            self.channels[channel].add(client_socket)
            client_info["channel"] = channel

        # Notify the client
        self.send_message_to_client(client_socket, {
            "type": "server_message",
            "content": f"You have joined the channel: {channel}"
        })
        print(f"{client_info['nickname']} joined channel {channel}")

        # Notify others in the old channel
        self.broadcast_message({
            "type": "server_message",
            "content": f"{client_info['nickname']} has joined the channel"
        }, exclude=client_socket, channel=channel)
        print(f"Broadcasted channel join message to {channel}")

    def list_channels(self, client_socket):
        """Send a list of available channels to the client."""
        with self.lock:
            channels = list(self.channels.keys())
        
        self.send_message_to_client(client_socket, {
            "type": "channel_list",
            "channels": channels
        })
        print(f"Sent channel list to {self.clients[client_socket]['nickname']}")

    def list_users(self, client_socket, channel):
        """Send a list of users in a channel to the client."""
        user_list = []

        with self.lock:
            if channel in self.channels:
                for client in self.channels[channel]:
                    if client in self.clients:
                        user_list.append(self.clients[client]["nickname"])
        
        self.send_message_to_client(client_socket, {
            "type": "user_list",
            "channel": channel,
            "users": user_list
        })
        print(f"Sent user list for channel {channel} to {self.clients[client_socket]['nickname']}")

    def handle_client_disconnect(self, client_socket):
        """Clean up when a client disconnects."""
        with self.lock:
            if client_socket in self.clients:
                nickname = self.clients[client_socket]["nickname"]
                channel = self.clients[client_socket]["channel"]

                # Remove from channels
                if channel in self.channels:
                    self.channels[channel].discard(client_socket)

                # Remove client
                del self.clients[client_socket]

                # Notify others
                self.broadcast_message({
                    "type": "server_message",
                    "content": f"{nickname} has left the chat!."
                }, channel=channel)
                print(f"Broadcasted leave message for {nickname}")

        client_socket.close()
        print(f"Client {nickname} disconnected")

if __name__ == "__main__":
    server = ChatServer()
    server.start()
