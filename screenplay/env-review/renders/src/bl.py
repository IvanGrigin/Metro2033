# Send Python code to the Blender MCP add-on (127.0.0.1:9876); prints JSON response.
import socket, json, sys
code = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
s = socket.create_connection(('127.0.0.1', 9876), timeout=60)
s.sendall(json.dumps({"type": "execute", "code": code, "strict_json": False}).encode() + b"\0")
buf = b''
while b"\0" not in buf:
    c = s.recv(65536)
    if not c: break
    buf += c
print(json.dumps(json.loads(buf.rstrip(b"\0")), ensure_ascii=False, indent=1))
