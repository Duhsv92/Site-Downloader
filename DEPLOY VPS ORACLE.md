# 🚀 Passo a Passo: Deploy do SaveClip na sua VM da Oracle

> **Objetivo:** publicar o **SaveClip** (Site Downloader) na sua VM da Oracle Cloud, de forma que o site fique acessível pela internet em `http://147.15.122.54`, com tudo funcionando: **YouTube (MP4/MP3 via yt-dlp + ffmpeg, com fallback automático para a API Cobalt)** e **Instagram / Facebook / TikTok (via API Cobalt)**.

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
7. YouTube bloqueado pela VM: cookies e fallback Cobalt
8. (Bônus) HTTPS grátis com Caddy

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
COBALT_API_URL=https://api-production-664d8.up.railway.app
PORT=8080
```

- `COBALT_API_URL` → sua instância Cobalt (processa Instagram, Facebook e TikTok). O YouTube não depende dela (usa o yt-dlp local), mas ela é usada como **fallback** quando o YouTube bloqueia a VM.
- `PORT=8080` → porta **dentro do container**. Não mude se usar o `docker-compose.yml` da seção 7 (o mapeamento de portas depende dela).

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
  -e COBALT_API_URL=https://api-production-664d8.up.railway.app \
  saveclip
```

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

O Docker Compose transforma aquele comando gigante em um arquivo simples e **repetível**. Já deixei o `docker-compose.yml` pronto na raiz do projeto:

```yaml
services:
  saveclip:
    build: .                  # constrói a partir do Dockerfile local
    image: saveclip:latest    # nome da imagem gerada
    container_name: saveclip
    restart: unless-stopped   # sobe sozinho se a VM reiniciar
    ports:
      - "80:8080"             # VM:80  -> container:8080 (site principal)
      - "8080:8080"           # extra, para teste direto na porta 8080
    env_file:
      - .env                  # lê as variáveis do arquivo .env
    environment:
      - YTDLP_COOKIES=/app/cookies.txt   # cookies do YouTube (opcional, seção 11)
    volumes:
      - ./cookies.txt:/app/cookies.txt:ro   # monta o cookies.txt da VM
```

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
   - (opcional) **Destination Port Range:** adicione outra regra para `8080`, se quiser testar direto nessa porta
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
- ou **http://147.15.122.54:8080** (mapeamento extra de teste)

Testes rápidos:
- Cole um link do **YouTube** → deve baixar MP4 1080p e MP3 320kbps (usa o yt-dlp + ffmpeg que estão dentro da imagem).
- Cole um link de **Instagram / Facebook / TikTok** → deve processar via API Cobalt.

Se aparecer erro, veja a seção **12 (Troubleshooting)** — cada mensagem de erro já tem a causa provável e a solução.

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

## 11. (Importante) YouTube bloqueado pela VM — cookies e fallback Cobalt

**Sintoma:** alguns vídeos do YouTube (principalmente música) falham com **"Erro na API (HTTP 400)"**. Nos logs do container aparece:

```
ERROR: [youtube] <ID>: Sign in to confirm you're not a bot.
Use --cookies-from-browser or --cookies for the authentication.
```

**Causa:** o YouTube bloqueia seletivamente vídeos para **IPs de datacenter** (como o da Oracle). Não existe player client que contorne isso sozinho — é bloqueio por reputação de IP.

**O que o projeto já faz (automático, sem ação sua):**

1. Tenta vários **player clients** (`tv`, `android`, `ios`, `web_safari`).
2. Se bloquear, faz **retry automático** rotacionando os clients (até 4 tentativas, com espera progressiva).
3. Se ainda falhar, **fallback automático para a API Cobalt** (`server.py` → `_cobalt_request`) — o IP do Railway normalmente passa nesse bloqueio e o download continua (qualidade 720p).

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

## 12. (Bônus) HTTPS grátis com Caddy

Com o site em `http://IP`, dá para ter **HTTPS grátis** com o **Caddy** — ele emite e renova o certificado automaticamente. Pré-requisito: um domínio apontando para `147.15.122.54` (registro `A` no seu provedor de domínio).

**Na VM**, crie o arquivo `Caddyfile`:

```bash
nano Caddyfile
```

```text
seu-dominio.com {
    reverse_proxy 127.0.0.1:8080
}
```

**Rode o Caddy como container:**

```bash
docker run -d --name caddy -p 80:80 -p 443:443 \
  -v $PWD/Caddyfile:/etc/caddy/Caddyfile \
  -v caddy_data:/data -v caddy_config:/config \
  caddy:2
```

Em ~1 minuto seu site estará em **https://seu-dominio.com** ✅

> 📚 **Aprenda:** o Caddy é um servidor web que "esconde" o Flask atrás de um proxy reverso, adicionando HTTPS de graça. Aqui já entra em cena a diferença entre *porta 80* (pública) e *porta 8080* (interna): o Caddy escuta na 80/443 e repassa para o container na 8080.

---

## 13. Troubleshooting (erros comuns)

| Sintoma | Causa provável | Solução |
|---|---|---|
| `Connection timed out` no navegador | Porta fechada no firewall da Oracle | Seção 8 (Security List + ufw) |
| `Permission denied (publickey)` | Chave/usuario errados | Usar `Downloads\ssh-key-2026-08-13.key` + `ubuntu@` |
| `Please login as the user "ubuntu"` | Usou `opc` | Usar `ubuntu@147.15.122.54` |
| `docker: command not found` | Docker não instalado | Seção 4 (e faça `exit` + reconectar) |
| `Cannot connect to the Docker daemon` | Usuário sem permissão | `sudo usermod -aG docker $USER` + reconectar |
| Site abre, mas YouTube dá `error.api.youtube.login` | YouTube bloqueando IP de datacenter | Já há **retry + fallback Cobalt** automáticos (seção 11); opcional: adicionar `cookies.txt` para melhorar a qualidade (1080p) |
| `error.api.ffmpeg.missing` | Imagem antiga sem ffmpeg | `docker compose build --no-cache` |
| `error.api.timeout` / Instagram não baixa | Instância Cobalt fora do ar | Teste com `curl -s https://api-production-664d8.up.railway.app` na VM |
| Porta 80 já em uso | Outro serviço na porta 80 | `sudo ss -tulpn \| grep :80` |
| Site some após reiniciar a VM | Container sem `restart` | Usar o `docker compose up -d` (já tem `restart: unless-stopped`) |

**Ver os logs de qualquer problema:**
```bash
docker logs --tail 50 saveclip
```

---

## 14. Comandos e dicas úteis de manutenção

```bash
docker compose ps                  # estado dos containers
docker compose logs -f saveclip    # acompanhar os logs
docker compose restart             # reiniciar o app (ex: após mudar o .env)
docker compose down                # parar e remover os containers
docker compose up -d --build       # reconstruir + subir (atualização)
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




