import imaplib, email
from email.header import decode_header

IMAP_USER    = "yusrilrizky121@gmail.com"
IMAP_PASS    = "mhyjenewwghdkbow"
ADMIN_SENDER = "yusrilrizky149@gmail.com"

try:
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(IMAP_USER, IMAP_PASS)
    mail.select("INBOX")
    status, data = mail.search(None, 'FROM', ADMIN_SENDER)
    ids = data[0].split() if data[0] else []
    print("Login OK, emails from admin:", len(ids))
    if ids:
        status2, msg_data = mail.fetch(ids[-1], "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        subj_raw = msg.get("Subject", "(none)")
        parts = decode_header(subj_raw)
        subj = "".join(p.decode(e or "utf-8") if isinstance(p, bytes) else p for p, e in parts)
        print("Latest subject:", subj)
    mail.logout()
except Exception as e:
    print("ERROR:", e)
