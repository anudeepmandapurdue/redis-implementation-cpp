import socket
import struct

def send_req(s, args):
    #Protocol: [nstr (4 bytes)] + [ [len (4 bytes)] + [string (len bytes)] ... ]
    body = struct.pack('<I', len(args))
    for arg in args:
        arg_bytes = arg.encode('utf-8')
        body += struct.pack('<I', len(arg_bytes)) + arg_bytes
    
    # Header: Total length of the body (4 bytes)
    header = struct.pack('<I', len(body))
    s.sendall(header + body)

def recv_res(s):
    # Response: [len (4 bytes)] + [status (4 bytes)] + [data...]
    header = s.recv(4)
    if not header: return None
    res_len = struct.unpack('<I', header)[0]
    res_body = s.recv(res_len)
    
    status = struct.unpack('<I', res_body[:4])[0]
    data = res_body[4:].decode('utf-8')
    return status, data

# Connect to your C++ server
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('127.0.0.1', 1234))

# Test SET
print("Setting 'key1' to 'hello'...")
send_req(s, ["set", "key1", "hello"])
print("Response:", recv_res(s))

# Test GET
print("Getting 'key1'...")
send_req(s, ["get", "key1"])
print("Response:", recv_res(s))

# Test DEL
print("Deleting 'key1'...")
send_req(s, ["del", "key1"])
print("Response:", recv_res(s))

s.close()