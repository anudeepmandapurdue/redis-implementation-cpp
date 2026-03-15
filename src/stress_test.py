import socket
import struct
import time

def send_request(s, args):
    """Serializes and sends a request in the custom binary protocol."""
    # Build the body: [nstr] + [len1, str1, len2, str2...]
    body = struct.pack('<I', len(args))
    for arg in args:
        arg_bytes = arg.encode('utf-8')
        body += struct.pack('<I', len(arg_bytes)) + arg_bytes
    
    # Send Header (total body length) + Body
    header = struct.pack('<I', len(body))
    s.sendall(header + body)

def recv_response(s):
    """Parses the response header and body."""
    # Read the 4-byte length prefix
    header = s.recv(4)
    if not header:
        return None, None
    res_len = struct.unpack('<I', header)[0]
    
    # Read the actual response body
    res_body = s.recv(res_len)
    if len(res_body) < 4:
        return None, None
    
    status = struct.unpack('<I', res_body[:4])[0]
    data = res_body[4:].decode('utf-8')
    return status, data

def test_server():
    addr = ('127.0.0.1', 1234)
    print("--- Starting Full Server Test ---")

    # 1. Basic SET/GET
    with socket.create_connection(addr) as s:
        print("[1] Testing Basic SET/GET...")
        send_request(s, ["set", "master_key", "original_value"])
        status, _ = recv_response(s)
        
        send_request(s, ["get", "master_key"])
        status, val = recv_response(s)
        assert status == 0 and val == "original_value", f"Failed! Got {val}"
        print("    Success: Basic operations verified.")

    # 2. Stress Test: Trigger Progressive Rehashing
    # Table starts at size 4. With load factor 8, it rehashes after 32 keys.
    # We will insert 200 keys to ensure multiple resizes and migration work.
    print("[2] Stress Testing: Inserting 200 keys to trigger rehashing...")
    with socket.create_connection(addr) as s:
        for i in range(200):
            send_request(s, ["set", f"key_{i}", f"val_{i}"])
            recv_response(s) # Consume OK response
        print("    Success: 200 keys inserted.")

    # 3. Dual-Table Verification
    # While migration might still be happening, check the first key we ever set
    with socket.create_connection(addr) as s:
        print("[3] Verifying data persistence after rehash...")
        send_request(s, ["get", "master_key"])
        status, val = recv_response(s)
        assert status == 0 and val == "original_value", "Key lost during rehash!"
        
        # Check a key from the middle of the stress test
        send_request(s, ["get", "key_100"])
        status, val = recv_response(s)
        assert status == 0 and val == "val_100"
        print("    Success: All data found in both old/new tables.")

    # 4. Deletion & Error Handling
    with socket.create_connection(addr) as s:
        print("[4] Testing DEL and RES_NX (Not Found)...")
        send_request(s, ["del", "master_key"])
        recv_response(s)
        
        send_request(s, ["get", "master_key"])
        status, val = recv_response(s)
        # Status 2 is your defined RES_NX
        assert status == 2, f"Expected Status 2, got {status}"
        print("    Success: Deletion and NX status verified.")

    print("\n--- ALL TESTS PASSED SUCCESSFULLY ---")

if __name__ == "__main__":
    try:
        test_server()
    except Exception as e:
        print(f"\n[!] Test failed with error: {e}")