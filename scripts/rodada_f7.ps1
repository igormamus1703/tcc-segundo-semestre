# Rodada da F7: validacao externa no JUA-Juris, reranker e replicacao.
#
# Pre-requisito: as rodadas da F4-F6 (BM25, denso, recorte, controle, fusao das
# 4) ja existem para o JurisTCU, e o cache de embeddings esta em disco.
# Tudo aqui reaproveita indices e embeddings: nada e reencodado.
#
# Mesmas garantias do rodada_completa.ps1: cada etapa segue mesmo que a
# anterior falhe, e o erro fica no log. Uma etapa cuja rodada ja existe e
# PULADA (o rotulo e procurado com casamento exato), entao o script pode ser
# rodado de novo depois de uma queda sem refazer o que ja saiu.
#
# Tempo (RTX 5060, 16 threads): ~40 min de BM25 no JUA, ~5 min de denso,
# ~45 min de reranker no JUA, minutos para o resto.
#
# Uso (a partir da raiz do repositorio):
#     .\scripts\rodada_f7.ps1

param(
    [string]$Est = "fixed_512_256",
    [string]$Python = "C:\venvs\tcc-juris\Scripts\python.exe"
)

$ErrorActionPreference = "Continue"
$raiz = Split-Path -Parent $PSScriptRoot
$proj = Join-Path $raiz "juris-chunking"
$carimbo = Get-Date -Format "yyyyMMdd-HHmm"
$logDir = Join-Path $raiz "results\logs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir "rodada_f7_$carimbo.log"

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
        Registrar ("=== FIM: {0} em {1:N1} min ===" -f $nome, ((Get-Date) - $t0).TotalMinutes)
    } catch {
        Registrar "=== FALHOU: $nome -> $_ ==="
    }
}

# Rodada mais recente com o rotulo EXATO (src.experiment.ultima_rodada), ou "".
function Rodada($rotulo) {
    $r = & $Python -c "from src.experiment import ultima_rodada; r = ultima_rodada('$rotulo'); print(r or '')"
    return "$r".Trim()
}

function SeFaltar($rotulo, [scriptblock]$acao) {
    $r = Rodada $rotulo
    if ($r) { Registrar "pulando $rotulo (ja existe: $(Split-Path -Leaf $r))" }
    else { Etapa $rotulo $acao }
}

Registrar "rodada F7 $carimbo"
Set-Location $proj

$Q = "data\interim\jua\queries_test.jsonl"
$QR = "data\interim\jua\qrels_test.trec"
if (-not (Test-Path $Q)) { Etapa "JUA-Juris -> acordaos (src.jua)" { & $Python -m src.jua } }

# 1. JUA-Juris: as rodadas base, sobre os mesmos indices ---------------------
SeFaltar "jua_bm25" { & $Python -m src.run_experiments --strategy all --retriever bm25 --queries $Q --label jua_bm25 }
SeFaltar "jua_bm25_sec_sem_relatorio" { & $Python -m src.run_experiments --strategy all --retriever bm25 --queries $Q --secoes sem:relatorio --label jua_bm25_sec_sem_relatorio }
SeFaltar "jua_bm25_controle_amostra" { & $Python -m src.run_experiments --strategy all --retriever bm25 --queries $Q --amostra-igual-a sem:relatorio --label jua_bm25_controle_amostra }
SeFaltar "jua_dense_bge_m3" { & $Python -m src.run_experiments --strategy all --retriever dense --queries $Q --label jua_dense_bge_m3 }
SeFaltar "jua_dense_sec_sem_relatorio" { & $Python -m src.run_experiments --strategy all --retriever dense --queries $Q --secoes sem:relatorio --label jua_dense_sec_sem_relatorio }

# 2. Fusoes (segundos) ---------------------------------------------------------
$jb = Rodada "jua_bm25"; $jbc = Rodada "jua_bm25_sec_sem_relatorio"
$jd = Rodada "jua_dense_bge_m3"; $jdc = Rodada "jua_dense_sec_sem_relatorio"
$tb = Rodada "bm25"; $tbc = Rodada "bm25_sec_sem_relatorio"
$td = Rodada "dense_bge_m3"; $tdc = Rodada "dense_sec_sem_relatorio"
SeFaltar "jua_fusao4_peso_igual" { & $Python -m src.fusion --metodo soma_norm --label jua_fusao4_peso_igual --experimentos $jb $jbc $jd $jdc }
SeFaltar "jua_fusao2_recortados" { & $Python -m src.fusion --metodo soma_norm --label jua_fusao2_recortados --experimentos $jbc $jdc }
SeFaltar "juristcu_fusao2_recortados" { & $Python -m src.fusion --metodo soma_norm --label juristcu_fusao2_recortados --experimentos $tbc $tdc }

# 3. Reranker (GPU). O cache de scores e por colecao e e compartilhado -------
function Fontes($b, $bc, $d, $dc) {
    return @(
        "$b\runs\${Est}__bm25__chunks.jsonl",
        "$bc\runs\${Est}__bm25__sec-sem_relatorio__chunks.jsonl",
        "$d\runs\${Est}__dense-bge_m3__chunks.jsonl",
        "$dc\runs\${Est}__dense-bge_m3__sec-sem_relatorio__chunks.jsonl"
    )
}
$tf4 = Rodada "fusao4_peso_igual"; $jf4 = Rodada "jua_fusao4_peso_igual"

SeFaltar "juristcu_rerank_fusao4" {
    & $Python -m src.rerank --estrategia $Est --nome fusao4 --label juristcu_rerank_fusao4 `
        --candidatos "$tf4\runs\${Est}__soma_norm.trec" --fontes (Fontes $tb $tbc $td $tdc) `
        --cache "data\interim\rerank_cache\juristcu_$Est.tsv"
}
SeFaltar "juristcu_rerank_bm25" {
    & $Python -m src.rerank --estrategia $Est --nome bm25 --label juristcu_rerank_bm25 `
        --candidatos "$tb\runs\${Est}__bm25.trec" --fontes "$tb\runs\${Est}__bm25__chunks.jsonl" `
        --cache "data\interim\rerank_cache\juristcu_$Est.tsv"
}
SeFaltar "jua_rerank_fusao4" {
    & $Python -m src.rerank --estrategia $Est --nome fusao4 --label jua_rerank_fusao4 --queries $Q `
        --candidatos "$jf4\runs\${Est}__soma_norm.trec" --fontes (Fontes $jb $jbc $jd $jdc) `
        --cache "data\interim\rerank_cache\jua_$Est.tsv"
}
SeFaltar "jua_rerank_bm25" {
    & $Python -m src.rerank --estrategia $Est --nome bm25 --label jua_rerank_bm25 --queries $Q `
        --candidatos "$jb\runs\${Est}__bm25.trec" --fontes "$jb\runs\${Est}__bm25__chunks.jsonl" `
        --cache "data\interim\rerank_cache\jua_$Est.tsv"
}

# 4. Avaliacao das rodadas do JUA (tabelas e figuras no padrao da F5/F6) ------
Etapa "avaliacao JUA (5 estrategias x condicoes)" {
    & $Python -m src.evaluate --experiment $jb --qrels $QR --queries $Q --incluir $jbc (Rodada "jua_bm25_controle_amostra") $jd $jdc
    & $Python -m src.plots --experiment $jb
}

# 5. Replicacao: as hipoteses do pre-registro, nas duas colecoes --------------
Etapa "replicacao (H1-H7)" { & $Python -m src.replicacao --spec configs\f7_replicacao.json --label f7_replicacao }

Registrar "fim da rodada F7 -> log em $log"
