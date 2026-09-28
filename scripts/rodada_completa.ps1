# Rodada completa do experimento: BM25 + denso + F6 (secoes e fusao) + avaliação.
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
#     .\scripts\rodada_completa.ps1 -PularF6                 # só F4/F5

param(
    [switch]$SomenteDenso,
    [switch]$SomenteBM25,
    [string]$Embedder = "",
    # Orçamento do encode denso. Com 5 h saem structural_gold, structural_pred e
    # recursive_default (~4,9 h); as duas fixas ficam para a noite seguinte e
    # reaproveitam o cache. Passe 0 para não limitar (rodada completa, ~10 h).
    [double]$MaxHoras = 5,
    # F6 (seleção de conteúdo + fusão). Roda por padrão: é o resultado
    # principal do trabalho e custa minutos, porque reaproveita o cache de
    # embeddings recortando as linhas em vez de reencodar.
    [switch]$PularF6,
    # Estratégia usada na tabela principal da F6 (a melhor sob recorte).
    [string]$Est = "fixed_512_256",
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
    $argsTempo = @()
    if ($MaxHoras -gt 0) { $argsTempo = @("--max-horas", $MaxHoras) }
    Etapa "denso (orcamento: $MaxHoras h)" {
        & $Python -u -m src.run_experiments --strategy all --retriever dense @argsEmbedder @argsTempo
    } | Out-Null
    Etapa "avaliacao do denso" {
        & $Python -u -m src.evaluate
    } | Out-Null
}

# 3. F6: selecao de conteudo + fusao -------------------------------------------
# Esta etapa e o resultado principal do trabalho (nDCG@10 de 0,2486 para 0,3215)
# e e barata: o recorte no denso reaproveita o cache de embeddings recortando as
# linhas por chunk_id, entao custa minutos em vez das ~10 h de um reencode.
if (-not $PularF6) {
    # Rótulos EXATOS. Com casamento por substring, "bm25" pegaria
    # "cv_fusao_bm25_denso" e "dense" pegaria "dense_peso_rel0.5" — a F6
    # encadearia a partir de rodadas derivadas e o erro só apareceria como um
    # número estranho na tabela final.
    $rotuloDenso = if ($Embedder) { "dense_$Embedder" } else { "dense_bge_m3" }
    $bm25Completo  = & $Python -m src.experiment --ultima "bm25"
    $densoCompleto = & $Python -m src.experiment --ultima $rotuloDenso
    if (-not $bm25Completo -or -not $densoCompleto) {
        Registrar "F6 pulada: faltam as rodadas de BM25 e/ou densa como base"
    } else {
        Registrar "F6 sobre: $bm25Completo  +  $densoCompleto"

        Etapa "F6 recorte por secao (BM25)" {
            & $Python -u -m src.run_experiments --strategy all --retriever bm25 `
                --secoes sem:relatorio --label bm25_sec_sem_relatorio
        } | Out-Null
        Etapa "F6 recorte por secao (denso, usa o cache)" {
            & $Python -u -m src.run_experiments --strategy all --retriever dense `
                --secoes sem:relatorio --label dense_sec_sem_relatorio
        } | Out-Null
        # O controle nao e opcional: sem ele o ganho do recorte tem duas
        # explicacoes (estrutura do acordao ou indice menor) e nao da para
        # afirmar nenhuma das duas.
        Etapa "F6 CONTROLE (indice do mesmo tamanho, sorteado)" {
            & $Python -u -m src.run_experiments --strategy all --retriever bm25 `
                --amostra-igual-a sem:relatorio --label bm25_controle_amostra
        } | Out-Null

        $bm25Sec  = & $Python -m src.experiment --ultima "bm25_sec_sem_relatorio"
        $densoSec = & $Python -m src.experiment --ultima "dense_sec_sem_relatorio"
        $controle = & $Python -m src.experiment --ultima "bm25_controle_amostra"

        Etapa "F6 fusao das 4 condicoes (peso igual, sem hiperparametro)" {
            & $Python -u -m src.fusion --metodo soma_norm --label fusao4_peso_igual `
                --experimentos $bm25Completo $bm25Sec $densoCompleto $densoSec
        } | Out-Null
        Etapa "F6 fusao com peso por validacao cruzada" {
            & $Python -u -m src.tuning --bm25 $bm25Sec --denso $densoSec `
                --label cv_fusao_sec_sem_relatorio
        } | Out-Null

        Etapa "F6 avaliacoes" {
            & $Python -u -m src.evaluate --experiment $bm25Sec  --incluir $bm25Completo
            & $Python -u -m src.evaluate --experiment $densoSec --incluir $densoCompleto
            & $Python -u -m src.evaluate --experiment $controle --incluir $bm25Completo $bm25Sec
        } | Out-Null

        # Tabela principal: um punhado de condicoes escolhidas. Jogar todos os
        # runs numa tabela so faria a correcao de Bonferroni enterrar efeitos
        # reais sob comparacoes que ninguem pretende fazer.
        $fusao4 = & $Python -m src.experiment --ultima "fusao4_peso_igual"
        $cvSec  = & $Python -m src.experiment --ultima "cv_fusao_sec_sem_relatorio"
        $e = "$Est"
        Etapa "F6 tabela principal + figuras" {
            & $Python -u -m src.evaluate --label f6_tabela_principal --runs `
                "$bm25Completo\runs\$e`__bm25.trec" `
                "$densoCompleto\runs\$e`__dense-bge_m3.trec" `
                "$bm25Sec\runs\$e`__bm25__sec-sem_relatorio.trec" `
                "$densoSec\runs\$e`__dense-bge_m3__sec-sem_relatorio.trec" `
                "$cvSec\runs\$e`__cv-soma_norm.trec" `
                "$fusao4\runs\$e`__soma_norm.trec"
            $tabela = & $Python -m src.experiment --ultima "f6_tabela_principal"
            & $Python -u -m src.plots --experiment $tabela --referencia "$e`__bm25"
        } | Out-Null
    }
}

Registrar "rodada concluida"
Registrar "resultados em results\experiments\ (ver INDICE.md)"
Write-Output ""
Write-Output "Resumo das rodadas:"
Get-Content (Join-Path $raiz "results\experiments\INDICE.md") -ErrorAction SilentlyContinue | Select-Object -Last 8
