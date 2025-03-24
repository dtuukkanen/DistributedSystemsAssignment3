import socket
import threading
import json

class ChatClient:
    def __init__(self):
        """Initialize the chat client."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.nickname = None
        self.server_address = None
        self.server_port = None
        self.current_channel = "general"
        self.connected = False
        self.received_thread = None

    def connect_to_server(self, address, port, nickname):
        """Connect to the chat server."""
        self.server_address = address
        self.server_port = port
        self.nickname = nickname

        try:
            self.socket.connect((address, port))
            self.connected = True

            # Send nickname to server
            self.send_message({
                "type": "set_nickname",
                "nickname": nickname
            })

            # Start receiving messages in a separate thread
            self.received_thread = threading.Thread(target=self.receive_messages)
            self.received_thread.daemon = True
            self.received_thread.start()

            return True
        
        except ConnectionRefusedError:
            print("Connection failed: server not available")
            return False
        except Exception as e:
            print(f"Connection fialed: {e}")
            return False
        
    def send_message(self, message):
        """Send a message to the server."""
        if not self.connected:
            print("Not connected to server")
            return
        
        try:
            self.socket.send(json.dumps(message).encode('utf-8'))
        except Exception as e:
            print(f"Failed to send message: {e}")
            self.disconnect()

    def send_chat_message(self, content):
        """Send a chat message to the current channel."""
        self.send_message({
            "type": "chat",
            content: content
        })

    def send_private_message(self, recipient, content):
        """Send a private message to a specific user."""
        self.send_message({
            "type": "private",
            "recipient": recipient,
            "content": content
        })

    def join_channel(self, channel):
        """Join a different channel."""
        self.send_message({
            "type": "join_channel",
            "channel": channel
        })
        self.current_channel = channel

    def list_channels(self):
        """Request the list of avavilable channels."""
        self.send_message({
            "type": "list_channels"
        })

    def list_users(self, channel=None):
        """Request a list of users in a channel."""
        if not channel:
            channel = self.current_channel

        self.send_message({
            "type": "list_users",
            "channel": channel
        })

    def receive_messages(self):
        """Receive and process messages from the server."""
        try:
            while self.connected:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    break

                try:
                    message = json.loads(data)
                    self.process_message(message)
                except json.JSONDecodeError:
                    print("Received invalid message format")

        except ConnectionError:
            pass
        except Exception as e:
            if self.connected:
                self.disconnect()

    def process_message(self, message):
        """Process a received message."""
        message_type = message.get("type", "")

        if message_type == "chat":
            sender = message.get("sender", "")
            content = message.get("content", "")
            print(f"[{self.current_channel}] {sender}: {content}")
        
        elif message_type == "private":
            sender = message.get("sender", "Unknown")
            content = message.get("content", "")
            print(f"[Private from {sender}]: {content}")
        
        elif message_type == "server_message":
            content = message.get("content", "")
            print(f"[Server] {content}")

        elif message_type == "channel_list":
            channels = message.get("channels", [])
            print("Available channels:")
            for channel in channels:
                print(f"- {channel}")

        elif message_type == "user_list":
            channel = message.get("channel", "")
            users = message.get("users", [])
            print(f"Users in channel {channel}:")
            for user in users:
                print(f"- {user}")
        
        elif message_type == "error":
            error_message = message.get("content", "Unknown error")
            print(f"[Error] {error_message}")

    def disconnect(self):
        """Disconnect from the server."""
        if self.connected:
            self.connected = False
            try:
                self.socket.close()
            except:
                pass
            print("Disconnected from server")

def display_menu():
    """Display the client menu."""
    print("\nChat Commands:")
    print("  /msg <user> <message> - Send private message")
    print("  /join <channel> - Join a channel")
    print("  /channels - List available channels")
    print("  /users - List users in current channel")
    print("  /quit - Disconnect and exit")
    print("  /help - Show this help message")
    print("  Just type to send a message to the current channel")
    print()

def main():
    """Main funciton to run the chat client."""
    client = ChatClient()

    print("==== Chat Client ====")

    # Get connection details
    server_address = input("Server address (default: localhost): ") or "localhost"
    server_port = input("Server port (default: 9000): ") or 9000
    nickname = input("Choose a nickname: ")

    while not nickname:
        nickname = input("Nickname cannot be empty. Choose a nickname: ")

    print(f"Connecting to {server_address}:{server_port}...")
    if not client.connect_to_server(server_address, server_port, nickname):
        print("Failed to connect. Exiting.")
        return
    
    print(f"Connected as {nickname}!")
    display_menu()

    # Main loop
    while client.connected:
        try:
            user_input = input()

            if not user_input:
                continue

            if user_input.startswith("/"):
                parts = user_input.split(" ", 2)
                command = parts[0].lower()

                if command == "/quit":
                    client.disconnect()
                    break

                elif command == "/msg" and len(parts) >= 3:
                    recipient = parts[1]
                    message = parts[2]
                    client.send_private_message(recipient, message)

                elif command == "/join" and len(parts) >= 2:
                    channel = parts[1]
                    client.join_channel(channel)

                elif command == "/channels":
                    client.list_channels()

                elif command == "/users":
                    client.list_users()

                elif command == "/help":
                    display_menu()

                else:
                    print("Unknown command or missing parameters")
                    display_menu()
            else:
                client.send_chat_message(user_input)
            
        except KeyboardInterrupt:
            client.disconnect()
            break
    
    print("Goodbye!")

if __name__ == "__main__":
    main()
