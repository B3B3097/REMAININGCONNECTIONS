# -*- coding: utf-8 -*-
"""Real MTProto proxy validation: obfuscated2 handshake + req_pq_multi/resPQ.
Protocol spec: core.telegram.org/mtproto/mtproto-transports. Synchronous,
socket-based, depends only on `cryptography`."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import socket
import struct
import time

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

PROTO_ABRIDGED = b"\xef\xef\xef\xef"
PROTO_INTERMEDIATE = b"\xee\xee\xee\xee"
PROTO_SECURE = b"\xdd\xdd\xdd\xdd"

REQ_PQ_MULTI = 0xBE7E8EF1
RES_PQ = 0x05162463

MAX_FRAME = 2 * 1024 * 1024
FAKETLS_DEFAULT_DOMAIN = "www.google.com"
DEFAULT_DCS = (2, 1, 3, 4, 5)
FAKETLS_CLIENT_HELLO_LEN = 517
FAKETLS_MAX_APP_DATA = 1425
FAKETLS_CCS = b"\x14\x03\x03\x00\x01\x01"
FAKETLS_APP_DATA_PREFIX = b"\x17\x03\x03"


class ProtocolError(Exception):
    pass


def aes_ctr(key: bytes, iv: bytes):
    return Cipher(algorithms.AES(key), modes.CTR(iv)).encryptor()


def _extract_domain(blob: bytes) -> str:
    text = blob.rstrip(b"\x00").decode("ascii", "ignore")
    text = "".join(ch for ch in text if ch.isprintable())
    text = text.lstrip("\x00\r\n\t ")
    common_tlds = (".com", ".net", ".org", ".ir", ".ru", ".io", ".co", ".dev",
                   ".app", ".cloud", ".me", ".info")
    best = None
    for tld in common_tlds:
        pos = text.find(tld)
        if pos == -1:
            continue
        end = pos + len(tld)
        if best is None or end > best:
            best = end
    if best is None:
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"
        cleaned = "".join(ch for ch in text if ch in allowed)
        return cleaned[:253] or FAKETLS_DEFAULT_DOMAIN
    domain = text[:best]
    while domain and not domain[0].isalnum():
        domain = domain[1:]
    return domain or FAKETLS_DEFAULT_DOMAIN


def parse_secret(secret: str) -> dict:
    """Parse MTProxy secret: raw hex, dd/ee-prefixed hex, extended, base64url."""
    s = (secret or "").strip()
    lower = s.lower()
    if not s:
        raise ValueError("empty secret")

    def _hex_ok(value: str) -> bool:
        return all(c in "0123456789abcdef" for c in value)

    try:
        raw = bytes.fromhex(lower)
        hex_parsed = True
    except ValueError:
        hex_parsed = False

    if hex_parsed:
        if lower.startswith("ee"):
            if len(lower) < 34:
                raise ValueError("EE/FakeTLS secret too short")
            domain = ""
            if len(lower) > 34:
                try:
                    domain = bytes.fromhex(lower[34:]).decode("ascii", "ignore").rstrip("\x00")
                except ValueError:
                    domain = ""
            return {"raw": bytes.fromhex(lower[2:34]), "kind": "faketls",
                    "domain": domain or FAKETLS_DEFAULT_DOMAIN,
                    "display": lower[:70]}
        if lower.startswith("dd"):
            if len(lower) < 34:
                raise ValueError("DD secret too short")
            return {"raw": bytes.fromhex(lower[2:34]), "kind": "dd",
                    "domain": "", "display": lower[:70]}
        if len(raw) > 16:
            return {"raw": raw[:16], "kind": "extended", "domain": "",
                    "display": raw[:16].hex()}
        if len(raw) != 16:
            raise ValueError(f"hex secret decoded to {len(raw)} bytes, expected 16")
        return {"raw": raw, "kind": "raw", "domain": "", "display": lower}

    b64 = s.replace("-", "+").replace("_", "/")
    b64 += "=" * ((4 - len(b64) % 4) % 4)
    try:
        raw = base64.b64decode(b64, validate=False)
    except Exception as exc2:
        raise ValueError(f"secret is neither hex nor base64: {exc2}")
    if len(raw) == 16:
        return {"raw": raw, "kind": "raw", "domain": "", "display": raw.hex()}
    if len(raw) >= 17 and raw[0] == 0xDD:
        return {"raw": raw[1:17], "kind": "dd", "domain": "",
                "display": "dd" + raw[1:17].hex()}
    if len(raw) >= 17 and raw[0] == 0xEE:
        domain = _extract_domain(raw[17:])
        return {"raw": raw[1:17], "kind": "faketls", "domain": domain,
                "display": "ee" + raw[1:17].hex()}
    if len(raw) > 16:
        return {"raw": raw[:16], "kind": "extended", "domain": "",
                "display": raw[:16].hex()}
    raise ValueError(f"base64 secret decoded to {len(raw)} bytes, expected >= 16")


def _x25519_public() -> bytes:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import x25519
    priv = x25519.X25519PrivateKey.generate()
    return priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def make_faketls_client_hello(secret16: bytes, domain: str):
    domain_bytes = (domain or FAKETLS_DEFAULT_DOMAIN).encode("ascii", "ignore")
    greases = [(v & 0xF0) + 0x0A for v in os.urandom(7)]
    for i in range(1, len(greases), 2):
        if greases[i] == greases[i - 1]:
            greases[i] = 0x10 ^ greases[i]
    out = bytearray()
    out += b"\x16\x03\x01\x02\x00\x01\x00\x01\xfc\x03\x03"
    random_offset = len(out)
    out += b"\x00" * 32
    out += b"\x20" + os.urandom(32)
    out += b"\x00\x22"
    out += bytes([greases[0], greases[0]])
    out += (b"\x13\x01\x13\x02\x13\x03\xc0\x2b\xc0\x2f\xc0\x2c\xc0\x30"
            b"\xcc\xa9\xcc\xa8\xc0\x13\xc0\x14\x00\x9c\x00\x9d\x00\x2f"
            b"\x00\x35\x00\x0a\x01\x00\x01\x91")
    out += bytes([greases[2], greases[2]])
    out += b"\x00\x00\x00\x00"
    out += struct.pack(">H", len(domain_bytes) + 5)
    out += struct.pack(">H", len(domain_bytes) + 3)
    out += b"\x00"
    out += struct.pack(">H", len(domain_bytes))
    out += domain_bytes
    out += b"\x00\x17\x00\x00\xff\x01\x00\x01\x00\x00\x0a\x00\x0a\x00\x08"
    out += bytes([greases[4], greases[4]])
    out += (b"\x00\x1d\x00\x17\x00\x18\x00\x0b\x00\x02\x01\x00\x00\x23\x00\x00"
            b"\x00\x10\x00\x0e\x00\x0c\x02\x68\x32\x08\x68\x74\x74\x70\x2f\x31"
            b"\x2e\x31\x00\x05\x00\x05\x01\x00\x00\x00\x00\x00\x0d\x00\x14\x00"
            b"\x12\x04\x03\x08\x04\x04\x01\x05\x03\x08\x05\x05\x01\x08\x06\x06"
            b"\x01\x02\x01\x00\x12\x00\x00\x00\x33\x00\x2b\x00\x29")
    out += bytes([greases[4], greases[4]])
    out += b"\x00\x01\x00\x00\x1d\x00\x20"
    out += _x25519_public()
    out += b"\x00\x2d\x00\x02\x01\x01\x00\x2b\x00\x0b\x0a"
    out += bytes([greases[6], greases[6]])
    out += b"\x03\x04\x03\x03\x03\x02\x03\x01\x00\x1b\x00\x03\x02\x00\x02"
    out += bytes([greases[3], greases[3]])
    out += b"\x00\x01\x00\x00\x15"
    padding_length = FAKETLS_CLIENT_HELLO_LEN - 2 - len(out)
    if padding_length < 0:
        raise ProtocolError("ClientHello too long")
    out += struct.pack(">H", padding_length) + b"\x00" * padding_length
    if len(out) != FAKETLS_CLIENT_HELLO_LEN:
        raise ProtocolError(f"bad ClientHello length {len(out)}")
    digest = hmac.new(secret16, bytes(out), hashlib.sha256).digest()
    ts = int(time.time())
    tail = struct.unpack("<I", digest[28:32])[0] ^ ts
    client_random = digest[:28] + struct.pack("<I", tail)
    out[random_offset:random_offset + 32] = client_random
    return bytes(out), client_random


def validate_faketls_response(secret16: bytes, client_random: bytes, response: bytes):
    if len(response) < 43:
        raise ProtocolError("short FakeTLS server response")
    server_random = response[11:43]
    zeroed = bytearray(response)
    zeroed[11:43] = b"\x00" * 32
    expected = hmac.new(secret16, client_random + bytes(zeroed), hashlib.sha256).digest()
    if not hmac.compare_digest(server_random, expected):
        raise ProtocolError("FakeTLS server random HMAC mismatch")


class _Sock:
    def __init__(self, sock):
        self.sock = sock

    def write(self, data: bytes):
        self.sock.sendall(data)

    def read_exact(self, n: int) -> bytes:
        out = bytearray()
        while len(out) < n:
            chunk = self.sock.recv(n - len(out))
            if not chunk:
                raise ProtocolError(f"connection closed, got {len(out)}/{n}")
            out += chunk
        return bytes(out)


class FakeTlsTransport:
    def __init__(self, sock, secret16: bytes, domain: str):
        self.sock = _Sock(sock)
        self.secret = secret16
        self.domain = domain or FAKETLS_DEFAULT_DOMAIN
        self.buffer = bytearray()
        self.first_write = True

    def handshake(self):
        hello, client_random = make_faketls_client_hello(self.secret, self.domain)
        self.sock.write(hello)
        header = self.sock.read_exact(5)
        rtype, plen = self._parse(header)
        if rtype != 0x16:
            raise ProtocolError(f"expected ServerHello, got 0x{rtype:02x}")
        payload = self.sock.read_exact(plen)
        ccs = self.sock.read_exact(len(FAKETLS_CCS))
        if ccs != FAKETLS_CCS:
            raise ProtocolError("bad FakeTLS ChangeCipherSpec")
        app_header = self.sock.read_exact(5)
        atype, aplen = self._parse(app_header)
        if atype != 0x17:
            raise ProtocolError(f"expected AppData, got 0x{atype:02x}")
        app_payload = self.sock.read_exact(aplen)
        response = header + payload + ccs + app_header + app_payload
        validate_faketls_response(self.secret, client_random, response)

    def write(self, data: bytes):
        out = bytearray()
        if self.first_write:
            out += FAKETLS_CCS
            self.first_write = False
        for off in range(0, len(data), FAKETLS_MAX_APP_DATA):
            chunk = data[off:off + FAKETLS_MAX_APP_DATA]
            out += FAKETLS_APP_DATA_PREFIX + struct.pack(">H", len(chunk)) + chunk
        self.sock.write(bytes(out))

    def read_exact(self, n: int) -> bytes:
        while len(self.buffer) < n:
            header = self.sock.read_exact(5)
            rtype, plen = self._parse(header)
            payload = self.sock.read_exact(plen)
            if rtype == 0x14 and payload == b"\x01":
                continue
            if rtype != 0x17:
                raise ProtocolError(f"expected AppData, got 0x{rtype:02x}")
            self.buffer += payload
        out = bytes(self.buffer[:n])
        del self.buffer[:n]
        return out

    @staticmethod
    def _parse(header: bytes):
        if len(header) != 5:
            raise ProtocolError("short TLS record header")
        rtype = header[0]
        if header[1:3] not in (b"\x03\x01", b"\x03\x03"):
            raise ProtocolError("bad TLS record version")
        return rtype, struct.unpack(">H", header[3:5])[0]


def make_obfuscated2_handshake(secret16: bytes, proto_tag: bytes, dc_id: int):
    forbidden = {b"GET ", b"POST", b"HEAD", b"OPTI", b"\x00\x00\x00\x00",
                 PROTO_ABRIDGED, PROTO_INTERMEDIATE, PROTO_SECURE}
    while True:
        init = bytearray(os.urandom(64))
        if init[0] == 0xEF:
            continue
        if bytes(init[:4]) in forbidden:
            continue
        if bytes(init[4:8]) == b"\x00\x00\x00\x00":
            continue
        break
    init[56:60] = proto_tag
    init[60] = dc_id & 0xFF
    init[61:64] = b"\x00\x00\x00"

    enc_key = hashlib.sha256(bytes(init[8:40]) + secret16).digest()
    dec_key = hashlib.sha256(bytes(init[55:23:-1]) + secret16).digest()
    enc_iv = bytes(init[40:56])
    dec_iv = bytes(init[23:7:-1])

    enc = aes_ctr(enc_key, enc_iv)
    dec = aes_ctr(dec_key, dec_iv)

    encrypted = enc.update(bytes(init))
    init[56:64] = encrypted[56:64]
    return bytes(init), enc, dec


def make_req_pq_multi():
    nonce = os.urandom(16)
    payload = struct.pack("<I", REQ_PQ_MULTI) + nonce
    msg_id = int(time.time() * (2 ** 32)) & ~3
    packet = (b"\x00" * 8 + struct.pack("<Q", msg_id)
              + struct.pack("<I", len(payload)) + payload)
    return nonce, packet


def frame_message(data: bytes, mode: str) -> bytes:
    if mode == "secure":
        pad_len = os.urandom(1)[0] % 4
        return struct.pack("<I", len(data) + pad_len) + data + os.urandom(pad_len)
    if mode == "intermediate":
        return struct.pack("<I", len(data)) + data
    if mode == "abridged":
        if len(data) % 4:
            raise ProtocolError("abridged payload must be 4-aligned")
        words = len(data) // 4
        if words < 127:
            return struct.pack("<B", words) + data
        return b"\x7f" + struct.pack("<I", words)[:3] + data
    raise ProtocolError(f"unsupported mode {mode}")


def read_frame(transport, dec, mode: str) -> bytes:
    if mode in ("secure", "intermediate"):
        raw_len = transport.read_exact(4)
        length = struct.unpack("<I", dec.update(raw_len))[0]
        if length > 0x80000000:
            length -= 0x80000000
        if length <= 0 or length > MAX_FRAME:
            raise ProtocolError(f"bad frame length {length}")
        return dec.update(transport.read_exact(length))
    if mode == "abridged":
        first = dec.update(transport.read_exact(1))[0]
        if first < 127:
            flen = first * 4
        else:
            rest = dec.update(transport.read_exact(3))
            flen = struct.unpack("<I", rest + b"\x00")[0] * 4
        if flen <= 0 or flen > MAX_FRAME:
            raise ProtocolError(f"bad abridged length {flen}")
        return dec.update(transport.read_exact(flen))
    raise ProtocolError(f"unsupported mode {mode}")


def parse_res_pq(frame: bytes, expected_nonce: bytes) -> str:
    if len(frame) < 40:
        raise ProtocolError(f"short MTProto response {len(frame)}")
    if frame[:8] != b"\x00" * 8:
        raise ProtocolError("not unencrypted MTProto (auth_key_id != 0)")
    msg_len = struct.unpack("<I", frame[16:20])[0]
    if msg_len <= 0 or msg_len > len(frame) - 20:
        raise ProtocolError("bad MTProto message length")
    body = frame[20:20 + msg_len]
    if len(body) < 36:
        raise ProtocolError("short MTProto body")
    ctor = struct.unpack("<I", body[:4])[0]
    if ctor != RES_PQ:
        raise ProtocolError(f"unexpected constructor 0x{ctor:08x}")
    if body[4:20] != expected_nonce:
        raise ProtocolError("resPQ nonce mismatch")
    return body[20:36].hex()


def check_once(host, port, secret_str, dc_id, mode, connect_timeout, response_timeout):
    started = time.monotonic()
    parsed = parse_secret(secret_str)
    secret16 = parsed["raw"]
    inner_mode = "secure" if mode == "faketls" else mode
    tag = {"abridged": PROTO_ABRIDGED, "intermediate": PROTO_INTERMEDIATE,
           "secure": PROTO_SECURE}[inner_mode]
    sock = None
    try:
        sock = socket.create_connection((host, int(port)), timeout=connect_timeout)
        sock.settimeout(response_timeout)
        if mode == "faketls":
            transport = FakeTlsTransport(sock, secret16, parsed["domain"])
            transport.handshake()
        else:
            transport = _Sock(sock)
        init_packet, enc, dec = make_obfuscated2_handshake(secret16, tag, dc_id)
        transport.write(init_packet)
        nonce, req = make_req_pq_multi()
        transport.write(enc.update(frame_message(req, inner_mode)))
        frame = read_frame(transport, dec, inner_mode)
        server_nonce = parse_res_pq(frame, nonce)
        rtt = (time.monotonic() - started) * 1000
        return {"ok": True, "rtt_ms": round(rtt, 2), "error": None, "detail": None,
                "dc": dc_id, "mode": mode, "server_nonce": server_nonce}
    except ProtocolError as exc:
        return {"ok": False, "rtt_ms": None, "error": "protocol_error",
                "detail": str(exc), "dc": dc_id, "mode": mode, "server_nonce": None}
    except socket.timeout as exc:
        return {"ok": False, "rtt_ms": None, "error": "timeout", "detail": str(exc),
                "dc": dc_id, "mode": mode, "server_nonce": None}
    except (OSError, ConnectionError) as exc:
        return {"ok": False, "rtt_ms": None, "error": "network_error",
                "detail": f"{type(exc).__name__}: {exc}", "dc": dc_id, "mode": mode,
                "server_nonce": None}
    finally:
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass


def check_proxy(host, port, secret, timeout=8.0, dcs=DEFAULT_DCS):
    try:
        parsed = parse_secret(secret)
    except ValueError as exc:
        return {"ok": False, "rtt_ms": None, "error": "invalid_secret",
                "detail": str(exc), "dc": None, "mode": None, "server_nonce": None}
    if parsed["kind"] == "faketls":
        modes = ("faketls",)
    elif parsed["kind"] == "dd":
        modes = ("secure",)
    else:
        modes = ("secure", "abridged", "intermediate")
    result = None
    for dc_id in dcs:
        for mode in modes:
            result = check_once(host, port, secret, dc_id, mode, timeout, timeout)
            if result["ok"]:
                return result
    return result


def main():
    import argparse
    import json as _json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--secret", required=True)
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()
    result = check_proxy(args.host, args.port, args.secret, timeout=args.timeout)
    print(_json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
