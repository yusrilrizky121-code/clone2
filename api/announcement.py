from http.server import BaseHTTPRequestHandler
import json, urllib.request, urllib.error

# Firestore REST API — baca document "announcements/current"
FIRESTORE_PROJECT = "auspoty-web"
FIRESTORE_API_KEY = "AIzaSyAYJEVXTS17vEX4J6_ymevMiJUnWV-Xf8Q"
ADMIN_EMAIL       = "yusrilrizky149@gmail.com"

FIRESTORE_URL = (
    f"https://firestore.googleapis.com/v1/projects/{FIRESTORE_PROJECT}"
    f"/databases/(default)/documents/announcements/current"
    f"?key={FIRESTORE_API_KEY}"
)


def _parse_firestore_value(val: dict):
    """Ambil nilai dari Firestore value object."""
    if "stringValue" in val:
        return val["stringValue"]
    if "integerValue" in val:
        return int(val["integerValue"])
    if "booleanValue" in val:
        return val["booleanValue"]
    if "nullValue" in val:
        return None
    return str(val)


def fetch_from_firestore():
    """Baca announcement dari Firestore REST API."""
    try:
        req = urllib.request.Request(FIRESTORE_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        fields = data.get("fields", {})
        status  = _parse_firestore_value(fields.get("status",  {"stringValue": "none"}))
        title   = _parse_firestore_value(fields.get("title",   {"stringValue": ""}))
        message = _parse_firestore_value(fields.get("message", {"stringValue": ""}))
        ann_id  = _parse_firestore_value(fields.get("id",      {"stringValue": ""}))
        ann_type = _parse_firestore_value(fields.get("type",   {"stringValue": "info"}))
        if status != "success":
            return {"status": "none"}
        return {"status": "success", "id": ann_id, "title": title, "message": message, "type": ann_type}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"status": "none"}
        return {"status": "error", "message": f"HTTP {e.code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _cors_headers(handler_self, code=200):
    handler_self.send_response(code)
    handler_self.send_header("Content-Type", "application/json")
    handler_self.send_header("Access-Control-Allow-Origin", "*")
    handler_self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
    handler_self.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler_self.end_headers()


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        result = fetch_from_firestore()
        _cors_headers(self)
        self.wfile.write(json.dumps(result).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass
