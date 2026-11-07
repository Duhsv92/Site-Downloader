# 🚀 Guia Completo: Como Configurar e Rodar o SaveClip

O **SaveClip** é uma aplicação completa para baixar vídeos e extrair áudio em MP3 do **Instagram, Facebook, YouTube e TikTok**.

A aplicação é dividida em duas partes para garantir total segurança:
1. **Instância da API Cobalt** — roda na **própria VM da Oracle Cloud** (container Docker, imagem oficial `ghcr.io/imputnet/cobalt:11`), responsável por processar as mídias do Instagram, Facebook e TikTok — e como *fallback* do YouTube. Montagem completa na seção 5 e no guia [DEPLOY VPS ORACLE.md](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/DEPLOY%20VPS%20ORACLE.md), seção 11.
2. **Servidor SaveClip** (`server.py` + `Dockerfile`), também na **VM da Oracle Cloud** (Docker), que serve o site e **esconde o endereço da sua API e chaves privadas** de todos os visitantes.

> ▶️ **YouTube agora é baixado pela API Cobalt** (fluxo principal, junto com Instagram/Facebook/TikTok): o servidor repassa o link para a instância Cobalt, que devolve o MP4 (até 1080p) ou o MP3 320kbps. Se a Cobalt falhar no YouTube (ex: bloqueio "Sign in to confirm you're not a bot" em IP de datacenter), o sistema **cai automaticamente no `yt-dlp`** como fallback. Veja a seção 4 e o guia [DEPLOY VPS ORACLE.md](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/DEPLOY%20VPS%20ORACLE.md).

> ✅ **Status atual:** o SaveClip está **no ar em HTTPS** — **https://saverclip.mobaily.com.br** (o `http://` redireciona sozinho para `https://`), com o **Caddy** emitindo/renovando o certificado do Let's Encrypt. A **API Cobalt** em uso é a instância do **Railway** — **https://api-production-65e6.up.railway.app** — que processa Instagram, Facebook, TikTok **e YouTube** (com o `yt-dlp` como fallback automático no YouTube). O site continua rodando na VM da Oracle; os downloads saem como links de `/tunnel` no domínio da Cobalt do Railway. Como subir/atualizar: [DEPLOY VPS ORACLE.md](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/DEPLOY%20VPS%20ORACLE.md), seções 10 e 13.

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

   Edite o arquivo `.env` e defina a URL da sua API (a instância Cobalt do Railway):
   ```env
   COBALT_API_URL=https://api-production-65e6.up.railway.app
   PORT=8080
   ```
   > 🔑 Esta instância **não exige API key** — deixe `COBALT_API_KEY` e `COBALT_AUTH_SCHEME` comentados. (Se um dia a instância passar a exigir chave, preencha `COBALT_API_KEY=<uuid>` + `COBALT_AUTH_SCHEME=Api-Key`.)

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
     - **Value (Valor):** `https://saverclip.mobaily.com.br/cobalt` (instância self-hosted na sua VM, com o HTTPS ativo — a Cobalt fica no sub-caminho `/cobalt/` do site)
     - **Key (Nome):** `COBALT_API_KEY` → **Value:** o UUID do `keys.json` da VM
     - **Key (Nome):** `COBALT_AUTH_SCHEME` → **Value:** `Api-Key`
   - Clique em **Add**.
   > ⚠️ **Atenção (mixed content):** a Vercel serve o site em **HTTPS**, e o navegador **bloqueia** downloads de links em HTTP. Nesse cenário a Cobalt precisa estar em HTTPS (veja a seção 13 do [DEPLOY VPS ORACLE.md](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/DEPLOY%20VPS%20ORACLE.md), com Caddy).

4. **Clique em Deploy:**
   - A Vercel usará o `vercel.json` para servir o front-end e executar o backend como **Function Serverless** de forma 100% gratuita.

---

## 🔑 3. Como Trocar o Link da API ou a API Key

Se no futuro você trocar a instância Cobalt (self-hosted ou externa) ou precisar atualizar o link/chave da API, os pontos que leem a mesma variável `COBALT_API_URL` são:

- **Localmente:** Altere `COBALT_API_URL`, `COBALT_API_KEY` e `COBALT_AUTH_SCHEME` no arquivo [.env](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/.env).
- **Na VM da Oracle (produção, Cobalt self-hosted):** o site aponta para o endereço **interno** da rede Docker — `COBALT_API_URL=http://cobalt:9000` + `COBALT_API_KEY=<uuid>`. Edite `~/Site-Downloader/.env` e rode `cd ~/Site-Downloader && docker compose restart saveclip`. A **URL pública** da Cobalt (usada nos links de `/tunnel`) fica na variável `API_URL` do serviço `cobalt`: no `docker-compose.yml` (modo HTTP, `http://saverclip.mobaily.com.br:8080/`) e no `docker-compose.https.yml` (modo HTTPS, hoje o ativo: `https://saverclip.mobaily.com.br/` — a Cobalt usa só a **origem** dessa URL, então os links saem como `https://saverclip.mobaily.com.br/tunnel?id=...`, roteados pelo Caddy); se você mudá-la, rode `docker compose up -d cobalt`.
- **Numa instância externa (Railway/Vercel):** Atualize o valor em **Settings → Environment Variables** no painel da hospedagem e também no `.env` da VM:
  ```bash
  # exemplo: atualizar via Railway CLI
  railway variables set COBALT_API_URL=https://sua-instancia.up.railway.app
  ```
- **No Código Python:** o valor padrão é a variável `DEFAULT_COBALT_URL`, nos arquivos [server.py](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/server.py) e [api/download.py](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/api/download.py) — usada apenas quando não existe `.env`/variável de ambiente (ex: Vercel sem `COBALT_API_URL` configurada).
- **Com HTTPS ativo (o padrão hoje):** a **API** da Cobalt fica em **`https://saverclip.mobaily.com.br/cobalt/`** (sub-caminho do próprio domínio do site, sem registro DNS novo) — é esse o valor a usar no `COBALT_API_URL` do seu PC/Vercel. Os **downloads** (`/tunnel`) saem na **raiz** do domínio, `https://saverclip.mobaily.com.br/tunnel?id=...`, porque a Cobalt usa apenas a **origem** do `API_URL` do container (veja a seção 13 do [DEPLOY VPS ORACLE.md](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/DEPLOY%20VPS%20ORACLE.md)). Se você voltar ao modo HTTP puro (seção 13.4), a URL pública da Cobalt volta a ser `http://saverclip.mobaily.com.br:8080`. Dentro da VM o site continua usando `http://cobalt:9000` (rede interna do Docker).



---

## 🛠️ 4. Recursos e Funcionalidades

- 🔍 **Busca de Vídeos sem Download Forçado:** O botão **Buscar Vídeo** consulta a mídia e exibe a miniatura/prévia antes de iniciar qualquer salvamento.
- 🎬 **Prévia em Player de Vídeo:** Exibe a capa/thumbnail e leitor de vídeo direto na caixa de resultado.
- 📥 **Download Direto para o Dispositivo:** Sistema por `Blob` que força o salvamento do arquivo diretamente na pasta **Downloads** do PC ou celular.
- 🎵 **Extração de Áudio MP3 (320 kbps):** Opção para extrair e baixar apenas o áudio do vídeo na qualidade máxima (HQ 320kbps).
- ▶️ **YouTube via Cobalt (com fallback yt-dlp):** O SaveClip baixa vídeos do **YouTube** (incluindo Shorts e links `youtu.be`) pela **API Cobalt** (fluxo principal, junto com Instagram, Facebook e TikTok). Qualidade padrão **1080p** (ajustável via `videoQuality`) e áudio **MP3 320kbps**. Se a Cobalt falhar no YouTube (bloqueio de IP de datacenter), o `yt-dlp` entra como **fallback automático**.

> ⚠️ **Requisito: ffmpeg** — o yt-dlp usa o ffmpeg para mesclar vídeo+áudio em MP4 e converter o áudio para MP3. Instale em qualquer plataforma:
> - **Windows:** `winget install Gyan.FFmpeg` (ou `choco install ffmpeg`)
> - **macOS:** `brew install ffmpeg`
> - **Ubuntu/Debian:** `sudo apt install ffmpeg`
>
> Se o ffmpeg não estiver na pasta PATH, defina a variável `FFMPEG_PATH` apontando para o executável. Sem ffmpeg, o vídeo é baixado em qualidade reduzida (apenas formatos progressivos) e o MP3 fica indisponível (erro `error.api.ffmpeg.missing`).

> 🔧 **Bloqueio do YouTube ("Sign in to confirm you're not a bot"):** em IPs de datacenter (VPS/Railway) o YouTube bloqueia seletivamente alguns vídeos (principalmente música e Shorts). O projeto agora tenta a **API Cobalt primeiro** e, se ela falhar no YouTube (ex: `error.api.youtube.login`), cai automaticamente no **yt-dlp** — que por sua vez usa player clients alternativos (`_base_opts()` em [api/ytdlp.py](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/api/ytdlp.py)) e retry com rotação de clients. Para melhorar a taxa de sucesso, coloque cookies dos dois lados: um `cookies.json` na instância Cobalt (formato `{"youtube": ["cookie=...; b=..."]}` via `COOKIE_PATH`) e um `cookies.txt` na VM (montado via `YTDLP_COOKIES` — veja [DEPLOY VPS ORACLE.md](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/DEPLOY%20VPS%20ORACLE.md), seções 11 e 12).

> ⚠️ **Limitações na Vercel:** as funções Serverless têm limite de tempo (10s no plano Hobby) e de tamanho de resposta (~4,5 MB). Para downloads de YouTube em produção, prefira rodar o `server.py` em uma VPS/Railway em vez do deploy Vercel, ou mantenha a Vercel apenas para as demais plataformas via Cobalt.

---

## 🚂 5. Opção: Hospedando a Própria Instância Cobalt

### ✅ Opção A (recomendada) — Na sua própria VM Oracle

Atualmente a produção usa a **instância Cobalt do Railway** (`https://api-production-65e6.up.railway.app`). Se preferir custo zero e independência total, a alternativa é rodar a Cobalt **dentro da própria VM**, junto com o site: os dois containers já estão no `docker-compose.yml` e conversam pela rede interna do Docker (o site continua sendo a única porta pública do site; a Cobalt usa a porta 8080 só para os links de `/tunnel`). Lembrete: o Railway já derrubou uma instância no passado quando a conta de teste expirou.

Passo a passo completo (chave de API + testes): [DEPLOY VPS ORACLE.md](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/DEPLOY%20VPS%20ORACLE.md), **seção 11**. Resumo:

```bash
cd ~/Site-Downloader
git pull

# Gera a chave de API e cria o keys.json
KEY=$(python3 -c "import uuid; print(uuid.uuid4())")
printf '{\n  "%s": {\n    "name": "saveclip",\n    "limit": 120,\n    "allowedServices": "all"\n  }\n}\n' "$KEY" > keys.json

# Aponta o site para a Cobalt interna e usa a MESMA chave
sed -i "s|^COBALT_API_URL=.*|COBALT_API_URL=http://cobalt:9000|" .env
grep -q '^COBALT_API_KEY=' .env && sed -i "s|^COBALT_API_KEY=.*|COBALT_API_KEY=$KEY|" .env || echo "COBALT_API_KEY=$KEY" >> .env
grep -q '^COBALT_AUTH_SCHEME=' .env || echo "COBALT_AUTH_SCHEME=Api-Key" >> .env

docker compose up -d --build  # sobe (ou baixa) a imagem oficial ghcr.io/imputnet/cobalt:11
docker compose ps             # deve listar saveclip E cobalt como Up
curl -s http://127.0.0.1:8080/   # informações da instância Cobalt
```

Para atualizar a Cobalt depois: `docker compose pull cobalt && docker compose up -d cobalt`.

### 🚂 Opção B — Numa hospedagem externa (Railway)

Caso queira hospedar sua própria instância da API Cobalt:

1. Acesse [railway.com](https://railway.com) e crie uma conta.
2. Acesse `railway.com/new`, busque pelo template **"Cobalt"** e clique em **Deploy**.
3. No painel do Railway, vá em **Settings → Networking → Generate Domain**.
4. Copie o domínio gerado (ex: `https://sua-instancia.up.railway.app`) e defina em `COBALT_API_URL`.

### 🔁 Recriando a instância Cobalt do zero (se ela cair)

Sintoma de instância removida: o domínio responde **`{"status":"error","code":404,"message":"Application not found"}`** com o header `x-railway-fallback: true` (quem respondeu foi o edge do Railway, não a Cobalt). Nesse caso:

1. [railway.com](https://railway.com) → **New Project** → **Deploy a Docker Image** → cole `ghcr.io/imputnet/cobalt:11` → **Deploy**.
2. **Settings → Networking → Public Networking → Generate Domain** e confirme que a **porta pública é `9000`** (a imagem oficial da Cobalt expõe `9000`, é onde o container escuta).
3. Em **Variables**, defina:
   ```env
   API_URL=https://sua-instancia.up.railway.app/
   API_PORT=9000
   ```
   > 🔑 A `API_URL` precisa ser o **domínio público, com a barra `/` no final**. É ela que a Cobalt usa para montar os links de `/tunnel` — ou seja, os links de download que o site repassa ao visitante. Se ficar errada, o download quebra mesmo com a API "no ar".
4. Faça **Redeploy** e valide (o `GET /` devolve um JSON com `"cobalt":{"version":"11.x","services":[...]}`):
   ```bash
   curl -s https://sua-instancia.up.railway.app/
   ```
5. Atualize `COBALT_API_URL` no `.env` local, na Vercel e na VM (seção 3).

| Sintoma | Significado |
|:--|:--|
| `404 Application not found` | O domínio não aponta para nenhum serviço (instância removida/renomeada) |
| `502 Application failed to respond` | O serviço existe, mas o container não responde — confira a **porta pública (9000)** e os **Deploy/Run logs** do Railway |
| `api.auth.api-key.missing` | A instância exige API key — configure `COBALT_API_KEY` (+ `COBALT_AUTH_SCHEME=Api-Key`) |

### 🔐 API Key: qual esquema de autenticação o SaveClip usa

A Cobalt aceita dois esquemas no header `Authorization`:

| Esquema | Para que serve | Como configurar no SaveClip |
|:--|:--|:--|
| `Api-Key <uuid>` | Chave de API do arquivo `keys.json` da instância | `COBALT_AUTH_SCHEME=Api-Key` (**padrão**) |
| `Bearer <jwt>` | Token JWT temporário emitido pelo `/session` (Cloudflare Turnstile) | `COBALT_AUTH_SCHEME=Bearer` |

> ⚠️ Antes, o código enviava sempre `Bearer`, que **não** funciona com uma API key (a Cobalt responderia `api.auth.api-key.missing`). Agora o esquema é configurável e o padrão é `Api-Key`.

Para exigir autenticação na instância Cobalt: `API_KEY_URL=file:///keys.json` + `API_AUTH_REQUIRED=1`. O `keys.json` precisa existir **dentro do container** — no Railway, isso exige um **Volume** montado. Sem API key, a instância continua protegida pelo rate limit por IP (`RATELIMIT_WINDOW` / `RATELIMIT_MAX`).

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
   railway variables set COBALT_API_URL=https://sua-instancia.up.railway.app
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

7. Pronto! O site fica disponível no domínio gerado com **todas** as plataformas funcionando: Instagram, Facebook, TikTok e YouTube (via Cobalt, com yt-dlp como fallback).

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
   COBALT_API_URL=https://sua-instancia.up.railway.app
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
- 🎞️ [yt-dlp](https://github.com/yt-dlp/yt-dlp) — downloader usado como fallback do YouTube
- 🚂 [Templates do Railway](https://railway.com/templates)
- 🛠️ [Railway CLI (GitHub)](https://github.com/railwayapp/cli) — usado para o deploy local via `railway up`
- 📖 [Documentação da API Cobalt](https://github.com/imputnet/cobalt/blob/main/docs/api.md)

