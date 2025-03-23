import websocket
import json
import base64
import time
from solders.pubkey import Pubkey  # type: ignore
from construct import Padding, Struct, Int64sl, Int16ul, Int8ul, Int64ul, Bytes

WSS = "wss://mainnet.helius-rpc.com/?api-key="

CREATE_POOL_EVENT_LAYOUT = Struct(
    Padding(8),
    "timestamp" / Int64sl,             # i64: signed 64-bit integer
    "index" / Int16ul,                 # u16: unsigned 16-bit integer
    "creator" / Bytes(32),             # pubkey: 32 bytes
    "base_mint" / Bytes(32),           # pubkey: 32 bytes
    "quote_mint" / Bytes(32),          # pubkey: 32 bytes
    "base_mint_decimals" / Int8ul,     # u8: unsigned 8-bit integer
    "quote_mint_decimals" / Int8ul,    # u8: unsigned 8-bit integer
    "base_amount_in" / Int64ul,        # u64: unsigned 64-bit integer
    "quote_amount_in" / Int64ul,       # u64: unsigned 64-bit integer
    "pool_base_amount" / Int64ul,      # u64: unsigned 64-bit integer
    "pool_quote_amount" / Int64ul,     # u64: unsigned 64-bit integer
    "minimum_liquidity" / Int64ul,     # u64: unsigned 64-bit integer
    "initial_liquidity" / Int64ul,     # u64: unsigned 64-bit integer
    "lp_token_amount_out" / Int64ul,   # u64: unsigned 64-bit integer
    "pool_bump" / Int8ul,              # u8: unsigned 8-bit integer
    "pool" / Bytes(32),                # pubkey: 32 bytes
    "lp_mint" / Bytes(32),             # pubkey: 32 bytes
    "user_base_token_account" / Bytes(32),   # pubkey: 32 bytes
    "user_quote_token_account" / Bytes(32)     # pubkey: 32 bytes
)

def decode_event(program_data_base64):
    try:
        parsed_data = CREATE_POOL_EVENT_LAYOUT.parse(base64.b64decode(program_data_base64))
        
        json_data = {
            "timestamp": parsed_data.timestamp,
            "index": parsed_data.index,
            "creator": str(Pubkey.from_bytes(parsed_data.creator)),
            "base_mint": str(Pubkey.from_bytes(parsed_data.base_mint)),
            "quote_mint": str(Pubkey.from_bytes(parsed_data.quote_mint)),
            "base_mint_decimals": parsed_data.base_mint_decimals,
            "quote_mint_decimals": parsed_data.quote_mint_decimals,
            "base_amount_in": parsed_data.base_amount_in,
            "quote_amount_in": parsed_data.quote_amount_in,
            "pool_base_amount": parsed_data.pool_base_amount,
            "pool_quote_amount": parsed_data.pool_quote_amount,
            "minimum_liquidity": parsed_data.minimum_liquidity,
            "initial_liquidity": parsed_data.initial_liquidity,
            "lp_token_amount_out": parsed_data.lp_token_amount_out,
            "pool_bump": parsed_data.pool_bump,
            "pool": str(Pubkey.from_bytes(parsed_data.pool)),
            "lp_mint": str(Pubkey.from_bytes(parsed_data.lp_mint)),
            "user_base_token_account": str(Pubkey.from_bytes(parsed_data.user_base_token_account)),
            "user_quote_token_account": str(Pubkey.from_bytes(parsed_data.user_quote_token_account))
        }
        return json_data
    except:
        return None

def on_message(ws, message):
    try:
        log_data = json.loads(message)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return

    logs = log_data.get("params", {}).get("result", {}).get("value", {}).get("logs", [])

    if "Program log: Instruction: CreatePool" in ''.join(logs):
        for log_entry in logs:
            if "Program data: " in log_entry:
                try:
                    program_data_base64 = str(log_entry).split("Program data: ")[1]
                    print(program_data_base64)
                    event_data_json = decode_event(program_data_base64)
                    if event_data_json:
                        print(f"{event_data_json}")
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
            {"mentions": ["pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"]},
            {"commitment": "processed"}
        ]
    }
    try:
        ws.send(json.dumps(request))
        print("Subscribed to logs...")
    except Exception as e:
        print(f"Error sending subscription request: {e}")

def start_websocket():
    while True:
        ws = websocket.WebSocketApp(WSS,
                                    on_message=on_message,
                                    on_error=on_error,
                                    on_close=on_close)
        ws.on_open = on_open
        ws.run_forever()
        print("WebSocket connection lost. Reconnecting in 1 second...")
        time.sleep(1)

if __name__ == "__main__":
    try:
        start_websocket()
    except Exception as e:
        print(f"Unexpected error in main event loop: {e}")
