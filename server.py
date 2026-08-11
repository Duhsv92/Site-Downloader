import os
# type: ignore # pyrefly: ignore [missing-import]
import requests
# type: ignore # pyrefly: ignore [missing-import]
from flask import Flask, jsonify, request, send_from_directory

try:
    # type: ignore # pyrefly: ignore [missing-import]
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__, static_folder='.')

# ==============================================================================
# 🔑 CONFIGURAÇÃO DA API COBALT / LINK DA API KEY
# ==============================================================================
# Para trocar o link da API, altere o arquivo .env (COBALT_API_URL=...)
# ou nas Variáveis de Ambiente da hospedagem (ex: Vercel / Railway).
# Você também pode trocar o valor padrão na variável DEFAULT_COBALT_URL abaixo:
# ==============================================================================

DEFAULT_COBALT_URL = "https://api-production-664d8.up.railway.app"

raw_url = os.environ.get("COBALT_API_URL", DEFAULT_COBALT_URL).strip().rstrip("/")
if raw_url and not (raw_url.startswith("http://") or raw_url.startswith("https://")):
    COBALT_API_URL = f"https://{raw_url}"
else:
    COBALT_API_URL = raw_url

COBALT_API_KEY = os.environ.get("COBALT_API_KEY", "")

ALLOWED_DOMAINS = (
    "instagram.com",
    "instagr.am",
    "facebook.com",
    "fb.watch",
    "fb.com",
    "m.facebook.com",
    "tiktok.com",
    "vm.tiktok.com",
)

def is_allowed_url(url):
    if not url:
        return False
    lower = url.lower()
    return any(domain in lower for domain in ALLOWED_DOMAINS)


@app.route("/")
def serve_index():
    return send_from_directory(".", "index.html")


@app.route("/<path:path>")
def serve_static(path):
    if os.path.exists(os.path.join(".", path)):
        return send_from_directory(".", path)
    return send_from_directory(".", "index.html")


@app.route("/api/download", methods=["POST"])
def api_download():
    if not COBALT_API_URL:
        return jsonify({
            "status": "error",
            "error": {
                "code": "error.api.configuration"
            }
        }), 500

    body = request.get_json(silent=True)

    if not body or not isinstance(body.get("url"), str):
        return jsonify({
            "status": "error",
            "error": {
                "code": "error.api.link.invalid"
            }
        }), 400

    url = body["url"].strip()

    if not url or not is_allowed_url(url):
        return jsonify({
            "status": "error",
            "error": {
                "code": "error.api.link.invalid"
            }
        }), 400

    payload = {
        "url": url,
        "videoQuality": body.get("videoQuality", "1080"),
        "filenameStyle": body.get("filenameStyle", "pretty"),
        "downloadMode": body.get("downloadMode", "auto"),
        "audioFormat": body.get("audioFormat", "mp3"),
        "audioBitrate": body.get("audioBitrate", "320"),
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    if COBALT_API_KEY:
        headers["Authorization"] = f"Bearer {COBALT_API_KEY}"

    try:
        response = requests.post(
            COBALT_API_URL,
            json=payload,
            headers=headers,
            timeout=60
        )

        data = response.json()
        return jsonify(data), response.status_code

    except requests.Timeout:
        return jsonify({
            "status": "error",
            "error": {
                "code": "error.api.timeout"
            }
        }), 504

    except requests.RequestException:
        return jsonify({
            "status": "error",
            "error": {
                "code": "error.api.fetch.fail"
            }
        }), 502

    except ValueError:
        return jsonify({
            "status": "error",
            "error": {
                "code": "error.api.fetch.critical"
            }
        }), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
