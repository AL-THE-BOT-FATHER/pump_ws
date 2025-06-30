import websocket
import json
import base64
import time
from dataclasses import dataclass, asdict
from solders.pubkey import Pubkey  # type: ignore
from construct import Padding, Struct, Int64sl, Int16ul, Int8ul, Int64ul, Bytes

WSS = "wss://mainnet.helius-rpc.com/?api-key="

_create_layout = Struct(
    Padding(8),
    "timestamp" / Int64sl,               # i64
    "index" / Int16ul,                   # u16
    "creator" / Bytes(32),               # pubkey
    "base_mint" / Bytes(32),             # pubkey
    "quote_mint" / Bytes(32),            # pubkey
    "base_mint_decimals" / Int8ul,       # u8
    "quote_mint_decimals" / Int8ul,      # u8
    "base_amount_in" / Int64ul,          # u64
    "quote_amount_in" / Int64ul,         # u64
    "pool_base_amount" / Int64ul,        # u64
    "pool_quote_amount" / Int64ul,       # u64
    "minimum_liquidity" / Int64ul,       # u64
    "initial_liquidity" / Int64ul,       # u64
    "lp_token_amount_out" / Int64ul,     # u64
    "pool_bump" / Int8ul,                # u8
    "pool" / Bytes(32),                  # pubkey
    "lp_mint" / Bytes(32),               # pubkey
    "user_base_token_account" / Bytes(32),  # pubkey
    "user_quote_token_account" / Bytes(32)  # pubkey
)

@dataclass
class CreatePoolEvent:
    timestamp: int
    index: int
    creator: str
    base_mint: str
    quote_mint: str
    base_mint_decimals: int
    quote_mint_decimals: int
    base_amount_in: int
    quote_amount_in: int
    pool_base_amount: int
    pool_quote_amount: int
    minimum_liquidity: int
    initial_liquidity: int
    lp_token_amount_out: int
    pool_bump: int
    pool: str
    lp_mint: str
    user_base_token_account: str
    user_quote_token_account: str

def decode_event(program_data_base64: str) -> CreatePoolEvent | None:
    try:
        raw = base64.b64decode(program_data_base64)
        p = _create_layout.parse(raw)
        return CreatePoolEvent(
            timestamp=p.timestamp,
            index=p.index,
            creator=str(Pubkey.from_bytes(p.creator)),
            base_mint=str(Pubkey.from_bytes(p.base_mint)),
            quote_mint=str(Pubkey.from_bytes(p.quote_mint)),
            base_mint_decimals=p.base_mint_decimals,
            quote_mint_decimals=p.quote_mint_decimals,
            base_amount_in=p.base_amount_in,
            quote_amount_in=p.quote_amount_in,
            pool_base_amount=p.pool_base_amount,
            pool_quote_amount=p.pool_quote_amount,
            minimum_liquidity=p.minimum_liquidity,
            initial_liquidity=p.initial_liquidity,
            lp_token_amount_out=p.lp_token_amount_out,
            pool_bump=p.pool_bump,
            pool=str(Pubkey.from_bytes(p.pool)),
            lp_mint=str(Pubkey.from_bytes(p.lp_mint)),
            user_base_token_account=str(Pubkey.from_bytes(p.user_base_token_account)),
            user_quote_token_account=str(Pubkey.from_bytes(p.user_quote_token_account)),
        )
    except Exception:
        return None

def on_message(ws, message):
    try:
        log_data = json.loads(message)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return

    logs = log_data.get("params", {}) \
                   .get("result", {}) \
                   .get("value", {}) \
                   .get("logs", [])

    if "Program log: Instruction: CreatePool" in "".join(logs):
        for log_entry in logs:
            if log_entry.startswith("Program data: "):
                b64 = log_entry.split("Program data: ", 1)[1]
                event = decode_event(b64)
                if event:
                    print(asdict(event))
                break

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
            {"commitment": "processed"},
        ],
    }
    try:
        ws.send(json.dumps(request))
        print("Subscribed to logs...")
    except Exception as e:
        print(f"Error sending subscription request: {e}")

def start_websocket():
    while True:
        ws = websocket.WebSocketApp(
            WSS,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        ws.on_open = on_open
        ws.run_forever()
        print("WebSocket connection lost. Reconnecting in 1 second...")
        time.sleep(1)

if __name__ == "__main__":
    try:
        start_websocket()
    except Exception as e:
        print(f"Unexpected error in main event loop: {e}")
