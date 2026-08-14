import os
# type: ignore # pyrefly: ignore [missing-import]
import requests
# type: ignore # pyrefly: ignore [missing-import]
import shutil
# type: ignore # pyrefly: ignore [missing-import]
from flask import Flask, jsonify, request, send_file, send_from_directory

# Módulo de download do YouTube via yt-dlp (compartilhado com a função Vercel)
try:
    from api.ytdlp import (
        build_youtube_result,
        decode_url,
        download_to_temp,
        is_youtube_url,
        map_ytdlp_error,
        schedule_cleanup,
    )
except ImportError:
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
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "vm.tiktok.com",
)

def is_allowed_url(url):
    if not url:
        return False
    lower = url.lower()
    return any(domain in lower for domain in ALLOWED_DOMAINS)


def _cobalt_request(url, body):
    """Chama a API Cobalt (Instagram/Facebook/TikTok e fallback do YouTube).

    Retorna (data_json, status_code). Lança requests.Timeout, requests.RequestException
    ou ValueError em caso de falha."""
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

    response = requests.post(
        COBALT_API_URL,
        json=payload,
        headers=headers,
        timeout=60
    )

    data = response.json()
    return data, response.status_code


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

    # ========================================================
    # YOUTUBE -> yt-dlp (novo método de download)
    # ========================================================
    if is_youtube_url(url):
        try:
            return jsonify(
                build_youtube_result(url, body.get("videoQuality", "1080"))
            ), 200
        except Exception as exc:
            err_code = map_ytdlp_error(exc)
            # Log do erro real para diagnóstico nos logs
            print(f"[yt-dlp/metadata] ERRO: {exc}", flush=True)

            # Fallback automático: quando o YouTube bloqueia o IP de datacenter
            # da VM ("Sign in to confirm you're not a bot"), tenta a API Cobalt
            # (hospedada no Railway, que costuma passar nesse bloqueio).
            if err_code == "error.api.youtube.login" and COBALT_API_URL:
                try:
                    data, status = _cobalt_request(url, body)
                    print("[cobalt-fallback] YouTube OK via Cobalt", flush=True)
                    return jsonify(data), status
                except Exception as exc2:
                    print(f"[cobalt-fallback] ERRO: {exc2}", flush=True)

            return jsonify({
                "status": "error",
                "error": {"code": err_code}
            }), 400

    # ========================================================
    # DEMAIS PLATAFORMAS -> API Cobalt (fluxo original)
    # ========================================================

    if not url or not is_allowed_url(url):
        return jsonify({
            "status": "error",
            "error": {
                "code": "error.api.link.invalid"
            }
        }), 400

    try:
        data, status = _cobalt_request(url, body)
        return jsonify(data), status

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
        # Log do erro real para diagnóstico nos logs do Railway
        print(f"[yt-dlp/download] ERRO ({mode}): {exc}", flush=True)
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
