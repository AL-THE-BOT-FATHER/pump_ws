import websocket
import json
import base64
from dataclasses import dataclass, asdict
from solders.pubkey import Pubkey  # type: ignore
from construct import Struct, Padding, Int64ul, Int64sl, Flag, Bytes

WSS = "wss://mainnet.helius-rpc.com/?api-key="

@dataclass
class TradeEvent:
    mint: str
    sol_amount: int
    token_amount: int
    is_buy: bool
    user: str
    timestamp: int
    virtual_sol_reserves: int
    virtual_token_reserves: int
    real_sol_reserves: int
    real_token_reserves: int
    fee_recipient: str
    fee_basis_points: int
    fee: int
    creator: str
    creator_fee_basis_points: int
    creator_fee: int

_trade_layout = Struct(
    Padding(8),
    "mint" / Bytes(32),
    "sol_amount" / Int64ul,
    "token_amount" / Int64ul,
    "is_buy" / Flag,
    "user" / Bytes(32),
    "timestamp" / Int64sl,
    "virtual_sol_reserves" / Int64ul,
    "virtual_token_reserves" / Int64ul,
    "real_sol_reserves" / Int64ul,
    "real_token_reserves" / Int64ul,
    "fee_recipient" / Bytes(32),
    "fee_basis_points" / Int64ul,
    "fee" / Int64ul,
    "creator" / Bytes(32),
    "creator_fee_basis_points" / Int64ul,
    "creator_fee" / Int64ul,
)

def parse_trade_event(program_data_b64: str) -> TradeEvent | None:
    try:
        raw = base64.b64decode(program_data_b64)
        p = _trade_layout.parse(raw)
        return TradeEvent(
            mint=str(Pubkey.from_bytes(p.mint)),
            sol_amount=p.sol_amount,
            token_amount=p.token_amount,
            is_buy=p.is_buy,
            user=str(Pubkey.from_bytes(p.user)),
            timestamp=p.timestamp,
            virtual_sol_reserves=p.virtual_sol_reserves,
            virtual_token_reserves=p.virtual_token_reserves,
            real_sol_reserves=p.real_sol_reserves,
            real_token_reserves=p.real_token_reserves,
            fee_recipient=str(Pubkey.from_bytes(p.fee_recipient)),
            fee_basis_points=p.fee_basis_points,
            fee=p.fee,
            creator=str(Pubkey.from_bytes(p.creator)),
            creator_fee_basis_points=p.creator_fee_basis_points,
            creator_fee=p.creator_fee,
        )
    except Exception as e:
        print(f"Error parsing TradeEvent: {e}")
        return None

def on_message(ws, message):
    try:
        msg = json.loads(message)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return

    rv = msg.get("params", {}).get("result", {}).get("value", {})
    logs = rv.get("logs", [])

    if "Program log: Instruction: Buy" in logs or "Program log: Instruction: Sell" in logs:
        for entry in logs:
            if entry.startswith("Program data: vdt/"):
                b64 = entry.split("Program data: ", 1)[1]
                event = parse_trade_event(b64)
                if event:
                    print(asdict(event))
                break

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WebSocket connection closed")

def on_open(ws):
    sub_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "logsSubscribe",
        "params": [
            {"mentions": ["6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"]},
            {"commitment": "processed"}
        ]
    }
    try:
        ws.send(json.dumps(sub_req))
        print("Subscribed to logs...")
    except Exception as e:
        print(f"Error sending subscription request: {e}")

def start_websocket():
    ws = websocket.WebSocketApp(
        WSS,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.on_open = on_open
    ws.run_forever()

if __name__ == "__main__":
    try:
        start_websocket()
    except Exception as e:
        print(f"Unexpected error in main loop: {e}")
