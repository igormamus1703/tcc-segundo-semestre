# Rodada completa do experimento: BM25 + denso + avaliação.
#
# Feito para rodar a noite inteira sem supervisão. Três garantias:
#   1. O BM25 (~25 min) roda PRIMEIRO, então há resultado utilizável já na
#      primeira meia hora, mesmo que o denso falhe depois.
#   2. O encode denso grava blocos em disco conforme avança; se cair, basta
#      rodar de novo — ele retoma de onde parou, sem reencodar.
#   3. Cada etapa segue mesmo que a anterior falhe, e o erro fica no log.
#
# Uso (a partir da raiz do repositório):
#     .\scripts\rodada_completa.ps1
#     .\scripts\rodada_completa.ps1 -SomenteDenso
#     .\scripts\rodada_completa.ps1 -Embedder pt_compact    # exige `hf auth login`

param(
    [switch]$SomenteDenso,
    [switch]$SomenteBM25,
    [string]$Embedder = "",
    [string]$Python = "C:\venvs\tcc-juris\Scripts\python.exe"
)

$ErrorActionPreference = "Continue"
$raiz = Split-Path -Parent $PSScriptRoot
$proj = Join-Path $raiz "juris-chunking"
$carimbo = Get-Date -Format "yyyyMMdd-HHmm"
$logDir = Join-Path $raiz "results\logs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir "rodada_$carimbo.log"

function Registrar($msg) {
    $linha = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $msg
    Write-Output $linha
    Add-Content -Path $log -Value $linha -Encoding utf8
}

function Etapa($nome, [scriptblock]$acao) {
    Registrar "=== INICIO: $nome ==="
    $t0 = Get-Date
    try {
        & $acao 2>&1 | ForEach-Object {
            Write-Output $_
            Add-Content -Path $log -Value $_ -Encoding utf8
        }
        $dur = ((Get-Date) - $t0).TotalMinutes
        Registrar ("=== FIM: {0} em {1:N1} min ===" -f $nome, $dur)
        return $true
    } catch {
        Registrar "=== FALHOU: $nome -> $_ ==="
        return $false
    }
}

Registrar "rodada $carimbo"
Registrar "log em $log"
Set-Location $proj

# Verificações antes de comprometer a noite -----------------------------------
Registrar "--- verificacoes previas ---"
& $Python -c @"
import sys, torch, shutil
ok = True
if not torch.cuda.is_available():
    print('ERRO: CUDA indisponivel - o encode denso levaria ~127 h em CPU'); ok = False
else:
    print(f'GPU: {torch.cuda.get_device_name(0)}')
livre = shutil.disk_usage('C:/').free / 1024**3
print(f'disco livre: {livre:.1f} GB')
if livre < 15:
    print('ERRO: menos de 15 GB livres; o cache de embeddings precisa de ~8,4 GB'); ok = False
sys.exit(0 if ok else 1)
"@
if ($LASTEXITCODE -ne 0) {
    Registrar "verificacoes previas FALHARAM - abortando antes de perder a noite"
    exit 1
}

$argsEmbedder = @()
if ($Embedder) { $argsEmbedder = @("--embedder", $Embedder) }

# 1. BM25: barato e garante resultado ------------------------------------------
if (-not $SomenteDenso) {
    Etapa "BM25 (5 estrategias)" {
        & $Python -u -m src.run_experiments --strategy all --retriever bm25
    } | Out-Null
    Etapa "avaliacao do BM25" {
        & $Python -u -m src.evaluate
    } | Out-Null
}

# 2. Denso: a parte longa -------------------------------------------------------
if (-not $SomenteBM25) {
    Etapa "denso (5 estrategias, ~10 h)" {
        & $Python -u -m src.run_experiments --strategy all --retriever dense @argsEmbedder
    } | Out-Null
    Etapa "avaliacao do denso" {
        & $Python -u -m src.evaluate
    } | Out-Null
}

Registrar "rodada concluida"
Registrar "resultados em results\experiments\ (ver INDICE.md)"
Write-Output ""
Write-Output "Resumo das rodadas:"
Get-Content (Join-Path $raiz "results\experiments\INDICE.md") -ErrorAction SilentlyContinue | Select-Object -Last 8
