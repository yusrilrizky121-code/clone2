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
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(charset, errors="replace").strip()
    return ""

mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
mail.login(IMAP_USER, IMAP_PASS)
mail.select("INBOX")

# Cari email dari admin
status, data = mail.search(None, 'FROM', ADMIN_SENDER)
ids = data[0].split() if data[0] else []
print(f"Emails from {ADMIN_SENDER}: {len(ids)}")

for mid in ids[-3:]:
    s2, md = mail.fetch(mid, "(RFC822)")
    msg = email.message_from_bytes(md[0][1])
    subject = _decode_str(msg.get("Subject", "")) or "(no subject)"
    body    = _get_body(msg)
    msg_id  = msg.get("Message-ID", mid.decode())
    print(f"\n--- Email ID: {mid} ---")
    print(f"Subject : '{subject}'")
    print(f"Body    : '{body[:200]}'")
    print(f"Msg-ID  : {msg_id}")
    print(f"Content-Type: {msg.get_content_type()}")

mail.logout()
