import websocket
import json
import base64
from solders.pubkey import Pubkey  # type: ignore
import struct

WSS = "wss://mainnet.helius-rpc.com/?api-key="

def parse_event_data(data_hex):
    try:
        data_bytes = bytes.fromhex(data_hex)
        offset = 8

        def read_length_prefixed_string(data, offset):
            try:
                length = struct.unpack('<I', data[offset:offset + 4])[0]
                offset += 4
                string_data = data[offset:offset + length]
                offset += length
                return string_data.decode('utf-8').strip('\x00'), offset
            except Exception as e:
                print(f"Error reading length-prefixed string: {e}")
                raise

        def read_pubkey(data, offset):
            try:
                pubkey_data = data[offset:offset + 32]
                offset += 32
                pubkey = str(Pubkey.from_bytes(pubkey_data))
                return pubkey, offset
            except Exception as e:
                print(f"Error reading pubkey: {e}")
                raise

        event_data = {}
        event_data['name'], offset = read_length_prefixed_string(data_bytes, offset)
        event_data['symbol'], offset = read_length_prefixed_string(data_bytes, offset)
        event_data['uri'], offset = read_length_prefixed_string(data_bytes, offset)
        event_data['mint'], offset = read_pubkey(data_bytes, offset)
        event_data['bonding_curve'], offset = read_pubkey(data_bytes, offset)
        event_data['user'], offset = read_pubkey(data_bytes, offset)

        return event_data
    except Exception as e:
        print(f"Error parsing event data: {e}")
        raise

def on_message(ws, message):
    try:
        log_data = json.loads(message)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return

    logs = log_data.get("params", {}).get("result", {}).get("value", {}).get("logs", [])

    if "Instruction: InitializeMint2" in ''.join(logs):
        for log_entry in logs:
            if "Program data: " in log_entry and not log_entry.startswith("Program data: vdt/"):
                try:
                    program_data_base64 = log_entry.split("Program data: ")[1]
                    program_data_bytes = base64.b64decode(program_data_base64)
                    program_data_hex = program_data_bytes.hex()
                except Exception as e:
                    print(f"Error decoding base64 program data: {e}")
                    continue

                try:
                    event_data = parse_event_data(program_data_hex)
                    event_data_json = json.dumps(event_data)
                    print(f"{event_data_json},")
                except Exception as e:
                    print(f"Error processing event data: {e}")

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WebSocket connection closed")

def on_open(ws):
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "logsSubscribe",
        "params": [
            {"mentions": ["6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"]},
            {"commitment": "processed"}
        ]
    }
    try:
        ws.send(json.dumps(request))
        print("Subscribed to logs...")
    except Exception as e:
        print(f"Error sending subscription request: {e}")

def start_websocket():
    ws = websocket.WebSocketApp(WSS,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.on_open = on_open
    ws.run_forever()

if __name__ == "__main__":
    try:
        start_websocket()
    except Exception as e:
        print(f"Unexpected error in main event loop: {e}")
