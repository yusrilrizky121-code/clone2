import imaplib, email
from email.header import decode_header

IMAP_USER    = "yusrilrizky121@gmail.com"
IMAP_PASS    = "mhyjenewwghdkbow"
ADMIN_SENDER = "yusrilrizky149@gmail.com"

def _decode_str(s):
    if s is None: return ""
    parts = decode_header(s)
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)

def _get_body(msg):
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

try:
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(IMAP_USER, IMAP_PASS)
    mail.select("INBOX")
    # Cari semua email (tidak filter sender dulu)
    status, data = mail.search(None, "ALL")
    ids = data[0].split() if data[0] else []
    print(f"Total emails in inbox: {len(ids)}")
    if ids:
        # Ambil 3 terbaru
        for mid in ids[-3:]:
            s2, md = mail.fetch(mid, "(RFC822)")
            msg = email.message_from_bytes(md[0][1])
            sender = _decode_str(msg.get("From", ""))
            subject = _decode_str(msg.get("Subject", ""))
            print(f"  From: {sender} | Subject: {subject}")
    mail.logout()
    print("\nAPI akan bekerja saat ada email dari:", ADMIN_SENDER)
except Exception as e:
    print("ERROR:", e)
