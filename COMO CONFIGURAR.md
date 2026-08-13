# 🚀 Guia Completo: Como Configurar e Rodar o SaveClip

O **SaveClip** é uma aplicação completa para baixar vídeos e extrair áudio em MP3 do **Instagram, Facebook, YouTube e TikTok**.

A aplicação é dividida em duas partes para garantir total segurança:
1. **Instância da API Cobalt** (hospedada no Railway, Render ou VPS, responsável por processar as mídias do Instagram, Facebook e TikTok).
2. **Servidor / Serverless SaveClip** (`server.py` ou `api/download.py`), que intercepta as chamadas do front-end e **esconde o endereço da sua API e chaves privadas** de todos os visitantes do site.

> ▶️ **YouTube é baixado via `yt-dlp`** (não usa mais a Cobalt): o servidor extrai os metadados e baixa o vídeo (MP4) ou áudio (MP3) diretamente, com qualidade até 1080p (padrão) ou superior, usando o **ffmpeg** para mesclar vídeo+áudio e converter para MP3. Veja a seção 4.

---

## 💻 1. Rodando o SaveClip Localmente

1. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure o arquivo `.env`:**
   Copie o exemplo do `.env.example` para `.env`:
   ```bash
   copy .env.example .env   # no Linux/Mac: cp .env.example .env
   ```

   Edite o arquivo `.env` e defina a URL da sua API:
   ```env
   COBALT_API_URL=https://api-production-664d8.up.railway.app
   PORT=5000
   ```

3. **Inicie o servidor:**
   ```bash
   python server.py
   ```

4. **Acesse no navegador:**
   Abra **http://localhost:5000** 🎉
   - A URL da API Cobalt fica salva somente no `.env` do backend, garantindo que os visitantes nunca tenham acesso ao seu endereço privado do Railway.

---

## 🌐 2. Deploy no GitHub + Vercel (para Instagram, Facebook e TikTok)

O projeto está totalmente pré-configurado com [vercel.json](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/vercel.json) e funções Serverless Python em [api/download.py](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/api/download.py).

> ⚠️ **Atenção (YouTube):** na Vercel, os downloads de **vídeo do YouTube** funcionam apenas em qualidade reduzida (sem o ffmpeg no runtime serverless, o yt-dlp baixa somente formatos progressivos) e o **áudio MP3 não funciona** (o ffmpeg é obrigatório para extrair MP3). Para ter o YouTube 100% funcional em produção, use o **deploy do servidor completo** (seção 6) em vez da Vercel, ou use a Vercel apenas para as demais plataformas via Cobalt.

### Passo a passo para publicação:

1. **Suba seu projeto para o GitHub:**
   - O arquivo `.env` já está protegido pelo `.gitignore` e não será enviado para o repositório.
   ```bash
   git add .
   git commit -m "Deploy SaveClip"
   git push origin main
   ```

2. **Conecte na Vercel:**
   - Acesse o painel da [Vercel](https://vercel.com/) e faça login.
   - Clique em **Add New...** → **Project**.
   - Importe o repositório do GitHub (ex: `Site-Downloader`).

3. **Configure as Variáveis de Ambiente na Vercel:**
   - Na tela de Deploy (ou em **Settings → Environment Variables**), adicione:
     - **Key (Nome):** `COBALT_API_URL`
     - **Value (Valor):** `https://api-production-664d8.up.railway.app`
   - Clique em **Add**.

4. **Clique em Deploy:**
   - A Vercel usará o `vercel.json` para servir o front-end e executar o backend como **Function Serverless** de forma 100% gratuita.

---

## 🔑 3. Como Trocar o Link da API ou a API Key

Se no futuro você alterar sua instância do Railway ou precisar atualizar o link/chave da API, você pode alterar em 3 locais simples:

- **Localmente:** Altere a linha `COBALT_API_URL` no arquivo [.env](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/.env).
- **Na Vercel:** Atualize o valor em **Settings → Environment Variables** no painel da Vercel.
- **No Código Python:** Altere a variável `DEFAULT_COBALT_URL` nos arquivos [server.py](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/server.py) e [api/download.py](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/api/download.py).

---

## 🛠️ 4. Recursos e Funcionalidades

- 🔍 **Busca de Vídeos sem Download Forçado:** O botão **Buscar Vídeo** consulta a mídia e exibe a miniatura/prévia antes de iniciar qualquer salvamento.
- 🎬 **Prévia em Player de Vídeo:** Exibe a capa/thumbnail e leitor de vídeo direto na caixa de resultado.
- 📥 **Download Direto para o Dispositivo:** Sistema por `Blob` que força o salvamento do arquivo diretamente na pasta **Downloads** do PC ou celular.
- 🎵 **Extração de Áudio MP3 (320 kbps):** Opção para extrair e baixar apenas o áudio do vídeo na qualidade máxima (HQ 320kbps).
- ▶️ **YouTube via yt-dlp:** O SaveClip baixa vídeos do **YouTube** (incluindo Shorts e links `youtu.be`) com **yt-dlp**, substituindo a API Cobalt para essa plataforma. Qualidade padrão **1080p** (ajustável via `videoQuality`) e áudio **MP3 320kbps**. As demais plataformas (Instagram, Facebook, TikTok) continuam usando a Cobalt.

> ⚠️ **Requisito: ffmpeg** — o yt-dlp usa o ffmpeg para mesclar vídeo+áudio em MP4 e converter o áudio para MP3. Instale em qualquer plataforma:
> - **Windows:** `winget install Gyan.FFmpeg` (ou `choco install ffmpeg`)
> - **macOS:** `brew install ffmpeg`
> - **Ubuntu/Debian:** `sudo apt install ffmpeg`
>
> Se o ffmpeg não estiver na pasta PATH, defina a variável `FFMPEG_PATH` apontando para o executável. Sem ffmpeg, o vídeo é baixado em qualidade reduzida (apenas formatos progressivos) e o MP3 fica indisponível (erro `error.api.ffmpeg.missing`).

> ⚠️ **Limitações na Vercel:** as funções Serverless têm limite de tempo (10s no plano Hobby) e de tamanho de resposta (~4,5 MB), além de não garantirem o ffmpeg. Para downloads de YouTube em produção, prefira rodar o `server.py` em uma VPS/Railway (com ffmpeg instalado) em vez do deploy Vercel, ou mantenha a Vercel apenas para as demais plataformas via Cobalt.

---

## 🚂 5. Opção: Hospedando a Própria Instância Cobalt no Railway

Caso queira hospedar sua própria instância da API Cobalt:

1. Acesse [railway.com](https://railway.com) e crie uma conta.
2. Acesse `railway.com/new`, busque pelo template **"Cobalt"** e clique em **Deploy**.
3. No painel do Railway, vá em **Settings → Networking → Generate Domain**.
4. Copie o domínio gerado (ex: `https://cobalt-api-xxxxx.up.railway.app`) e defina em `COBALT_API_URL`.

---

## 🚂 6. Deploy do Servidor Completo no Railway (Recomendado — tudo funciona)

Este é o deploy **recomendado para o YouTube funcionar 100%** em produção: o servidor `server.py` serve o site E a API, com **ffmpeg** incluído na imagem Docker (mesmo comportamento do ambiente local).

1. **Suba o projeto para o GitHub** (o `.env` não vai por causa do `.gitignore`).

2. **Crie um novo projeto no Railway** (`railway.com` → **New Project** → **Deploy from GitHub repo**).

3. O Railway detecta o [railway.json](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/railway.json) e o [Dockerfile](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/Dockerfile) automaticamente (imagem `python:3.12-slim` + `ffmpeg` instalado).

4. **Configure as variáveis de ambiente** (Settings → Variables):
   ```env
   COBALT_API_URL=https://api-production-664d8.up.railway.app
   PORT=8080
   ```

5. **Gere o domínio público**: Settings → Networking → **Generate Domain**.

6. Pronto! O site fica disponível em `https://seu-app.up.railway.app` com **todas** as plataformas funcionando: Instagram, Facebook, TikTok (via Cobalt) e YouTube em alta qualidade + MP3 320kbps (via yt-dlp + ffmpeg).

> 💡 O mesmo `Dockerfile` também funciona no **Render** (Web Service → Docker) ou em qualquer **VPS** com Docker.

---

## 📖 Links Úteis

- 📦 [Repositório Oficial do Cobalt](https://github.com/imputnet/cobalt)
- 🎞️ [yt-dlp](https://github.com/yt-dlp/yt-dlp) — downloader de vídeo usado para o YouTube
- 🚂 [Templates do Railway](https://railway.com/templates)
- 📖 [Documentação da API Cobalt](https://github.com/imputnet/cobalt/blob/main/docs/api.md)

