from http.server import BaseHTTPRequestHandler
import json, imaplib, email, re
from email.header import decode_header

# ── Kredensial Gmail inbox yang dipantau ─────────────────────────────────────
IMAP_USER     = "yusrilrizky121@gmail.com"
IMAP_PASS     = "mhyjenewwghdkbow"   # App Password (tanpa spasi)
IMAP_HOST     = "imap.gmail.com"
ADMIN_SENDER  = "yusrilrizky149@gmail.com"   # satu-satunya yang boleh kirim
# ─────────────────────────────────────────────────────────────────────────────

def _decode_str(s):
    """Decode encoded email header string."""
    if s is None:
        return ""
    parts = decode_header(s)
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)

def _get_body(msg):
    """Ambil plain-text body dari email."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace").strip()
    else:
        charset = msg.get_content_charset() or "utf-8"
        return msg.get_payload(decode=True).decode(charset, errors="replace").strip()
    return ""

def fetch_latest_announcement():
    """
    Konek ke Gmail via IMAP, cari email terbaru dari ADMIN_SENDER,
    kembalikan dict announcement atau None.
    """
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, 993)
        mail.login(IMAP_USER, IMAP_PASS)
        mail.select("INBOX")

        # Cari email dari admin sender
        status, data = mail.search(None, f'FROM "{ADMIN_SENDER}"')
        if status != "OK" or not data[0]:
            mail.logout()
            return None

        ids = data[0].split()
        # Ambil email terbaru (id terakhir)
        latest_id = ids[-1]
        status, msg_data = mail.fetch(latest_id, "(RFC822)")
        mail.logout()

        if status != "OK":
            return None

        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        subject = _decode_str(msg.get("Subject", "Auspoty"))
        body    = _get_body(msg)
        msg_id  = msg.get("Message-ID", latest_id.decode())

        # Deteksi tipe dari subject/body
        lower = (subject + body).lower()
        if any(w in lower for w in ["update", "versi", "version", "rilis"]):
            ann_type = "update"
        elif any(w in lower for w in ["peringatan", "warning", "penting", "urgent"]):
            ann_type = "warning"
        elif any(w in lower for w in ["promo", "diskon", "gratis", "free"]):
            ann_type = "promo"
        else:
            ann_type = "info"

        return {
            "status":  "success",
            "id":      str(msg_id).strip(),
            "title":   subject[:100] if subject.strip() else (body[:60] + "..." if len(body) > 60 else body) or "Pesan dari Admin",
            "message": body[:500] if body else subject or "Ada pesan baru dari admin.",
            "type":    ann_type,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _cors(handler_self, code=200):
    handler_self.send_response(code)
    handler_self.send_header("Content-Type", "application/json")
    handler_self.send_header("Access-Control-Allow-Origin", "*")
    handler_self.end_headers()


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        result = fetch_latest_announcement()
        if result is None:
            result = {"status": "none"}
        _cors(self)
        self.wfile.write(json.dumps(result).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass
