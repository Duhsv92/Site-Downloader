# ============================================================
# SaveClip — Imagem completa (frontend + API + YouTube via yt-dlp)
# Deploy recomendado: Railway / Render / VPS (qualquer serviço Docker)
# ============================================================
FROM python:3.12-slim

# ffmpeg é obrigatório para mesclar vídeo+áudio (MP4 em alta qualidade)
# e para extrair o áudio em MP3 320kbps
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala as dependências primeiro (aproveita o cache de build)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do projeto
COPY . .

# Porta padrão (pode ser sobrescrita pela plataforma via variável PORT)
ENV PORT=8080
EXPOSE 8080

CMD ["python", "server.py"]
