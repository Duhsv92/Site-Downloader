# ============================================================
# SaveClip — Download de vídeos/áudios do YouTube via yt-dlp
# Substitui a API Cobalt apenas para o YouTube.
# Requer: pip install yt-dlp  +  ffmpeg instalado no sistema.
# ============================================================

import base64
import glob
import os
import re
import shutil
import tempfile
import threading
import time

import yt_dlp

# Domínios do YouTube
YOUTUBE_DOMAINS = ("youtube.com", "youtu.be")

# Qualidade máxima padrão (em altura)
DEFAULT_QUALITY = 1080

# Extensões de saída
VIDEO_EXT = "mp4"
AUDIO_EXT = "mp3"


def is_youtube_url(url):
    """Verifica se a URL pertence ao YouTube."""
    if not url:
        return False
    lower = url.lower()
    return any(d in lower for d in YOUTUBE_DOMAINS)


# ============================================================
# FFMPEG (necessário para mesclar vídeo+áudio e converter MP3)
# ============================================================

def _find_ffmpeg():
    """Localiza o binário do ffmpeg."""
    # 1) Variável de ambiente explícita (FFMPEG_PATH)
    loc = os.environ.get("FFMPEG_PATH")
    if loc and os.path.exists(loc):
        return loc

    # 2) PATH do sistema
    path = shutil.which("ffmpeg")
    if path:
        return path

    # 3) Diretórios conhecidos do winget (Windows)
    try:
        candidates = glob.glob(
            os.path.expandvars(
                r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\*\*\bin\ffmpeg.exe"
            )
        )
        if candidates:
            return candidates[0]
    except Exception:
        pass

    # 4) imageio-ffmpeg (fallback via pip)
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _ffmpeg_location():
    """Retorna diretório/executável do ffmpeg para o yt-dlp, ou None."""
    ff = _find_ffmpeg()
    if not ff:
        return None
    d = os.path.dirname(ff)
    probe = os.path.join(d, "ffprobe" + os.path.splitext(ff)[1])
    if os.path.exists(probe):
        return d
    return ff


def _base_opts():
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 30,
        "retries": 3,
        "no_color": True,
        # Contorna o bloqueio "Sign in to confirm you're not a bot" do YouTube,
        # muito comum em IPs de datacenter (Railway, VPS, etc). Tenta vários
        # player clients (tv/android/ios) que são menos marcados como bot do
        # que o player "web" padrão.
        "extractor_args": {
            "youtube": {
                "player_client": ["tv", "android", "ios", "web_safari"]
            }
        },
    }

    # Cookies opcionais do YouTube — contorna o "Sign in to confirm you're not a
    # bot" em IPs de datacenter (VPS/Railway) para vídeos bloqueados seletivamente.
    # Defina a variável YTDLP_COOKIES com o caminho do arquivo cookies.txt DENTRO
    # do container (ex: /app/cookies.txt, montado pelo docker-compose).
    cookies_file = os.environ.get("YTDLP_COOKIES")
    if cookies_file and os.path.exists(cookies_file):
        opts["cookies"] = cookies_file

    ff = _ffmpeg_location()
    if ff:
        opts["ffmpeg_location"] = ff
    return opts


# ============================================================
# Extração de metadados
# ============================================================

def extract_info(url, timeout=60):
    """Extrai os metadados do vídeo do YouTube sem baixar o arquivo."""
    with yt_dlp.YoutubeDL({**_base_opts(), "skip_download": True}) as ydl:
        return ydl.extract_info(url, download=False)


def _sanitize(name):
    name = re.sub(r'[\\/:*?"<>|]', "_", name or "")
    name = re.sub(r"\s+", " ", name).strip()
    return name[:150] or "youtube_video"


def _format_duration(seconds):
    if not seconds:
        return "--:--"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _parse_quality(quality):
    try:
        q = int(str(quality or DEFAULT_QUALITY))
    except (TypeError, ValueError):
        q = DEFAULT_QUALITY
    return max(144, min(q, 4320))


# ============================================================
# URLs de download (codificadas em base64)
# ============================================================

def encode_url(url):
    return base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii")


def decode_url(token):
    return base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")


# ============================================================
# Resposta no formato Cobalt (o frontend continua o mesmo)
# ============================================================

def build_youtube_result(url, quality="1080"):
    """Monta resposta equivalente ao status 'tunnel' da Cobalt usando yt-dlp."""
    info = extract_info(url)

    # Se for uma playlist sem ID próprio, usa o primeiro item
    if not info.get("id") and info.get("entries"):
        info = info["entries"][0]
    if not info or not info.get("id"):
        raise RuntimeError("Vídeo não encontrado ou indisponível")

    title = info.get("title") or "youtube_video"
    safe_title = _sanitize(title)
    q = _parse_quality(quality)

    return {
        "status": "tunnel",
        "url": f"/api/yt-dlp/download?q={encode_url(url)}&m=video&qty={q}",
        "filename": f"{safe_title}.{VIDEO_EXT}",
        "audio": f"/api/yt-dlp/download?q={encode_url(url)}&m=audio",
        "audioFilename": f"{safe_title}.{AUDIO_EXT}",
        "thumb": info.get("thumbnail") or "",
        "title": title,
        "duration": _format_duration(info.get("duration")),
        "preview": "image",
        "via": "yt-dlp",
    }


# ============================================================
# Download para arquivo temporário
# ============================================================

def download_to_temp(url, mode="video", quality=DEFAULT_QUALITY):
    """Baixa o vídeo (ou extrai o áudio MP3) para um diretório temporário.

    Retorna a tupla (caminho_do_arquivo, nome_desejado, dir_temporario).
    Em caso de erro, remove o diretório temporário e relança a exceção.
    """
    tmpdir = tempfile.mkdtemp(prefix="saveclip_yt_")
    try:
        if mode == "audio":
            out, filename = _download_audio(url, tmpdir)
        else:
            out, filename = _download_video(url, tmpdir, _parse_quality(quality))
        return out, filename, tmpdir
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise


def _download_video(url, tmpdir, quality):
    ff = _find_ffmpeg()
    opts = {
        **_base_opts(),
        "outtmpl": os.path.join(tmpdir, "video.%(ext)s"),
    }
    if ff:
        # Com ffmpeg: baixa vídeo + áudio separados e mescla em MP4 (melhor qualidade)
        opts["format"] = (
            f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]"
            f"/bestvideo[height<={quality}]+bestaudio"
            f"/best[ext=mp4]/best"
        )
        opts["merge_output_format"] = VIDEO_EXT
    else:
        # Sem ffmpeg: apenas formatos progressivos (qualidade mais baixa)
        opts["format"] = "best[ext=mp4]/best"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

    title = _sanitize((info or {}).get("title") or "youtube_video")

    candidates = [
        f for f in glob.glob(os.path.join(tmpdir, "video.*"))
        if not f.endswith(".part")
    ]
    if not candidates:
        raise RuntimeError("Falha ao baixar o vídeo")

    out = max(candidates, key=os.path.getsize)
    ext = os.path.splitext(out)[1].lstrip(".") or VIDEO_EXT
    return out, f"{title}.{ext}"


def _download_audio(url, tmpdir):
    if not _find_ffmpeg():
        raise RuntimeError(
            "ffmpeg não encontrado no sistema — necessário para extrair MP3. "
            "Instale o ffmpeg ou defina a variável FFMPEG_PATH."
        )

    opts = {
        **_base_opts(),
        "format": "bestaudio/best",
        "outtmpl": os.path.join(tmpdir, "audio.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": AUDIO_EXT,
            "preferredquality": "320",
        }],
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

    title = _sanitize((info or {}).get("title") or "youtube_video")

    out = os.path.join(tmpdir, f"audio.{AUDIO_EXT}")
    if not os.path.exists(out):
        raise RuntimeError("Falha ao gerar o arquivo de áudio MP3")
    return out, f"{title}.{AUDIO_EXT}"


# ============================================================
# Conversão de erros do yt-dlp em códigos amigáveis
# ============================================================

def map_ytdlp_error(exc):
    """Converte exceções do yt-dlp em códigos de erro no padrão Cobalt."""
    msg = (str(exc) or "").lower()

    if "ffmpeg" in msg or "ffprobe" in msg:
        return "error.api.ffmpeg.missing"
    if "private" in msg:
        return "error.api.youtube.private"
    if "sign in" in msg or "login" in msg or "confirm" in msg or "bot" in msg:
        return "error.api.youtube.login"
    if "country" in msg or "region" in msg or "georestricted" in msg:
        return "error.api.youtube.region"
    if "member" in msg or "membership" in msg:
        return "error.api.youtube.membership"
    if "age" in msg or "mature" in msg:
        return "error.api.youtube.login"
    if "unavailable" in msg or "not found" in msg or "removed" in msg:
        return "error.api.content.video.unavailable"
    if "unsupported url" in msg:
        return "error.api.link.unsupported"
    return "error.api.fetch.fail"


def schedule_cleanup(tmpdir, delay=60):
    """Remove o diretório temporário em segundo plano (garantia de limpeza,
    mesmo se o call_on_close do Flask não for disparado)."""
    def _clean():
        time.sleep(delay)
        shutil.rmtree(tmpdir, ignore_errors=True)

    threading.Thread(target=_clean, daemon=True).start()


