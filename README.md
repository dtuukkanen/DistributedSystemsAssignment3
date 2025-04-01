# Explanation of how transparency, scalability, and failure handling have been catered in the solution

## Transparency

### Access Transparency

- The client doesn't need to know the internal implementation of the server
- The JSON message format provides a consistent interface between client and server

### Location Transparency

- Clients connect using IP address adn port, allowing the server to be anywhere on the network
- Users reference each other by nicknames, not by physical locations (no IP addresses needed)

### Concurrency Transparency

- The server uses threading to handle multiple clients simultaneously
- The lock mechanism (`self.lock`) prevents reace conditions on shared data structures

## Scalability

### Thread-based Architecture

- Each client connection gets its own thread via `threading.Thread(target=self.handle_client)`
- This allows handling of multiple clients but has inherent limitations for very large scale

### Channel-based Design:

- Users are organized into channels, which provides a logical separation
- This can help distribute message load across different interest groups

### Limitations:

- The current design keeps all clients and messages in memory
- No database persistence or load balancing across multiple servers

## Failure handling

### Client-side Handling:

- Connection failures are properly detected and reported
- Client gracefully handles server disconnections in `receive_messages()`
- Proper socket cleanup in `disconnect()` method with `socket.shutdown()`

### Server-side Handling:

- Exception handling in `handle_client()` catches connection errors
- Client disconnections are properly detected and resources are released
- The `handle_client_disconnect()` method ensures clean client removal

### Message Delivery:

- Error handling for failed message deliveries exists
- However, there's no guarantee of message delivery or persistent storage

# Explain how the server manages multiple clients - via threads or otherwise - and how the connection is maintained. Explain why the connection is TCP or UDP

- The server users threads to manage multiple client. Every client gets own socket that handles the communication and stays open until client leaves.
- Connection is TCP since the socket remains open and handshake is being made with `socket.accept()`. Also messages are not lost.

# Video showcasing the program

https://lut-my.sharepoint.com/:v:/g/personal/daniel_tuukkanen_student_lut_fi/EWuqGhgUqV1PhjRiTsD1NiYBVRYSBfWwVDifrAlXWYtPWw?e=qi3ddX
