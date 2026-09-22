# ════════════════════════════════════════════════════════════════════
#  🌶️ Papo Pepper — instalador (Windows/PowerShell) · idempotente
#
#    powershell -ExecutionPolicy ByPass -File .\install.ps1
#    .\install.ps1 -Completo -Mcp
#    .\install.ps1 -Alvo claude
#    .\install.ps1 -SomenteAgentes
# ════════════════════════════════════════════════════════════════════
param([switch]$Completo, [switch]$Mcp, [switch]$SomenteAgentes, [string]$Alvo)
$ErrorActionPreference = "Stop"
Write-Host "🌶️ Papo Pepper — instalando…"

$usePy = $false
if (Get-Command py -ErrorAction SilentlyContinue) { $usePy = $true }
elseif (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.10+ não encontrado (instale em python.org e marque Add to PATH)"
}
function Run-Py($args_) { if ($usePy) { & py -3 @args_ } else { & python @args_ } }
Run-Py @("-c", "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)") `
    or throw "Python 3.10+ necessário"

$raiz = (Get-Location).Path
if (-not (Test-Path (Join-Path $raiz "pyproject.toml"))) {
    $dest = Join-Path $env:LOCALAPPDATA "papo-pepper-src"
    if (Test-Path (Join-Path $dest "papo-pepper")) {
        $raiz = Join-Path $dest "papo-pepper"
    } else {
        git clone --depth 1 https://github.com/geniallabsai/papo-pepper.git (Join-Path $dest "papo-pepper")
        $raiz = Join-Path $dest "papo-pepper"
    }
}
Write-Host "  repositório: $raiz"

if (-not $SomenteAgentes) {
    $spec = if ($Completo) { "$raiz[pdf,audio,math]" } else { $raiz }
    Run-Py @("-m", "pip", "install", "--quiet", "-e", $spec)
    Write-Host "  pacote: instalado (modo editável)"
}

Set-Location $raiz
$cliArgs = @()
if ($Alvo)  { $cliArgs += @("--alvo", $Alvo) }
if ($Mcp)   { $cliArgs += @("--mcp") }
if (Get-Command papo-pepper -ErrorAction SilentlyContinue) {
    & papo-pepper setup @cliArgs
} else {
    Run-Py @("-m", "papo_pepper", "setup", @cliArgs)
}

Write-Host ""
Write-Host "✔ pronto. Próximos passos:"
Write-Host "  • papo-pepper models            # provedor/modelos recomendados"
Write-Host "  • papo-pepper novo `"seu assunto`" --entrevista"
