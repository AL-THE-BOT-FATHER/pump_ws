import websocket
import json
import base64
from solders.pubkey import Pubkey  # type: ignore
from construct import Struct, Padding, Int64ul, Flag, Bytes

WSS = "wss://mainnet.helius-rpc.com/?api-key="

trade = Struct(
    Padding(8),
    "mint" / Bytes(32),
    "solAmount" / Int64ul,
    "tokenAmount" / Int64ul,
    "isBuy" / Flag,
    "user" / Bytes(32),
    "timestamp" / Int64ul,
    "virtualSolReserves" / Int64ul,
    "virtualTokenReserves" / Int64ul
)

def format_trade(parsed_data, txn_sig):
    try:
        return {
            "mint": str(Pubkey.from_bytes(bytes(parsed_data.mint))),
            "sol_amount": parsed_data.solAmount / 10**9,
            "token_amount": parsed_data.tokenAmount / 10**6,
            "is_buy": parsed_data.isBuy,
            "user": str(Pubkey.from_bytes(bytes(parsed_data.user))),
            "timestamp": parsed_data.timestamp,
            "virtual_sol_reserves": parsed_data.virtualSolReserves,
            "virtual_token_reserves": parsed_data.virtualTokenReserves,
            "txn_sig": txn_sig
        }
    except Exception as e:
        print(f"Error formatting trade data: {e}")
        return None

def on_message(ws, message):
    try:
        log_data = json.loads(message)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return

    try:
        result_value = log_data.get("params", {}).get("result", {}).get("value", {})
        txn_sig = result_value.get("signature", "")
        logs = result_value.get("logs", [])
    except Exception as e:
        print(f"Error extracting data from log response: {e}")
        return

    if "Program log: Instruction: Buy" in logs and "Program log: Instruction: Sell" not in logs:
        for log_entry in logs:
            if "Program data: vdt/" in log_entry:
                try:
                    program_data_base64 = str(log_entry).split("Program data: ")[1]
                    program_data_bytes = base64.b64decode(program_data_base64)
                except Exception as e:
                    print(f"Error decoding base64 program data: {e}")
                    continue

                try:
                    parsed_data = trade.parse(program_data_bytes)
                    trade_data = format_trade(parsed_data, txn_sig)
                    if trade_data:
                        print(trade_data)
                except Exception as e:
                    print(f"Error parsing or formatting trade data: {e}")

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