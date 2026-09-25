# ============================================================
# SaveClip — trocar-api.ps1
# Troca a URL da API Cobalt (Railway) em TODOS os pontos do projeto.
#
# USO (PowerShell, na raiz do projeto):
#   .\trocar-api.ps1 -Url https://sua-api-nova.up.railway.app
#   .\trocar-api.ps1 -Url https://saverclip.mobaily.com.br/cobalt   # Cobalt self-hosted no HTTPS (seção 13)
#   .\trocar-api.ps1 -Url https://sua-api-nova.up.railway.app -ApiKey <uuid> -AuthScheme Api-Key
#   .\trocar-api.ps1 -Url https://sua-api-nova.up.railway.app -DryRun   # apenas simula
#   .\trocar-api.ps1 -Url https://sua-api-nova.up.railway.app -Check    # troca e testa a instância
#
# Se o PowerShell bloquear o script:
#   powershell -ExecutionPolicy Bypass -File .\trocar-api.ps1 -Url ...
#
# O que é alterado:
#   .env                        -> COBALT_API_URL (+ COBALT_API_KEY / COBALT_AUTH_SCHEME, se informados)
#   server.py / api/download.py -> DEFAULT_COBALT_URL (usado quando não existe .env)
#   COMO CONFIGURAR.md / DEPLOY VPS ORACLE.md -> links de exemplo e documentação
#   O .env NÃO vai para o GitHub: em produção (VM Oracle) rode o sed indicado no fim do script.
#   O .env.example é mantido com placeholder de propósito (é o template público).
# ============================================================

[CmdletBinding()]
param(
    # Nova URL da instância Cobalt (ex: https://cobalt-production-e133.up.railway.app)
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Url,

    # Opcional: chave de API da instância (grava COBALT_API_KEY no .env)
    [string]$ApiKey,

    # Opcional: esquema do header Authorization ("Api-Key" é o padrão da Cobalt)
    [ValidateSet('Api-Key', 'Bearer')]
    [string]$AuthScheme,

    # Simula a troca sem gravar nada
    [switch]$DryRun,

    # Testa a instância (GET /) depois de trocar
    [switch]$Check
)

$ErrorActionPreference = 'Stop'

# ------------------------------------------------------------
# 1. Normaliza e valida a URL
# ------------------------------------------------------------
$newUrl = $Url.Trim().TrimEnd('/')
if ($newUrl -notmatch '^https?://') { $newUrl = "https://$newUrl" }
if ($newUrl -notmatch '^https?://[a-zA-Z0-9\.\-]+(:\d+)?(/[a-zA-Z0-9\.\-_/]*)?$') {
    throw "URL inválida: '$Url'. Informe algo como https://sua-api.up.railway.app ou https://saverclip.mobaily.com.br/cobalt"
}

# Em regex, "$" é especial no texto de substituição -> escapamos por segurança
$safeUrl = $newUrl.Replace('$', '$$')

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$targets = @('.env', 'server.py', 'api\download.py', 'COMO CONFIGURAR.md', 'DEPLOY VPS ORACLE.md')

# Instância self-hosted (Cobalt rodando na própria VM da Oracle) — trocada junto
$selfHostedPattern = 'https?://saverclip\.mobaily\.com\.br/cobalt/?|https?://saverclip\.mobaily\.com\.br:\d+|https?://cobalt\.saverclip\.mobaily\.com\.br'   # sub-caminho HTTPS (padrão, seção 13), porta 8080 (http) ou subdomínio (variante) — nunca a URL do site
# Qualquer domínio Railway já registrado no projeto (instância antiga ou atual)
$railwayPattern = 'https?://[a-zA-Z0-9\-\.]+\.up\.railway\.app'
# Valor padrão no código-fonte
$defaultPattern = 'DEFAULT_COBALT_URL = "https?://[^"]+"'

function Get-NewLineStyle([string]$text) {
    if ($text.Contains("`r`n")) { return "`r`n" }
    return "`n"
}

# Define (ou cria) a variável KEY=valor no conteúdo de um .env.
# Regras: atualiza a linha ATIVA se existir; senão reaproveita a comentada;
# senão acrescenta no fim. Nunca duplica a variável.
function Set-EnvVar([string]$content, [string]$key, [string]$value, [string]$nl) {
    $lines   = $content -split "\r?\n"
    $pattern = "^\s*#?\s*$([regex]::Escape($key))="
    $idx     = -1

    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $pattern) {
            $isActive = ($lines[$i] -notmatch '^\s*#')
            if ($isActive) { $idx = $i; break }      # linha ativa tem prioridade
            if ($idx -lt 0) { $idx = $i }            # lembra a comentada como alternativa
        }
    }

    if ($idx -ge 0) { $lines[$idx] = "$key=$value" }
    else            { $lines += "$key=$value" }

    return ($lines -join $nl)
}

Write-Host ""
Write-Host "Trocando a API Cobalt para: $newUrl" -ForegroundColor Cyan
if ($DryRun) { Write-Host "Modo DRY-RUN: nenhum arquivo será gravado." -ForegroundColor Yellow }
Write-Host ""

$total = 0
foreach ($rel in $targets) {
    $path = Join-Path $root $rel

    if (-not (Test-Path -LiteralPath $path)) {
        Write-Host ("  {0,-26} ignorado (arquivo não encontrado)" -f $rel) -ForegroundColor DarkGray
        continue
    }

    $original = [IO.File]::ReadAllText($path)
    $content  = $original
    $nl       = Get-NewLineStyle $original
    $hits     = 0

    # --- URL da API (self-hosted na VM e/ou qualquer domínio .up.railway.app) ---
    $before  = $content
    $content = [regex]::Replace($content, $selfHostedPattern, $safeUrl, 'IgnoreCase')
    $content = [regex]::Replace($content, $railwayPattern, $safeUrl, 'IgnoreCase')
    if ($content -ne $before) { $hits++ }

    # --- Valor padrão no código (lido quando o .env não existe) ---
    $before  = $content
    $content = [regex]::Replace($content, $defaultPattern, "DEFAULT_COBALT_URL = `"$newUrl`"")
    if ($content -ne $before) { $hits++ }

    # --- .env: garante COBALT_API_URL (+ chave e esquema, se informados) ---
    if ($rel -eq '.env') {
        $before  = $content
        $content = Set-EnvVar $content 'COBALT_API_URL' $newUrl $nl
        if ($content -ne $before) { $hits++ }

        if ($ApiKey) {
            $before  = $content
            $content = Set-EnvVar $content 'COBALT_API_KEY' $ApiKey $nl
            if ($content -ne $before) { $hits++ }
        }

        if ($AuthScheme) {
            $before  = $content
            $content = Set-EnvVar $content 'COBALT_AUTH_SCHEME' $AuthScheme $nl
            if ($content -ne $before) { $hits++ }
        }
    }

    if ($content -eq $original) {
        Write-Host ("  {0,-26} já estava atualizado" -f $rel) -ForegroundColor DarkGray
        continue
    }

    if (-not $DryRun) {
        [IO.File]::WriteAllText($path, $content)
    }

    $total += $hits
    Write-Host ("  {0,-26} {1} atualização(ões)" -f $rel, $hits) -ForegroundColor Green
}

Write-Host ""
Write-Host "Total de atualizações: $total" -ForegroundColor Cyan

# ------------------------------------------------------------
# 2. Testa a instância (GET / devolve a versão e os serviços)
# ------------------------------------------------------------
if ($Check -and -not $DryRun) {
    Write-Host ""
    Write-Host "Testando $newUrl/ ..." -ForegroundColor Cyan
    try {
        $info = Invoke-RestMethod -Uri "$newUrl/" -TimeoutSec 25
        Write-Host ("  OK — cobalt {0} | serviços: {1}" -f $info.cobalt.version, ($info.cobalt.services -join ', ')) -ForegroundColor Green
    } catch {
        Write-Host "  FALHOU: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  Railway: porta pública 9000 + Deploy/Run logs. Self-hosted (VM): container 'cobalt' Up e /cobalt/ respondendo pelo Caddy." -ForegroundColor Yellow
    }
}

# ------------------------------------------------------------
# 3. Lembretes (o .env da VM não é alterado por este script)
# ------------------------------------------------------------
Write-Host ""
Write-Host "Próximos passos:" -ForegroundColor Yellow
Write-Host "  1) Local: rode 'python server.py' e teste um download."
Write-Host "  2) Vercel: Settings -> Environment Variables -> COBALT_API_URL."
Write-Host "  3) VM Oracle (produção):"
Write-Host "       ssh -i <sua-chave>.key ubuntu@147.15.122.54"
Write-Host "       sed -i `"s|^COBALT_API_URL=.*|COBALT_API_URL=$newUrl|`" ~/Site-Downloader/.env"
Write-Host "       cd ~/Site-Downloader && docker compose restart"
Write-Host ""
