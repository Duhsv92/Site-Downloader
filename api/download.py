import os
# type: ignore # pyrefly: ignore [missing-import]
import requests
# type: ignore # pyrefly: ignore [missing-import]
import shutil
from flask import Flask, jsonify, request, send_file

# Módulo de download do YouTube via yt-dlp
from ytdlp import (
    build_youtube_result,
    decode_url,
    download_to_temp,
    is_youtube_url,
    map_ytdlp_error,
    schedule_cleanup,
)

try:
    # type: ignore # pyrefly: ignore [missing-import]
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)

# ==============================================================================
# 🔑 CONFIGURAÇÃO DA API COBALT / LINK DA API KEY
# ==============================================================================
# Para trocar o link da API, altere o arquivo .env (COBALT_API_URL=...)
# ou nas Variáveis de Ambiente na Vercel / Railway.
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
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "vm.tiktok.com",
)


# ============================================================
# VALIDAÇÃO
# ============================================================

def is_allowed_url(url: str) -> bool:
    if not url:
        return False

    lower = url.lower()

    return any(
        domain in lower
        for domain in ALLOWED_DOMAINS
    )


# ============================================================
# API DOWNLOAD
# ============================================================

@app.route("/api/download", methods=["POST"])
@app.route("/download", methods=["POST"])
@app.route("/", methods=["POST"])
def api_download():

    # Verifica se a URL da Cobalt foi configurada
    if not COBALT_API_URL:
        return jsonify({
            "status": "error",
            "error": {
                "code": "error.api.configuration"
            }
        }), 500

    # Tenta ler JSON
    body = request.get_json(silent=True)

    if not body or not isinstance(body.get("url"), str):
        return jsonify({
            "status": "error",
            "error": {
                "code": "error.api.link.invalid"
            }
        }), 400

    url = body["url"].strip()

    # ========================================================
    # YOUTUBE -> yt-dlp (novo método de download)
    # ========================================================
    if is_youtube_url(url):
        try:
            return jsonify(
                build_youtube_result(url, body.get("videoQuality", "1080"))
            ), 200
        except Exception as exc:
            return jsonify({
                "status": "error",
                "error": {"code": map_ytdlp_error(exc)}
            }), 400

    # ========================================================
    # DEMAIS PLATAFORMAS -> API Cobalt (fluxo original)
    # ========================================================

    # Validação da URL
    if not url or not is_allowed_url(url):
        return jsonify({
            "status": "error",
            "error": {
                "code": "error.api.link.invalid"
            }
        }), 400

    # ========================================================
    # PAYLOAD PARA COBALT
    # ========================================================

    payload = {
        "url": url,
        "videoQuality": body.get(
            "videoQuality",
            "1080"
        ),
        "filenameStyle": body.get(
            "filenameStyle",
            "pretty"
        ),
        "downloadMode": body.get(
            "downloadMode",
            "auto"
        ),
        "audioFormat": body.get(
            "audioFormat",
            "mp3"
        ),
        "audioBitrate": body.get(
            "audioBitrate",
            "320"
        ),
    }

    # ========================================================
    # HEADERS
    # ========================================================

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    if COBALT_API_KEY:
        headers["Authorization"] = (
            f"Bearer {COBALT_API_KEY}"
        )

    # ========================================================
    # REQUISIÇÃO PARA COBALT
    # ========================================================

    try:

        response = requests.post(
            COBALT_API_URL,
            json=payload,
            headers=headers,
            timeout=60
        )

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

    # ========================================================
    # RESPOSTA
    # ========================================================

    try:

        data = response.json()

    except ValueError:

        return jsonify({
            "status": "error",
            "error": {
                "code": "error.api.fetch.critical"
            }
        }), 502

    return jsonify(data), response.status_code


# ============================================================
# DOWNLOAD YOUTUBE VIA YT-DLP (stream do arquivo final)
# ============================================================

@app.route("/api/yt-dlp/download", methods=["GET"])
def ytdlp_download():
    token = request.args.get("q", "")
    mode = request.args.get("m", "video")
    quality = request.args.get("qty", "1080")

    try:
        url = decode_url(token)
    except Exception:
        return jsonify({
            "status": "error",
            "error": {"code": "error.api.link.invalid"}
        }), 400

    if not is_youtube_url(url):
        return jsonify({
            "status": "error",
            "error": {"code": "error.api.link.invalid"}
        }), 400

    try:
        filepath, filename, tmpdir = download_to_temp(url, mode, quality)
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": {"code": map_ytdlp_error(exc)}
        }), 400

    response = send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        conditional=True,
    )

    # Remove o arquivo temporário após o término do envio ao cliente
    response.call_on_close(
        lambda: shutil.rmtree(tmpdir, ignore_errors=True)
    )
    schedule_cleanup(tmpdir)
    return response


# ============================================================
# VERCEL / SERVERLESS HANDLER
# ============================================================

# A Vercel utiliza a instância Flask 'app' ou 'handler' como ponto de entrada.
handler = app

