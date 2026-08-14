# 🚀 Guia Completo: Como Configurar e Rodar o SaveClip

O **SaveClip** é uma aplicação completa para baixar vídeos e extrair áudio em MP3 do **Instagram, Facebook, YouTube e TikTok**.

A aplicação é dividida em duas partes para garantir total segurança:
1. **Instância da API Cobalt** (hospedada no **Railway**, responsável por processar as mídias do Instagram, Facebook e TikTok — e como *fallback* do YouTube).
2. **Servidor SaveClip** (`server.py` + `Dockerfile`), rodando na **VM da Oracle Cloud** (Docker), que serve o site e **esconde o endereço da sua API e chaves privadas** de todos os visitantes.

> ▶️ **YouTube é baixado via `yt-dlp`** (não usa mais a Cobalt por padrão): o servidor extrai os metadados e baixa o vídeo (MP4) ou áudio (MP3) diretamente, com qualidade até 1080p (padrão) ou superior, usando o **ffmpeg** para mesclar vídeo+áudio e converter para MP3. Se o YouTube bloquear o IP da VM (datacenter), o sistema **cai automaticamente na API Cobalt** como fallback. Veja a seção 4 e o guia [DEPLOY VPS ORACLE.md](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/DEPLOY%20VPS%20ORACLE.md).

> ✅ **Status atual (14/08/2026):** o SaveClip está **no ar e funcional** em **http://147.15.122.54** (VM da Oracle Cloud, Docker), com YouTube (MP4 1080p + MP3 320kbps via yt-dlp + fallback Cobalt), Instagram, Facebook e TikTok funcionando. O **Railway ficou apenas com a API Cobalt** (`api-production-664d8.up.railway.app`). Para o deploy na VM e como atualizar o site, veja o guia [DEPLOY VPS ORACLE.md](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/DEPLOY%20VPS%20ORACLE.md).

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
   PORT=8080
   ```

3. **Instale o ffmpeg** (obrigatório para o YouTube em MP4/MP3 funcionar localmente):
   - **Windows:** `winget install Gyan.FFmpeg`
   - **macOS:** `brew install ffmpeg`
   - **Ubuntu/Debian:** `sudo apt install ffmpeg`

4. **Inicie o servidor:**
   ```bash
   python server.py
   ```

5. **Acesse no navegador:**
   Abra **http://localhost:8080** 🎉
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

Se no futuro você alterar sua instância do Railway ou precisar atualizar o link/chave da API, você pode alterar em alguns locais simples:

- **Localmente:** Altere a linha `COBALT_API_URL` no arquivo [.env](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/.env).
- **Na VM da Oracle (produção):** edite o arquivo `~/Site-Downloader/.env` na VM e reinicie o app com `cd ~/Site-Downloader && docker compose restart`.
- **Na Vercel:** Atualize o valor em **Settings → Environment Variables** no painel da Vercel.
- **No Railway:** Atualize o valor em **Settings → Variables** do serviço no painel do Railway, ou pelo CLI:
  ```bash
  railway variables set COBALT_API_URL=https://nova-url-da-api.up.railway.app
  ```
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

> 🔧 **Bloqueio do YouTube ("Sign in to confirm you're not a bot"):** em IPs de datacenter (VPS/Railway) o YouTube bloqueia seletivamente alguns vídeos (principalmente música). O projeto lida com isso em **3 camadas automáticas**: (1) **player clients alternativos** (`tv`, `android`, `ios`, `web_safari`) no `_base_opts()` de [api/ytdlp.py](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/api/ytdlp.py); (2) **retry automático com rotação de clients** (`_run_with_retry`, até 4 tentativas); (3) **fallback automático para a API Cobalt** no [server.py](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/server.py) (`_cobalt_request`) quando o erro `error.api.youtube.login` persiste. Para melhorar ainda mais a taxa de sucesso do yt-dlp, coloque um `cookies.txt` (exportado do navegador logado no YouTube) na VM — ele é montado no container via `YTDLP_COOKIES` (veja [DEPLOY VPS ORACLE.md](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/DEPLOY%20VPS%20ORACLE.md), seção 11).

> ⚠️ **Limitações na Vercel:** as funções Serverless têm limite de tempo (10s no plano Hobby) e de tamanho de resposta (~4,5 MB), além de não garantirem o ffmpeg. Para downloads de YouTube em produção, prefira rodar o `server.py` em uma VPS/Railway (com ffmpeg instalado) em vez do deploy Vercel, ou mantenha a Vercel apenas para as demais plataformas via Cobalt.

---

## 🚂 5. Opção: Hospedando a Própria Instância Cobalt no Railway

Caso queira hospedar sua própria instância da API Cobalt:

1. Acesse [railway.com](https://railway.com) e crie uma conta.
2. Acesse `railway.com/new`, busque pelo template **"Cobalt"** e clique em **Deploy**.
3. No painel do Railway, vá em **Settings → Networking → Generate Domain**.
4. Copie o domínio gerado (ex: `https://cobalt-api-xxxxx.up.railway.app`) e defina em `COBALT_API_URL`.

---

## 🚂 6. (Histórico) Deploy do Servidor Completo no Railway

> ⚠️ **Este método foi substituído:** o SaveClip agora roda na **VM da Oracle Cloud** em Docker (veja [DEPLOY VPS ORACLE.md](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/DEPLOY%20VPS%20ORACLE.md)). O Railway ficou **apenas com a API Cobalt**. Esta seção permanece como referência do processo via Railway CLI.

> ✅ **Como está hoje (14/08/2026):** o SaveClip está publicado em **http://147.15.122.54** (VM da Oracle Cloud) e o Railway ficou só com a API Cobalt. O projeto **"Cobalt Tools - Complete Setup"** foi removido do Railway.

### Opção A — Deploy via Railway CLI (sem GitHub)

1. **Instale o Railway CLI** (requer Node.js):
   ```bash
   npm install -g @railway/cli
   ```

2. **Faça login** (abre o navegador para autorizar):
   ```bash
   railway login
   ```

3. **Vincule a pasta do projeto ao serviço desejado:**
   ```bash
   railway link
   ```
   Selecione workspace, projeto, ambiente (`production`) e serviço. Para usar um projeto/serviço específico sem menus:
   ```bash
   railway link -p <PROJECT_ID> -s "<SERVICE_NAME>" -e production
   ```

4. **Configure a variável de ambiente:**
   ```bash
   railway variables set COBALT_API_URL=https://api-production-664d8.up.railway.app
   ```
   > 🔑 A `COBALT_API_URL` deve apontar para a **API Cobalt** que processa Instagram, Facebook e TikTok (veja a seção 5).

5. **Envie o código e faça o deploy:**
   ```bash
   railway up
   ```
   O Railway detecta o [Dockerfile](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/Dockerfile) (imagem `python:3.12-slim` + `ffmpeg` instalado) e o [railway.json](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/railway.json). Para rodar em segundo plano:
   ```bash
   railway up --detach
   ```

6. **Gere o domínio público** (se ainda não tiver):
   ```bash
   railway domain
   ```

7. Pronto! O site fica disponível no domínio gerado com **todas** as plataformas funcionando: Instagram, Facebook, TikTok (via Cobalt) e YouTube em alta qualidade + MP3 320kbps (via yt-dlp + ffmpeg).

#### 🔄 Atualizar o site depois de mexer no código

Como o deploy vem da sua máquina, basta repetir:
```bash
railway up
```
Acompanhe com `railway logs`, `railway status` e `railway deployment list`.

### Opção B — Deploy via GitHub (deploy automático)

1. **Suba o projeto para o GitHub** (o `.env` não vai por causa do `.gitignore`).
2. Crie o projeto no Railway (`railway.com` → **New Project** → **Deploy from GitHub repo**) e selecione o repositório.
3. Configure as variáveis de ambiente (Settings → Variables):
   ```env
   COBALT_API_URL=https://api-production-664d8.up.railway.app
   PORT=8080
   ```
4. Gere o domínio público (Settings → Networking → **Generate Domain**).
5. Pronto! O GitHub fica conectado e cada `git push` faz deploy automático.

> 💡 O mesmo `Dockerfile` também funciona no **Render** (Web Service → Docker) ou em qualquer **VPS** com Docker.

> ⚠️ **Limite do plano grátis do Railway:** o plano gratuito limita a quantidade de recursos provisionados. Se a sua conta já tem outros serviços (ex: instância Cobalt), pode não ser possível criar um **projeto novo**. Soluções: usar um **serviço já existente** (como foi feito aqui, com `railway link` + `railway up`) ou excluir recursos desnecessários (ex: a interface web da Cobalt — desnecessária se você já tem o seu próprio front-end).

---

## 📖 Links Úteis

- 🐧 [DEPLOY VPS ORACLE.md](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/DEPLOY%20VPS%20ORACLE.md) — passo a passo completo de deploy na VM da Oracle Cloud
- 📦 [Repositório Oficial do Cobalt](https://github.com/imputnet/cobalt)
- 🎞️ [yt-dlp](https://github.com/yt-dlp/yt-dlp) — downloader de vídeo usado para o YouTube
- 🚂 [Templates do Railway](https://railway.com/templates)
- 🛠️ [Railway CLI (GitHub)](https://github.com/railwayapp/cli) — usado para o deploy local via `railway up`
- 📖 [Documentação da API Cobalt](https://github.com/imputnet/cobalt/blob/main/docs/api.md)

