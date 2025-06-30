import websocket
import json
import base64
import struct
from dataclasses import dataclass, asdict
from solders.pubkey import Pubkey  # type: ignore

WSS = "wss://mainnet.helius-rpc.com/?api-key="

# 8-byte discriminator + 3×4-byte lengths + 4×32-byte pubkeys + 5×8-byte ints = 188 bytes
_MIN_CREATE_EVENT_SIZE = 188

@dataclass
class CreateEvent:
    name: str
    symbol: str
    uri: str
    mint: str
    bonding_curve: str
    user: str
    creator: str
    timestamp: int
    virtual_token_reserves: int
    virtual_sol_reserves: int
    real_token_reserves: int
    token_total_supply: int


def parse_create_event(data_hex: str) -> CreateEvent:
    data = bytes.fromhex(data_hex)
    offset = 8  # skip discriminator/padding

    def read_length_prefixed_string() -> str:
        nonlocal offset
        # ensure there's room for length prefix
        if offset + 4 > len(data):
            raise ValueError("Not enough data for string length")
        (length,) = struct.unpack_from("<I", data, offset)
        offset += 4
        if length < 0 or offset + length > len(data):
            raise ValueError(f"Invalid string length {length}")
        raw = data[offset : offset + length]
        offset += length
        return raw.decode("utf-8", errors="replace").rstrip("\x00")

    def read_pubkey_str() -> str:
        nonlocal offset
        if offset + 32 > len(data):
            raise ValueError("Not enough data for pubkey")
        pk_bytes = data[offset : offset + 32]
        offset += 32
        return str(Pubkey.from_bytes(pk_bytes))

    # parse fields
    name = read_length_prefixed_string()
    symbol = read_length_prefixed_string()
    uri = read_length_prefixed_string()
    mint = read_pubkey_str()
    bonding_curve = read_pubkey_str()
    user = read_pubkey_str()
    creator = read_pubkey_str()

    # signed 64-bit timestamp
    if offset + 8 > len(data):
        raise ValueError("Not enough data for timestamp")
    (timestamp,) = struct.unpack_from("<q", data, offset)
    offset += 8

    # unsigned 64-bit reserves and supply
    def read_u64() -> int:
        nonlocal offset
        if offset + 8 > len(data):
            raise ValueError("Not enough data for u64")
        (val,) = struct.unpack_from("<Q", data, offset)
        offset += 8
        return val

    virtual_token_reserves = read_u64()
    virtual_sol_reserves = read_u64()
    real_token_reserves = read_u64()
    token_total_supply = read_u64()

    return CreateEvent(
        name=name,
        symbol=symbol,
        uri=uri,
        mint=mint,
        bonding_curve=bonding_curve,
        user=user,
        creator=creator,
        timestamp=timestamp,
        virtual_token_reserves=virtual_token_reserves,
        virtual_sol_reserves=virtual_sol_reserves,
        real_token_reserves=real_token_reserves,
        token_total_supply=token_total_supply,
    )


def on_message(ws, message):
    try:
        payload = json.loads(message)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return

    logs = payload.get("params", {}).get("result", {}).get("value", {}).get("logs", [])

    if any("Instruction: InitializeMint2" in log for log in logs):
        for entry in logs:
            # skip vdt/logs that aren't our CreateEvent struct
            if not entry.startswith("Program data: "):
                continue
            if entry.startswith("Program data: vdt/"):
                continue

            b64 = entry.split("Program data: ", 1)[1]
            try:
                raw = base64.b64decode(b64)
            except Exception as e:
                print(f"Error decoding base64 program data: {e}")
                continue

            if len(raw) < _MIN_CREATE_EVENT_SIZE:
                continue

            try:
                event = parse_create_event(raw.hex())
                if event:
                    print(asdict(event))
                    break
            except Exception as e:
                print(f"Error parsing CreateEvent data: {e}")
                continue


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
            {"commitment": "processed"},
        ],
    }
    try:
        ws.send(json.dumps(sub_req))
        print("Subscribed to logs...")
    except Exception as e:
        print(f"Error sending subscription request: {e}")


def start_websocket():
    ws = websocket.WebSocketApp(
        WSS, on_message=on_message, on_error=on_error, on_close=on_close
    )
    ws.on_open = on_open
    ws.run_forever()


if __name__ == "__main__":
    try:
        start_websocket()
    except Exception as e:
        print(f"Unexpected error in main event loop: {e}")
