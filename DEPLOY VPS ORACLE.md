# 🚀 Passo a Passo: Deploy do SaveClip na sua VM da Oracle

> **Objetivo:** publicar o **SaveClip** (Site Downloader) na sua VM da Oracle Cloud, de forma que o site fique acessível pela internet em `http://147.15.122.54`, com tudo funcionando: **YouTube (MP4/MP3 via yt-dlp + ffmpeg, com fallback automático para a API Cobalt)** e **Instagram / Facebook / TikTok (via API Cobalt)**.

> ✅ **Status atual (24/09/2026):** o site está **no ar em HTTPS** — **https://saverclip.mobaily.com.br** (o `http://` redireciona sozinho) — com o **Caddy** (Let's Encrypt) na frente dos containers. A **Cobalt** atende a **API** em `https://saverclip.mobaily.com.br/cobalt/` (sub-caminho, sem DNS novo) e os **downloads** em `https://saverclip.mobaily.com.br/tunnel?...` (na raiz do domínio — a Cobalt usa só a origem do `API_URL`; veja 13.1). A **porta 443 já está liberada** na Security List da Oracle. Para ativar/reverter o HTTPS, veja a **seção 13**.

**Sua VM (verificada na prática em 13/08/2026):**

| Item | Valor |
|---|---|
| IP público | `147.15.122.54` |
| Usuário SSH | `ubuntu` |
| SO | Ubuntu 24.04 LTS |
| Arquitetura | ARM64 (Ampere A1 — Always Free) |
| Recursos | 2 vCPUs, 11 GB RAM, 193 GB disco |
| Chave SSH que funciona | `C:\Users\Eduardo\Downloads\ssh-key-2026-08-13.key` |

**O que você vai aprender:**

1. Como conectar na VM (revisão)
2. Como colocar o código mais novo no GitHub (fonte de verdade do deploy)
3. O que é Docker e como instalá-lo na VM
4. Como rodar o app dentro de um container
5. Como abrir as portas no firewall da Oracle **(a parte que mais dá dor de cabeça)**
6. Como atualizar o site depois de mexer no código
7. **Como hospedar a API Cobalt na própria VM** (Instagram/Facebook/TikTok) — sem depender do Railway
8. YouTube bloqueado pela VM: cookies e fallback Cobalt
9. (Bônus) HTTPS grátis com Caddy

---

## 0. Entenda o que vamos construir

Antes de digitar comandos, entenda o fluxo completo:

```
Navegador do usuário
        │
        ▼
  http://147.15.122.54:80    ← porta aberta no firewall da Oracle (seção 8)
        │
        ▼
  Container Docker "saveclip"   ← imagem com Python + ffmpeg + yt-dlp
        │
        ▼
  Flask server.py ouvindo em 0.0.0.0:8080   (dentro do container)
        │
        ├── URL do YouTube  ──►  yt-dlp + ffmpeg (baixa direto na VM)
        │                        └─ se o YouTube bloquear → API Cobalt (fallback)
        └── IG/Facebook/TikTok ─►  API Cobalt (COBALT_API_URL)
```

**Conceitos importantes (guarde estes 6):**

| Conceito | O que é | No nosso caso |
|---|---|---|
| **VM / Instance** | Máquina virtual com IP público | Sua instância Ubuntu 24.04 |
| **Docker** | Empacota o app com todas as dependências numa imagem | O projeto já tem um `Dockerfile` pronto |
| **Imagem** | O "molde": código + SO + bibliotecas | `saveclip:latest` |
| **Container** | Uma "cópia rodando" da imagem | `saveclip` |
| **Porta** | Número que identifica uma "entrada" de rede | 80 (HTTP) e 8080 (app) |
| **Security List** | Firewall no nível da nuvem Oracle | Precisa liberar a porta 80 |
| **.env** | Arquivo com configurações/segredos | `COBALT_API_URL`, `PORT` |

> 💡 **A mentalidade do deploy:** o seu PC **edita** o código; o **GitHub guarda** o código; a **VM roda** o código (24h/dia); o **Docker** garante que o app rode igual em qualquer máquina.

---

## 1. Pré-requisitos

Você já tem quase tudo:

- ✅ Chave SSH válida nos Downloads (`ssh-key-2026-08-13.key`)
- ✅ VM no ar (conexão já testada na seção 2)
- ✅ Projeto com `Dockerfile` (o "molde" do container)
- ✅ Repositório GitHub público (`github.com/Duhsv92/Site-Downloader`)
- ❌ Docker **não instalado** — mas vamos instalá-lo **na VM**, não no seu Windows

> 💡 **Por que Docker na VM e não no Windows?** O container precisa rodar em uma máquina com IP público e que fique ligada o tempo todo — essa é a VM. O seu PC serve só para editar e enviar o código.

---

## 2. Conectar na VM (revisão rápida)

Abra o **PowerShell** no Windows e use a chave do Downloads:

```powershell
ssh -i C:\Users\Eduardo\Downloads\ssh-key-2026-08-13.key ubuntu@147.15.122.54
```

Você deve cair no terminal da VM. Confirme:

```bash
whoami        # deve mostrar: ubuntu
uname -m      # deve mostrar: aarch64  (prova que é ARM64)
```

---

## 3. Colocar o código mais novo no GitHub (fonte de verdade)

Na VM vamos **baixar o código do GitHub** (`git clone`). Por isso o GitHub precisa estar com a versão mais nova do projeto.

> ⚠️ **Importante:** o GitHub está **1 commit atrás** do seu PC (o `Dockerfile` e o `railway.json` ainda não subiram). Sem este passo, o `docker build` na VM falharia porque não existiria `Dockerfile`!

**No seu Windows** (na pasta `C:\Users\Eduardo\Documents\GitHub\Site Downloader`):

1. Veja o que mudou:
   ```powershell
   git status
   ```

2. O arquivo `api\Untitled` é um rascunho que não faz parte do site. Apague-o:
   ```powershell
   Remove-Item .\api\Untitled
   ```

3. Envie tudo (o `.env` **não** sobe — ele está no `.gitignore`):
   ```powershell
   git add .
   git commit -m "Deploy: Dockerfile, railway.json, docker-compose e modulo yt-dlp"
   git push origin main
   ```

4. Confira no navegador: **github.com/Duhsv92/Site-Downloader** → a lista de arquivos deve mostrar `Dockerfile`, `railway.json` e `docker-compose.yml`.

> 📚 **Aprenda o ciclo do git:** `git add .` marca os arquivos para envio → `git commit` cria um "ponto de salvamento" local → `git push` envia esse ponto para o GitHub. Daqui para frente, **toda atualização do site** segue exatamente esse ciclo (e o guia repete isso na seção 10).

---

## 4. Instalar o Docker na VM

Conectado na VM, **atualize o sistema**:

```bash
sudo apt update && sudo apt upgrade -y
```

**Instale o Docker** usando o script oficial da própria Docker (simples e seguro):

```bash
curl -fsSL https://get.docker.com | sudo sh
```

> 📚 **Aprenda:** esse comando baixa o instalador oficial e executa com `sudo`. Em produção você pode preferir instalar via repositório APT, mas o script é o caminho mais rápido para aprender.

**Adicione seu usuário ao grupo `docker`** (assim você não precisa digitar `sudo` em todo comando Docker):

```bash
sudo usermod -aG docker $USER
```

**Saia e entre na VM de novo** (o grupo só vale em novos logins):

```bash
exit
# no Windows, conecte de novo:
ssh -i C:\Users\Eduardo\Downloads\ssh-key-2026-08-13.key ubuntu@147.15.122.54
```

**Teste se o Docker funciona:**

```bash
docker --version
docker run hello-world
```

Se aparecer a mensagem *"Hello from Docker!"*, está pronto. 🎉


---

## 5. Baixar o código na VM

```bash
cd ~
git clone https://github.com/Duhsv92/Site-Downloader.git
cd Site-Downloader
ls
```

Você deve ver o arquivo **`Dockerfile`** na listagem (prova que o push da seção 3 funcionou).

Agora **crie o arquivo de variáveis de ambiente na VM** (ele não vem do GitHub de propósito — é o seu segredo):

```bash
nano .env
```

Cole este conteúdo (no `nano`: `Ctrl+V` cola no terminal SSH; `Ctrl+O` salva; `Ctrl+X` sai):

```env
# Endereço INTERNO da Cobalt (mesma rede do Docker) — rápido e seguro.
COBALT_API_URL=http://cobalt:9000
# Chave de API da sua instância Cobalt (UUID do arquivo keys.json — seção 11)
COBALT_API_KEY=cole-aqui-o-uuid-gerado-na-seção-11
COBALT_AUTH_SCHEME=Api-Key
# Porta INTERNA do site dentro do container e o endereço público dele
PORT=8080
APP_URL=http://saverclip.mobaily.com.br
# Depois de ativar o HTTPS (seção 13), troque a linha acima por:
# APP_URL=https://saverclip.mobaily.com.br
```

- `COBALT_API_URL` → sua instância Cobalt rodando **na própria VM** (processa Instagram, Facebook e TikTok, e é o **fallback** quando o YouTube bloqueia a VM). Como o site e a Cobalt ficam na **mesma rede do Docker**, usamos o nome `cobalt:9000` — assim nada sai pela internet e a API fica escondida dos visitantes.
- `COBALT_API_KEY` + `COBALT_AUTH_SCHEME` → a chave que autoriza o site a usar a sua Cobalt (veja a seção 11). Devem ser **iguais às do `keys.json`** da VM.
- `PORT=8080` → porta **dentro do container**. Não mude se usar o `docker-compose.yml` da seção 7 (o mapeamento de portas depende dela).
- `APP_URL` → endereço público do site (usado apenas para referência/logs — o código não lê esta variável). No modo HTTPS da **seção 13**, ajuste para `https://saverclip.mobaily.com.br`.

> 🍪 **Cookies do YouTube (opcional):** se quiser reduzir o bloqueio do YouTube, coloque um arquivo `cookies.txt` (exportado do navegador logado) na pasta do projeto. O `docker-compose.yml` já monta ele no container (variável `YTDLP_COOKIES`) — veja a seção 11.

> 📚 **Aprenda:** o `.env` é a configuração "viva" da aplicação. O `server.py` lê as variáveis com `os.environ.get(...)` no momento em que inicia. Por isso, **se você mudar o `.env`, precisa reiniciar o container** (`docker compose restart`).

---

## 6. (Opcional, didático) Primeiro deploy sem Docker Compose

Esta etapa é para você **entender o que acontece por baixo dos panos**. Depois vamos automatizar com o Compose.

**1. Construir a imagem** (baixa o Python, instala ffmpeg, yt-dlp e as dependências — a primeira vez demora 2 a 5 minutos):

```bash
docker build -t saveclip .
```

> 📚 **Aprenda:** o `Dockerfile` do projeto faz basicamente 3 coisas: usa o Python como base, instala o **ffmpeg** (obrigatório para MP4 em alta qualidade e MP3) e copia o código para a imagem. É isso que garante que o app rode igual em qualquer máquina.

**2. Rodar o container:**

```bash
docker run -d --name saveclip -p 80:8080 \
  -e COBALT_API_URL=http://saverclip.mobaily.com.br:8080 \
  saveclip
```

> 💡 **Atenção:** este teste manual (sem Compose) ainda usaria uma Cobalt externa. A partir da seção 7 a Cobalt roda **dentro da própria VM** (serviço `cobalt`) e o `.env` do site aponta para a rede interna (`http://cobalt:9000`) — veja a **seção 11**.

**3. Acompanhar os logs** (pode abrir em outro terminal da VM):

```bash
docker logs -f saveclip
```

> 📚 **Aprenda cada parâmetro:** `-d` roda em segundo plano (detached) → `--name` dá um nome ao container → `-p 80:8080` faz a porta 80 da VM apontar para a porta 8080 do container (é assim que o mundo externo chega no Flask) → `-e` injeta uma variável de ambiente sem arquivo. Nenhum parâmetro está aí por acaso.

**Para apagar e partir para a versão profissional:**

```bash
docker rm -f saveclip
```

---

## 7. Deploy profissional com Docker Compose

O Docker Compose transforma aquele comando gigante em um arquivo simples e **repetível**. Já deixei o `docker-compose.yml` pronto na raiz do projeto — ele sobe **dois containers**:

```yaml
services:
  saveclip:
    build: .                  # constrói a partir do Dockerfile local
    image: saveclip:latest    # nome da imagem gerada
    container_name: saveclip
    restart: unless-stopped   # sobe sozinho se a VM reiniciar
    ports:
      - "80:8080"             # VM:80  -> container:8080 (site principal)
    env_file:
      - .env                  # lê as variáveis do arquivo .env
    environment:
      - YTDLP_COOKIES=/app/cookies.txt   # cookies do YouTube (opcional, seção 12)
    volumes:
      - ./cookies.txt:/app/cookies.txt:ro   # monta o cookies.txt da VM

  cobalt:
    image: ghcr.io/imputnet/cobalt:11   # imagem oficial (funciona em ARM64)
    container_name: cobalt
    restart: unless-stopped
    ports:
      - "8080:9000"           # VM:8080 -> Cobalt:9000 (links de /tunnel)
    environment:
      API_URL: "http://saverclip.mobaily.com.br:8080/"   # URL pública, com "/" no fim
      API_KEY_URL: "file:///keys.json"    # chave de API (seção 11)
      API_AUTH_REQUIRED: "1"
      ...                     # demais ajustes já vêm prontos no arquivo
    volumes:
      - ./keys.json:/keys.json:ro
```

> ⚠️ **Mudança importante na porta 8080:** antes ela era um "atalho" para testar o site. Agora ela pertence à **API Cobalt**, porque os links de `/tunnel` (o download que o navegador do visitante abre) precisam de uma porta pública. O site continua em `http://IP` (porta 80) e a porta 8080 já está liberada no firewall da Oracle — nenhuma regra nova é necessária. (Se mais adiante você ativar o HTTPS da **seção 13**, o Caddy assume as portas 80/443 e a 8080 deixa de ser publicada.)

**Suba com um único comando:**

```bash
docker compose up -d --build
```

**Confirme que está rodando:**

```bash
docker compose ps
```

Resultado esperado: container `saveclip` com estado `Up` e as portas mapeadas.


---

## 8. Abrir a porta no firewall da Oracle Cloud (A PEGADINHA!)

O container está rodando, mas **a Oracle bloqueia tudo, exceto SSH (22), por padrão**. Sem este passo, o navegador não carrega nada e parece que tudo falhou.

1. Acesse o console da Oracle: **cloud.oracle.com** (faça login com a conta da VM)
2. Menu ☰ (canto superior esquerdo) → **Networking** → **Virtual cloud networks**
3. Clique na VCN da sua instância
4. No menu lateral **Resources**, clique em **Security Lists** → **Default Security List** (ou a que sua instância usa)
5. Clique em **Add Ingress Rules**
6. Preencha:
   - **Source Type:** `CIDR`
   - **Source CIDR:** `0.0.0.0/0` (libera para a internet inteira — é isso que queremos para um site público)
   - **IP Protocol:** `TCP`
   - **Destination Port Range:** `80`
   - **Destination Port Range:** `8080` → **obrigatório** (é a porta pública da API Cobalt que roda na VM — seção 11; sem ela, os links de download do Instagram/Facebook/TikTok não abrem no navegador)
7. Clique em **Add Ingress Rules**.

> ⚠️ **Importante (erro comum):** cada VM está ligada a uma **Subnet**, e cada Subnet tem uma **Security List** própria. Se a sua instância usa uma Subnet pública diferente da padrão, edite a Security List **dessa subnet**. Se você criou um **Network Security Group (NSG)**, edite também — é um firewall separado que a Oracle aplica direto na instância.

**Verifique também o firewall do Ubuntu** (nas imagens da Oracle normalmente vem inativo):

```bash
sudo ufw status
```

- Se aparecer `inactive` → perfeito, nada a fazer.
- Se estiver `active` → libere as portas:
  ```bash
  sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 8080/tcp
  ```

> 📚 **Aprenda:** existem **dois firewalls** em jogo. O da **Oracle** (Security List/NSG, na nuvem) e o do **SO** (ufw, dentro da VM). O tráfego só chega ao seu site se passar pelos dois. Quando "não conecta", 99% das vezes é o da Oracle.

---

## 9. Testar no navegador

Abra no seu navegador:

- **http://147.15.122.54** (site principal, via porta 80)
- ou **http://saverclip.mobaily.com.br** (mesmo site, pelo seu domínio)

Testes rápidos:
- Cole um link do **YouTube** → deve baixar MP4 1080p e MP3 320kbps (usa o yt-dlp + ffmpeg que estão dentro da imagem).
- Cole um link de **Instagram / Facebook / TikTok** → deve processar via API Cobalt (self-hosted na própria VM).

**Testando a API Cobalt direto (sem o site):**

```bash
# Lê a chave do .env para usar no teste
KEY=$(grep COBALT_API_KEY ~/Site-Downloader/.env | cut -d= -f2)

# 1) A instância está viva? (devolve JSON com "cobalt": {"version": "11.x"...})
curl -s http://127.0.0.1:8080/

# 2) Pela internet, do seu PC: http://saverclip.mobaily.com.br:8080/

# 3) A chave está valendo? (deve responder que o link é inválido, e NÃO erro de autenticação)
curl -s -X POST http://127.0.0.1:8080/ \
  -H "Accept: application/json" -H "Content-Type: application/json" \
  -H "Authorization: Api-Key $KEY" \
  -d '{"url":"https://www.instagram.com/reel/teste/"}'
#    -> {"status":"error","error":{"code":"error.api.fetch.empty"}}  (link de mentira: o importante é NÃO ser erro de chave)

# 4) Sem a chave a API tem de RECUSAR (prova que ninguém de fora usa a sua instância)
curl -s -X POST http://127.0.0.1:8080/ \
  -H "Accept: application/json" -H "Content-Type: application/json" \
  -d '{"url":"https://www.instagram.com/reel/teste/"}'
#    -> {"status":"error","error":{"code":"error.api.auth.key.missing"}}

# 5) O /tunnel abre no navegador do visitante? (precisa dar 200 + Access-Control-Allow-Origin: *)
OUT=$(curl -s -X POST http://127.0.0.1:8080/ \
  -H "Accept: application/json" -H "Content-Type: application/json" \
  -H "Authorization: Api-Key $KEY" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","videoQuality":"480"}')
TUN=$(echo "$OUT" | python3 -c "import sys,json;print(json.load(sys.stdin).get('url',''))")
curl -s -D - -o /dev/null "$TUN" | head -5   # HTTP/1.1 200 OK + Access-Control-Allow-Origin: *
```

> ✅ **Verificado em 25/09/2026** (`1a852fe`) na VM real: os 5 testes acima responderam exatamente como indicado nos comentários. O teste 4 (`api-key.missing`) é o mais importante: confirma que a sua instância está protegida.

Se aparecer erro, veja a seção **14 (Troubleshooting)** — cada mensagem de erro já tem a causa provável e a solução.

---

## 10. Atualizar o site (fluxo de trabalho do dia a dia)

Depois que tudo funciona, atualizar o site leva **30 segundos**:

**No seu Windows** (pasta do projeto):
```powershell
git add .
git commit -m "descrição da mudança"
git push origin main
```

**Na VM:**
```bash
cd ~/Site-Downloader
git pull
docker compose up -d --build
```

Pronto. O Compose detecta que o código mudou, reconstrói a imagem e recria o container sem derrubar nada por mais que alguns segundos.


---

## 11. Hospedar a API Cobalt na sua própria VM (sem Railway) 🐋

O Railway deixou de ser confiável para este projeto: **o trial da conta expirou** e o serviço da Cobalt foi removido (`502 Application failed to respond` / `404 Application not found`). A solução definitiva é rodar **a mesma imagem oficial da Cobalt dentro da sua VM** — de graça, sem limite de trial, sem depender de terceiros e com o site e a API na mesma rede do Docker.

O `docker-compose.yml` da seção 7 **já sobe a Cobalt** junto com o site. Falta só criar a chave de API (`keys.json`), ajustar o `.env` e subir.

### 11.1. Por que a Cobalt precisa da porta 8080

A Cobalt não devolve o arquivo direto: ela responde com um link temporário de **`/tunnel`** (é assim que ela esconde o endereço real do CDN do Instagram/TikTok). Quem abre esse link é o **navegador do visitante**, então ele precisa ser público. Por isso o container `cobalt` publica a porta **8080** da VM — a mesma que já está liberada na Security List da Oracle (seção 8). **Nenhuma regra de firewall nova é necessária.**

```
Navegador ──HTTP :80──► container saveclip ──(rede interna)──► cobalt:9000
    │                                                                ▲
    └──── abre o link http://saverclip.mobaily.com.br:8080/tunnel?… ──┘
```

> 💡 **Por que a porta 8080 e não 9000?** A imagem da Cobalt escuta em `9000` **dentro** do container (`API_PORT`). Como a porta 9000 ainda não está liberada na Security List da Oracle, publicamos a Cobalt na **8080**, que já está aberta. Para usar a 9000, crie uma regra de ingress para `9000` (seção 8) e troque o mapeamento para `"9000:9000"`.

### 11.2. Criar o `keys.json` (a chave de API)

Sem chave, qualquer pessoa poderia processar links na sua instância. Com `API_AUTH_REQUIRED=1` (já configurado no compose), **só quem tem a chave consegue chamar a API** — os links de `/tunnel` continuam abrindo normalmente no navegador (eles são assinados pela própria Cobalt).

**Na VM** (conectado por SSH), rode o bloco abaixo:

```bash
cd ~/Site-Downloader

# 1) Gera um UUID novo — é a sua chave secreta
KEY=$(python3 -c "import uuid; print(uuid.uuid4())")
echo "Sua chave: $KEY"

# 2) Cria o keys.json com essa chave
printf '{\n  "%s": {\n    "name": "saveclip",\n    "limit": 120,\n    "allowedServices": "all"\n  }\n}\n' "$KEY" > keys.json

# 3) Usa a MESMA chave no .env do site
sed -i "s|^COBALT_API_URL=.*|COBALT_API_URL=http://cobalt:9000|" .env
grep -q '^COBALT_API_KEY=' .env && sed -i "s|^COBALT_API_KEY=.*|COBALT_API_KEY=$KEY|" .env || echo "COBALT_API_KEY=$KEY" >> .env
grep -q '^COBALT_AUTH_SCHEME=' .env || echo "COBALT_AUTH_SCHEME=Api-Key" >> .env

cat .env      # confira o resultado
```

- **`limit`** → quantos pedidos por minuto essa chave pode fazer (a janela é o `RATELIMIT_WINDOW=60` do compose). Use `"unlimited"` se quiser sem limite.
- O `keys.json` **nunca vai para o GitHub** (está no `.gitignore`). O modelo versionado é o `keys.json.example`.

### 11.3. Subir os containers

```bash
cd ~/Site-Downloader
docker compose up -d --build    # baixa a imagem da Cobalt (~1-2 min), reconstrói o site e sobe os 2 containers
docker compose ps               # devem aparecer "saveclip" e "cobalt" com status Up
docker logs --tail 25 cobalt    # deve mostrar "cobalt API ^ω^" e "url: http://saverclip.mobaily.com.br:8080/"
```

> 💡 **Use `--build`** na primeira vez (mudamos o `docker-compose.yml`: a porta 8080 passou do site para a Cobalt). Depois disso, `docker compose up -d` basta para mudanças só de `.env`.
>
> 📌 **Conferido em 25/09/2026:** o `docker compose ps` mostrou
> `cobalt ... 0.0.0.0:8080->9000/tcp` e `saveclip ... 0.0.0.0:80->8080/tcp`, e o log da Cobalt trouxe
> `api keys loaded successfully!` — ou seja, o `keys.json` foi lido corretamente.

Valide de dentro da VM (o `GET /` devolve as informações da instância):

```bash
curl -s http://127.0.0.1:8080/
```

E do seu computador, para provar que está público na internet:

```powershell
curl.exe -s http://saverclip.mobaily.com.br:8080/
```

**Teste final (obrigatório):** abra **http://saverclip.mobaily.com.br**, cole um link de **Instagram/TikTok** e faça o download. Se o vídeo baixar, o caminho `site → cobalt:9000 → /tunnel` está 100% funcionando.

### 11.4. Manutenção

```bash
docker compose pull cobalt && docker compose up -d cobalt   # atualiza a Cobalt (mesma v11.x)
docker logs --tail 50 cobalt                                # logs da API
docker compose restart saveclip                             # recarrega o .env do site
```

> 🔄 **Atualização automática (opcional):** a imagem oficial sugere o [watchtower](https://github.com/containrrr/watchtower) para atualizar a Cobalt sozinho. Não deixei ativo por padrão para o deploy ser previsível — se quiser, descomente o serviço `watchtower` do exemplo oficial da Cobalt.
>
> 🔐 **HTTPS na Cobalt:** se você colocar o site em HTTPS (seção 13), troque o `API_URL` do serviço `cobalt` para `https://seu-dominio/` — senão o navegador bloqueia o download por *mixed content*.
>
> 🍪 **Instagram exigindo login?** Crie um `cookies.json` (modelo no [exemplo oficial](https://github.com/imputnet/cobalt/blob/main/docs/examples/cookies.example.json)) na pasta do projeto e adicione no serviço `cobalt`: `COOKIE_PATH: "/cookies.json"` + volume `- ./cookies.json:/cookies.json:ro`.

> 🚂 **Quer voltar a usar uma instância externa (Railway)?** Veja [COMO CONFIGURAR.md](file:///c:/Users/Eduardo/Documents/GitHub/Site%20Downloader/COMO%20CONFIGURAR.md), seção 5 — e depois atualize o `COBALT_API_URL` do `.env` da VM, sem esquecer `docker compose restart saveclip`.

---

## 12. (Importante) YouTube bloqueado pela VM — cookies e fallback Cobalt

**Sintoma:** alguns vídeos do YouTube (principalmente música) falham com **"Erro na API (HTTP 400)"**. Nos logs do container aparece:

```
ERROR: [youtube] <ID>: Sign in to confirm you're not a bot.
Use --cookies-from-browser or --cookies for the authentication.
```

**Causa:** o YouTube bloqueia seletivamente vídeos para **IPs de datacenter** (como o da Oracle). Não existe player client que contorne isso sozinho — é bloqueio por reputação de IP.

**O que o projeto já faz (automático, sem ação sua):**

1. Tenta **player clients** confiáveis (`tv`/`android`).
2. Se bloquear, faz **retry automático** rotacionando os clients (até 3 tentativas, com espera curta — o fallback entra em ~10-15s).
3. Se ainda falhar, **fallback automático para a API Cobalt** (`server.py` → `_cobalt_request`). Desde a seção 11 essa Cobalt roda **na própria VM** (mesmo IP), então o resultado depende da mesma reputação de IP — quando ela consegue extrair, o download continua (em qualidade menor). O que realmente aumenta a taxa de sucesso no caminho de alta qualidade são os **cookies** abaixo.

**Como melhorar o yt-dlp direto (opcional): cookies de uma conta logada**

1. Instale a extensão **"Get cookies.txt LOCALLY"** no navegador.
2. Acesse **youtube.com** logado e clique no ícone da extensão → **Export**.
3. Envie o arquivo para a VM (PowerShell):
   ```powershell
   scp -i C:\Users\Eduardo\Downloads\ssh-key-2026-08-13.key C:\Users\Eduardo\Downloads\cookies.txt ubuntu@147.15.122.54:~/Site-Downloader/cookies.txt
   ```
4. Reinicie o container:
   ```bash
   cd ~/Site-Downloader && docker compose restart
   ```

O arquivo é montado em `/app/cookies.txt` (variável `YTDLP_COOKIES` no `docker-compose.yml`) e **nunca vai para o GitHub** (está no `.gitignore`). Os cookies **expirem** — quando o erro voltar, re-exporte e repita os passos 3 e 4.

> 💡 **Resumo da estratégia:** o **yt-dlp direto** entrega 1080p/MP3 320kbps quando o YouTube libera; o **fallback Cobalt** garante que nenhum vídeo fique sem download; os **cookies** aumentam a chance do caminho de melhor qualidade.

---

## 13. HTTPS grátis com Caddy (site + Cobalt)

O site responde em **`https://saverclip.mobaily.com.br`** (o `http://` redireciona sozinho). Quem faz isso é o **Caddy**, um terceiro container que fica na frente dos outros dois: ele pega e renova o certificado do **Let's Encrypt** sozinho — nada de `certbot`, nada de cron — e repassa o tráfego pela rede interna do Docker. O modo HTTP puro continua existindo; para voltar veja **13.4**.

O único pré-requisito é **um** item (feito em 24/09/2026):

| # | O que fazer | Onde fazer |
|---|---|---|
| 1 | **Liberar a porta 443** (TCP, origem `0.0.0.0/0`). A 80 já está liberada desde a seção 8. | Console da Oracle → **Security List** (mesmo passo a passo da seção 8, trocando 80 por 443) |

> 🔎 **Como saber se a 443 está realmente aberta:** `Connection timed out` no seu PC **não** prova que a porta está fechada — com nada escutando na 443, a VM responde com um ICMP que muitos roteadores/ISPs descartam em silêncio (some só depois que o Caddy sobe e escuta nessa porta). O teste que não mente é espiar, na própria VM, se o pacote externo chegou:
>
> ```bash
> # 1) na VM: espia (só registra no log, NÃO bloqueia nada)
> sudo iptables -I INPUT 1 -p tcp --dport 443 -m limit --limit 5/min -j LOG --log-prefix "PROBE443: "
> # 2) no seu PC: curl.exe --max-time 8 https://saverclip.mobaily.com.br/
> # 3) na VM: aparecendo "DPT=443" aqui, a Oracle está liberando
> sudo journalctl -k --since "-2 min" | grep PROBE443
> # 4) na VM: remove o espião (o firewall volta ao estado original)
> sudo iptables -D INPUT -p tcp --dport 443 -m limit --limit 5/min -j LOG --log-prefix "PROBE443: "
> ```

Do seu PC, dá para conferir a 443 e o DNS assim:

```powershell
Test-NetConnection saverclip.mobaily.com.br -Port 443 -InformationLevel Quiet              # tem que dar True
Resolve-DnsName saverclip.mobaily.com.br -Server 8.8.8.8 | Select-Object Name,IPAddress   # 147.15.122.54
```

### 13.1. Por que a Cobalt também precisa ser servida em HTTPS?

Uma página em `https://` **não consegue** baixar um arquivo servido em `http://` — o navegador bloqueia isso como *mixed content*. E quem baixa os arquivos pesados é o **navegador do visitante**, abrindo os links de `/tunnel` gerados pela Cobalt. Ou seja: se o site é `https://`, o link de `/tunnel` **também** precisa ser `https://`. Como a Cobalt não tem opção de "confiar no proxy", quem diz qual é a URL pública é a variável **`API_URL`** do container (`docker-compose.https.yml`).

Existem duas formas de resolver — o projeto está configurado com a **primeira**:

| Forma | Como o navegador chama a Cobalt | Precisa de DNS novo? |
|---|---|---|
| **Sub-caminho** (é a que está ativa) | API em `https://saverclip.mobaily.com.br/cobalt/` + downloads em `https://saverclip.mobaily.com.br/tunnel?...` | **Não** — usa o domínio que já existe |
| Subdomínio (variante comentada) | tudo em `https://cobalt.saverclip.mobaily.com.br/` | Sim: registro `A` no Registro.br + ajustar o `Caddyfile` |

> ⚠️ **Detalhe que custa caro se esquecer:** a Cobalt monta o link de `/tunnel` usando **só a origem** (esquema + domínio) do valor de `API_URL` — **o caminho é ignorado**. Então, com `API_URL=https://saverclip.mobaily.com.br/`, os links saem na **raiz** (`/tunnel?id=...`) e não em `/cobalt/tunnel`. Por isso o `Caddyfile` tem **duas** rotas para a Cobalt: `handle /tunnel*` (os downloads, na raiz, sem tirar prefixo) e `handle_path /cobalt/*` (a API, no sub-caminho, tirando o prefixo). No navegador, `.../tunnel` **não pode** cair no site — daria HTML no lugar do vídeo.

A variante com subdomínio está comentada no fim do `Caddyfile` — lá o domínio inteiro é da Cobalt, então `/tunnel` já resolve sozinho e a `API_URL` é `https://cobalt.saverclip.mobaily.com.br/`.

> 🔎 O tráfego **site → Cobalt continua interno** (`http://cobalt:9000`, pela rede do Docker). Isso não muda com o HTTPS porque não passa pela internet — quem precisa de TLS é só o link que o navegador abre.

### 13.2. Ativando o HTTPS (2 comandos)

Na VM, dentro da pasta do projeto:

```bash
cd ~/Site-Downloader
git pull                                                        # garante o Caddyfile e o docker-compose.https.yml
docker compose -f docker-compose.yml -f docker-compose.https.yml up -d
```

Confira:

```bash
docker compose ps                # agora são 3 containers: caddy, saveclip e cobalt (todos Up)
docker logs --tail 30 caddy      # procure por "certificate obtained successfully"
```

O `docker-compose.https.yml` é um **arquivo de override**: ele **não substitui** o `docker-compose.yml`, é aplicado *em cima* dele (por isso os dois `-f`). O que ele muda:

- sobe o container **`caddy`** nas portas **80 e 443** (usando o `Caddyfile` da raiz do projeto);
- o site **deixa de publicar a porta 80** (agora ela é do Caddy) e passa a existir na rede interna do Docker — e em `127.0.0.1:8090` na própria VM, para testes com `curl`;
- a Cobalt **deixa de publicar a 8080** e passa a usar `API_URL=https://saverclip.mobaily.com.br/` (só a origem dessa URL entra nos links de `/tunnel`), com o Caddy respondendo por `/tunnel*` e `/cobalt/*`;
- sobe os limites de rate limit da Cobalt (motivo explicado em **13.5**).

Em ~1 minuto: **https://saverclip.mobaily.com.br** ✅ (o `http://` redireciona sozinho para `https://`).

> ⚠️ **Depois de ativar o HTTPS, TODO update precisa dos dois `-f`.** O comando "normal" de atualização (`docker compose up -d --build`, sem o `-f docker-compose.https.yml`) **derruba o modo HTTPS**: ele volta a mapear a porta **80** para o site, que já é do Caddy — o container do site não sobe (*port is already allocated*) e o domínio passa a responder **502**. Nesse caso, rode de novo com os dois `-f` (ou volte ao HTTP pela **13.4** e ative outra vez).
>
> ```bash
> cd ~/Site-Downloader
> git pull
> docker compose -f docker-compose.yml -f docker-compose.https.yml up -d --build   # <- sempre com os dois -f
> ```

### 13.3. Testes (do seu PC, no PowerShell)

```powershell
# 1) O site responde em HTTPS com certificado válido
curl.exe -sI https://saverclip.mobaily.com.br/ | Select-String "HTTP/|server:"

# 2) O HTTP redireciona para HTTPS (deve vir 308 + location: https://...)
curl.exe -sI http://saverclip.mobaily.com.br/ | Select-String "HTTP/|location:"

# 3) A Cobalt está pública no sub-caminho (resposta JSON da instância)
curl.exe -s https://saverclip.mobaily.com.br/cobalt/

# 4) /cobalt (sem a barra no fim) redireciona para /cobalt/
curl.exe -sI https://saverclip.mobaily.com.br/cobalt | Select-String "HTTP/|location:"

# 5) O /tunnel responde com CORS liberado (o navegador precisa disso) — via API
curl.exe -sI "https://saverclip.mobaily.com.br/cobalt/tunnel?url=x" | Select-String "HTTP/|access-control-allow-origin"

# 6) A RAIZ /tunnel também tem de ser a Cobalt (400 + CORS) — e NÃO o site.
#    Se aqui vier "200" com "Content-Type: text/html", o download vai baixar
#    uma página HTML em vez do vídeo (veja 13.5).
curl.exe -sI "https://saverclip.mobaily.com.br/tunnel?url=x" | Select-String "HTTP/|content-type|access-control-allow-origin"
```

**Teste final (obrigatório):** abra **https://saverclip.mobaily.com.br**, cole um link de Instagram/TikTok e faça o download. É esse download que prova que o `/tunnel` está em HTTPS e que não há bloqueio de *mixed content*.

### 13.4. Voltando para HTTP

```bash
cd ~/Site-Downloader
docker compose up -d            # sem o -f docker-compose.https.yml: o Caddy fica de fora
docker rm -f caddy              # opcional: remove o container do Caddy
```

Os certificados continuam guardados no volume `caddy_data`, então voltar para HTTPS depois é instantâneo (sem bater no limite de tentativas do Let's Encrypt).

### 13.5. Detalhes que você vai querer saber

- **Os rate limits da Cobalt viram globais.** A Cobalt não tem opção de "confiar no proxy": atrás do Caddy ela enxerga **todas** as requisições como vindas do container do Caddy (e não de cada visitante). Por isso o `docker-compose.https.yml` sobe `RATELIMIT_MAX` para 60/min e `TUNNEL_RATELIMIT_MAX` para 120/min. Com poucos visitantes a diferença é invisível; com muitos, o limite passa a ser do site inteiro.
- **`http://147.15.122.54` deixa de abrir o site** no modo HTTPS: o Caddy só responde pelos domínios listados no `Caddyfile`. Use o domínio (e volte ao modo HTTP se precisar testar pelo IP).
- **Nada de IP fixo no código:** o `Caddyfile` fala pelos *nomes* dos serviços (`saveclip:8080` e `cobalt:9000`) — se as portas internas mudarem, é só ajustar ali.
- **O link de `/tunnel` mora na RAIZ do domínio, não dentro de `/cobalt/`.** Não é capricho: a Cobalt não tem opção de prefixo/caminho — ela monta o link a partir da origem do `API_URL`. Por isso existe no `Caddyfile` a rota `handle /tunnel*` → `cobalt:9000`, avaliada **antes** do site. Sintoma clássico de que ela saiu do lugar (ou de que o site ganhou uma rota `/tunnel`): o download salva um arquivo **HTML** em vez do vídeo.
- **Trocar de domínio no futuro:** atualize o bloco do domínio no `Caddyfile`, a `API_URL` no `docker-compose.https.yml` e suba de novo com os dois `-f`.
- **Renovação:** automática (o Caddy renova aos 2/3 da validade); para conferir: `docker logs caddy | grep -i certificate`.
- **Se apagar o volume `caddy_data`** o Caddy reemite os certificados — cuidado, o Let's Encrypt tem limite de tentativas por domínio.
- **Prefere um subdomínio só para a Cobalt?** Em vez do sub-caminho `/cobalt/`, registre `cobalt.saverclip.mobaily.com.br` (tipo `A` → `147.15.122.54`) no Registro.br, descomente a variante no fim do `Caddyfile`, troque a `API_URL` do `docker-compose.https.yml` para `https://cobalt.saverclip.mobaily.com.br/` e suba de novo com os dois `-f`. Vantagem: um domínio para cada coisa. Desvantagem: mais uma regra de DNS para manter.

> 📚 **Aprenda:** aqui o Caddy faz o papel de *reverse proxy* com TLS: ele **termina o HTTPS** (porta 443), "decifra" a requisição e a entrega já em HTTP simples para o container certo, pela rede interna do Docker. É por isso que a porta 80 deixa de ser do site e a 8080 deixa de ser da Cobalt — do lado de fora, só 80 e 443 existem.

---

## 14. Troubleshooting (erros comuns)

| Sintoma | Causa provável | Solução |
|---|---|---|
| `Connection timed out` no navegador | Porta fechada no firewall da Oracle | Seção 8 (Security List + ufw) |
| `Connection timed out` **só na 443** | Regra de 443 ausente, não salva, ou criada com origem errada (ex: `10.0.0.0/24` em vez de `0.0.0.0/0`) | Seção 13 — confirme a regra **TCP 443 / origem `0.0.0.0/0`**; use o teste `PROBE443` da seção 13, porque `timeout` no PC **não** prova porta fechada |
| `Permission denied (publickey)` | Chave/usuario errados | Usar `Downloads\ssh-key-2026-08-13.key` + `ubuntu@` |
| `Please login as the user "ubuntu"` | Usou `opc` | Usar `ubuntu@147.15.122.54` |
| `docker: command not found` | Docker não instalado | Seção 4 (e faça `exit` + reconectar) |
| `Cannot connect to the Docker daemon` | Usuário sem permissão | `sudo usermod -aG docker $USER` + reconectar |
| Site abre, mas YouTube dá `error.api.youtube.login` | YouTube bloqueando IP de datacenter | Já há **retry + fallback Cobalt** automáticos (seção 12); opcional: adicionar `cookies.txt` para melhorar a qualidade (1080p) |
| `error.api.ffmpeg.missing` | Imagem antiga sem ffmpeg | `docker compose build --no-cache` |
| `error.api.timeout` / Instagram não baixa | Container da Cobalt fora do ar | `docker compose ps` (o `cobalt` deve estar `Up`) + `docker logs --tail 50 cobalt` + teste: `curl -s https://saverclip.mobaily.com.br/cobalt/` (modo HTTPS) ou `curl -s http://127.0.0.1:8080/` (modo HTTP) |
| Erro `api.auth.api-key.missing` no site | O site não está enviando a chave da Cobalt, ou a chave é diferente da do container | `COBALT_API_KEY` no `.env` da VM precisa ser o **mesmo UUID** do `keys.json` — depois rode `docker compose restart saveclip` |
| Container `cobalt` reiniciando em loop | `keys.json` ausente, vazio ou com JSON inválido | Recrie o arquivo como na seção 11.2 (`docker logs cobalt` mostra o aviso da Cobalt) |
| Baixa, mas o arquivo não salva no PC | Link de `/tunnel` bloqueado no navegador | **Modo HTTPS:** o bloco `handle_path /cobalt/*` precisa estar no `Caddyfile` e a `API_URL` tem de terminar com `/` (`https://saverclip.mobaily.com.br/cobalt/`). **Modo HTTP:** porta **8080** liberada na Security List (seção 8) + `API_URL` em http com `/` no fim |
| A porta 8080 mostra um JSON da Cobalt em vez do site | Comportamento esperado no modo HTTP desde a seção 11 | O site é a **porta 80**; a 8080 é a API Cobalt. No modo HTTPS (seção 13) a 8080 fica fechada e a Cobalt é servida em `/cobalt/` |
| `{"code":404,"message":"Application not found"}` / `502 Application failed to respond` | Você ainda está usando a instância do Railway (trial expirado) | Migre para a Cobalt self-hosted da **seção 11** |
| Porta 80 já em uso | Outro serviço na porta 80 | `sudo ss -tulpn \| grep :80` |
| Site some após reiniciar a VM | Container sem `restart` | Usar o `docker compose up -d` (já tem `restart: unless-stopped`) |
| `ERR_SSL_PROTOCOL_ERROR` / site inacessível depois de ativar o HTTPS | Porta **443** fechada na Oracle (o Caddy escuta, mas o firewall bloqueia) | Passo 1 da **seção 13** (Security List: TCP 443, origem `0.0.0.0/0`) |
| O `caddy` reinicia em loop / "challenge failed" nos logs | O registro DNS **A** do domínio (ou do subdomínio, na variante comentada) ainda não aponta para `147.15.122.54` | `Resolve-DnsName saverclip.mobaily.com.br -Server 8.8.8.8` + `docker logs --tail 50 caddy` (espere o DNS propagar). Na variante de sub-caminho, nenhum DNS novo é necessário |
| Site em HTTPS, mas o download falha com *mixed content* no console do navegador | A Cobalt está com `API_URL` em `http://`, então o link de `/tunnel` sai em http | Suba com o override da **seção 13.2** (`-f docker-compose.https.yml`) — a `API_URL` precisa ser `https://saverclip.mobaily.com.br/`, pois a Cobalt usa só a **origem** dela |
| O download salva um arquivo **HTML** (página/0 KB) em vez do vídeo | O link de `/tunnel` caiu no site, e não na Cobalt | Confira no `Caddyfile` a rota `handle /tunnel*` → `cobalt:9000` (seção 13.5) e teste: `curl.exe -sI https://saverclip.mobaily.com.br/tunnel?url=x` deve responder **400** + `Access-Control-Allow-Origin` (e não `200` + `text/html`) |
| Site responde **502** depois de um `git pull` + `docker compose up -d --build` | O comando foi rodado **sem** o `-f docker-compose.https.yml`: o site tentou pegar a porta **80**, que agora é do Caddy (`port is already allocated`) | Suba de novo com os **dois `-f`** (seção 13.2). Confira com `docker compose ps` e `docker compose logs saveclip` |
| `http://147.15.122.54` parou de abrir | Esperado no modo HTTPS: o Caddy só responde pelos domínios do `Caddyfile` | Use o domínio; para testar pelo IP, volte ao modo HTTP (**seção 13.4**) |

**Ver os logs de qualquer problema:**
```bash
docker logs --tail 50 saveclip    # site (Flask / yt-dlp)
docker logs --tail 50 cobalt      # API Cobalt (Instagram/Facebook/TikTok)
```

---

## 15. Comandos e dicas úteis de manutenção

```bash
docker compose ps                  # estado dos containers
docker compose logs -f saveclip    # acompanhar os logs
docker compose restart             # reiniciar o app (ex: após mudar o .env)
docker compose down                # parar e remover os containers
docker compose up -d --build       # reconstruir + subir (atualização)
docker compose -f docker-compose.yml -f docker-compose.https.yml up -d   # subir COM HTTPS (seção 13)
docker logs --tail 30 caddy        # logs do Caddy (emissão/renovação do certificado)
docker system prune -f             # limpar imagens antigas (libera disco)
df -h                              # espaço em disco
```

**Cadastrar sua chave `id_ed25519` na VM (opcional, para não depender do arquivo do Downloads):**

```bash
mkdir -p ~/.ssh
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIA6WRzcnvwroML0veKjzDSS/Q5msxYsKhRmOfru/w9NL eduardo@DESKTOP-H1A32OU" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Depois, do Windows: `ssh -i C:\Users\Eduardo\.ssh\id_ed25519 ubuntu@147.15.122.54`

---

## 🎯 Resumo mental do deploy

```
git push (PC)  →  git pull (VM)  →  docker compose up -d --build
```

E se algo falhar:
```
docker compose ps  →  docker logs -f saveclip  →  firewall da Oracle (seção 8)
```

É isso! 🎉 Agora é com você: siga as seções em ordem e, quando tiver o site no ar, qualquer mudança de código vira apenas os 3 comandos do resumo.




