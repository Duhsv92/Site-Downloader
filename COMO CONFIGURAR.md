# 🚀 Guia: Como Configurar a API Cobalt para o SaveClip

Para que o SaveClip funcione de verdade (baixar vídeos do Instagram, Facebook e TikTok),
você precisa de uma **instância da API Cobalt** rodando. Aqui estão as opções:

---

## Opção 1: Deploy no Railway (Mais Fácil — Recomendado)

O **Railway** permite fazer deploy do Cobalt com **1 clique** e tem um plano gratuito.

### Passo a passo:

1. **Crie uma conta no Railway**
   - Acesse [railway.com](https://railway.com) e faça login com GitHub

2. **Use o template do Cobalt**
   - Acesse: [railway.com/new](https://railway.com/new)
   - Pesquise por **"Cobalt"** nos templates
   - Escolha **"Cobalt Tools Complete Setup"** (inclui API + Web UI)
   - Clique em **"Deploy"**

3. **Aguarde o deploy** (2-3 minutos)
   - O Railway vai provisionar automaticamente a API

4. **Gere um domínio público**
   - Clique no serviço da **API** no painel do Railway
   - Vá em **Settings → Networking → Generate Domain**
   - Você vai receber algo como: `cobalt-api-xxxxx.up.railway.app`

5. **Configure no SaveClip**
   - Abra o SaveClip no navegador
   - Clique no ⚙️ (engrenagem) na barra de navegação
   - Cole a URL da sua API: `https://cobalt-api-xxxxx.up.railway.app`
   - Clique em **Salvar**

6. **Pronto!** 🎉 Agora você pode baixar vídeos!

> **💰 Custo:** Railway oferece $5/mês de créditos grátis, suficiente para uso pessoal.

---

## Opção 2: Deploy com Docker (VPS ou Local)

Se você tem um servidor VPS ou quer rodar localmente:

### Pré-requisitos:
- Docker e Docker Compose instalados

### Passo a passo:

1. **Crie uma pasta para o projeto:**
   ```bash
   mkdir cobalt-api && cd cobalt-api
   ```

2. **Crie o arquivo `docker-compose.yml`:**
   ```yaml
   version: '3.8'

   services:
     cobalt-api:
       image: ghcr.io/imputnet/cobalt:latest
       container_name: cobalt-api
       restart: unless-stopped
       ports:
         - "9000:9000"
       environment:
         - API_URL=http://localhost:9000
       # Opcional: para cookies de autenticação de plataformas
       # volumes:
       #   - ./cookies.json:/cobalt/cookies.json
   ```

3. **Inicie o container:**
   ```bash
   docker compose up -d
   ```

4. **Teste se está funcionando:**
   ```bash
   curl http://localhost:9000/
   ```
   Deve retornar informações sobre a instância.

5. **Configure no SaveClip:**
   - Clique no ⚙️ e cole: `http://localhost:9000`

> **⚠️ Para acesso externo:** Use um reverse proxy (Nginx) com HTTPS.

---

## Opção 3: Deploy no Render (Alternativa Grátis)

1. Acesse [render.com](https://render.com) e crie uma conta
2. Clique em **"New" → "Web Service"**
3. Em "Image URL", use: `ghcr.io/imputnet/cobalt:latest`
4. Configure:
   - **Name:** cobalt-api
   - **Region:** escolha a mais próxima
   - **Plan:** Free
5. Adicione a variável de ambiente:
   - `API_URL` = a URL gerada pelo Render
6. Clique em **Deploy**
7. Use a URL gerada nas configurações do SaveClip

---

## Testando sua instância

Depois de configurar, teste com este comando (troque a URL):

```bash
curl -X POST "https://SUA-INSTANCIA.com/" \
     -H "Content-Type: application/json" \
     -H "Accept: application/json" \
     -d '{"url": "https://www.tiktok.com/@tiktok/video/7106594312292453675", "videoQuality": "1080"}'
```

A resposta deve conter `"status": "tunnel"` ou `"status": "redirect"` com uma URL de download.

---

## Dúvidas Frequentes

**P: Posso usar a API pública `api.cobalt.tools`?**
R: A API pública tem proteção anti-bot (Turnstile) e **não é feita para uso em projetos externos**.
Você precisa hospedar sua própria instância.

**P: É gratuito?**
R: O Cobalt é open source e grátis. O custo é apenas da hospedagem (Railway tem $5/mês grátis).

**P: Quais plataformas são suportadas?**
R: Instagram, Facebook, TikTok, YouTube, Twitter/X, Reddit, Pinterest, Tumblr, e muitas outras.

**P: Os vídeos ficam salvos no servidor?**
R: Não! O Cobalt apenas faz proxy do download. Nenhum vídeo é armazenado.

---

## Links Úteis

- 📦 [Repositório Cobalt (GitHub)](https://github.com/imputnet/cobalt)
- 🚂 [Railway Templates](https://railway.com/templates)
- 📖 [Documentação da API](https://github.com/imputnet/cobalt/blob/main/docs/api.md)
