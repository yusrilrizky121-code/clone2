from http.server import BaseHTTPRequestHandler
import json, urllib.request, urllib.error

# Firestore REST API — baca document "announcements/current"
# Rules Firestore harus: allow read: if true; (untuk collection announcements)
FIRESTORE_PROJECT = "auspoty-web"
FIRESTORE_API_KEY = "AIzaSyAYJEVXTS17vEX4J6_ymevMiJUnWV-Xf8Q"

FIRESTORE_URL = (
    f"https://firestore.googleapis.com/v1/projects/{FIRESTORE_PROJECT}"
    f"/databases/(default)/documents/announcements/current"
    f"?key={FIRESTORE_API_KEY}"
)


def _val(field: dict, default=""):
    """Ambil nilai dari Firestore field value object."""
    for k in ("stringValue", "integerValue", "booleanValue"):
        if k in field:
            return field[k]
    return default


def fetch_from_firestore():
    try:
        req = urllib.request.Request(
            FIRESTORE_URL,
            headers={"Accept": "application/json", "User-Agent": "AuspotyServer/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        fields = data.get("fields", {})
        status   = _val(fields.get("status",  {"stringValue": "none"}))
        title    = _val(fields.get("title",   {"stringValue": ""}))
        message  = _val(fields.get("message", {"stringValue": ""}))
        ann_id   = _val(fields.get("id",      {"stringValue": ""}))
        ann_type = _val(fields.get("type",    {"stringValue": "info"}))
        if status != "success":
            return {"status": "none"}
        return {
            "status":  "success",
            "id":      str(ann_id),
            "title":   str(title)[:100],
            "message": str(message)[:500],
            "type":    str(ann_type),
        }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"status": "none"}
        return {"status": "error", "message": f"Firestore HTTP {e.code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _cors(handler_self, code=200):
    handler_self.send_response(code)
    handler_self.send_header("Content-Type", "application/json")
    handler_self.send_header("Access-Control-Allow-Origin", "*")
    handler_self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
    handler_self.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler_self.end_headers()


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        result = fetch_from_firestore()
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
