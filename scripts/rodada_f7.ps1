# Rodada completa da F7: validacao externa (JUA-Juris), criterio 'toca',
# ranker aprendido, reranker zero-shot e ajustado, replicacao e painel.
#
# Pre-requisito: as rodadas da F4-F6 (BM25, denso, recorte, controle, fusao das
# 4 e auditoria) existem para o JurisTCU, e o cache de embeddings esta em disco.
# Nada aqui reencoda o corpus.
#
# Mesmas garantias do rodada_completa.ps1: cada etapa segue mesmo que a
# anterior falhe, e o erro fica no log. Uma etapa cuja rodada ja existe e
# PULADA (rotulo com casamento exato), entao o script pode ser rodado de novo
# depois de uma queda sem refazer o que ja saiu.
#
# Tempo aproximado (RTX 5060, 16 threads): ~2 h de buscas, ~1 h de fine-tune,
# ~40 min de reranker, ~30 min de analise. Medido em 05/10/2026.
#
# ATENCAO: nao dispare este script com outra fila escrevendo no mesmo rotulo.
# Uma rodada pela metade ja tem runs gravados e seria tomada como pronta.
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

function Busca($rotulo, $consultas, [string[]]$extra) {
    SeFaltar $rotulo { & $Python -m src.run_experiments --queries $consultas --label $rotulo @extra }
}

Registrar "rodada F7 $carimbo"
Set-Location $proj

$JT = "data\interim\queries.jsonl"
$TE = "data\interim\jua\queries_test.jsonl"
$TR = "data\interim\jua\queries_train_amostra.jsonl"
$SemRel = @("--secoes", "sem:relatorio")
$Toca = @("--secoes", "sem:relatorio", "--secoes-criterio", "toca")

# 0. Colecao -----------------------------------------------------------------
if (-not (Test-Path $TE)) { Etapa "JUA-Juris -> acordaos (src.jua)" { & $Python -m src.jua } }
if (-not (Test-Path $TR)) { Etapa "amostra de treino" { & $Python -c "from src.jua import amostra_treino; print(amostra_treino())" } }

# 1. JUA dificil (teste): as condicoes da F6 e as novas -----------------------
Busca "jua_bm25" $TE @("--strategy", "all", "--retriever", "bm25")
Busca "jua_bm25_sec_sem_relatorio" $TE (@("--strategy", "all", "--retriever", "bm25") + $SemRel)
Busca "jua_bm25_sec_sem_relatorio_toca" $TE (@("--strategy", "all", "--retriever", "bm25") + $Toca)
Busca "jua_bm25_controle_amostra" $TE @("--strategy", "all", "--retriever", "bm25", "--amostra-igual-a", "sem:relatorio")
Busca "jua_bm25_sec_sem_ementa" $TE @("--strategy", "structural_gold", "structural_pred", "--retriever", "bm25", "--secoes", "sem:ementa")
Busca "jua_dense_bge_m3" $TE @("--strategy", "all", "--retriever", "dense")
Busca "jua_dense_sec_sem_relatorio" $TE (@("--strategy", "all", "--retriever", "dense") + $SemRel)
Busca "jua_dense_sec_sem_relatorio_toca" $TE (@("--strategy", "all", "--retriever", "dense") + $Toca)

# 2. JurisTCU: so o que a F7 acrescenta --------------------------------------
Busca "bm25_sec_sem_relatorio_toca" $JT (@("--strategy", "all", "--retriever", "bm25") + $Toca)
Busca "dense_sec_sem_relatorio_toca" $JT (@("--strategy", "all", "--retriever", "dense") + $Toca)

# 3. JUA natural (amostra de 6.000 do treino) --------------------------------
#    h8_* sao as rodadas da confirmacao pre-registrada (adendo 2), mantidas
#    com o proprio rotulo para a proveniencia ficar clara.
Busca "h8_tr_bm25" $TR @("--strategy", $Est, "--retriever", "bm25", "--top-docs", "200")
Busca "h8_tr_bm25_maioria" $TR (@("--strategy", $Est, "--retriever", "bm25", "--top-docs", "200") + $SemRel)
Busca "h8_tr_bm25_toca" $TR (@("--strategy", $Est, "--retriever", "bm25", "--top-docs", "200") + $Toca)
Busca "juanat_bm25" $TR @("--strategy", "all", "--retriever", "bm25", "--top-docs", "200")
Busca "juanat_bm25_sec_sem_relatorio" $TR (@("--strategy", "all", "--retriever", "bm25", "--top-docs", "200") + $SemRel)
Busca "juanat_bm25_sec_sem_relatorio_toca" $TR (@("--strategy", "all", "--retriever", "bm25", "--top-docs", "200") + $Toca)
Busca "juanat_bm25_sec_sem_ementa" $TR @("--strategy", "structural_gold", "structural_pred", "--retriever", "bm25", "--top-docs", "200", "--secoes", "sem:ementa")
Busca "juanat_dense_bge_m3" $TR @("--strategy", "all", "--retriever", "dense", "--top-docs", "200")
Busca "juanat_dense_sec_sem_relatorio" $TR (@("--strategy", "all", "--retriever", "dense", "--top-docs", "200") + $SemRel)
Busca "juanat_dense_sec_sem_relatorio_toca" $TR (@("--strategy", "all", "--retriever", "dense", "--top-docs", "200") + $Toca)

# 4. Fusoes (segundos) ---------------------------------------------------------
foreach ($c in @(@{p = ""; f2 = "juristcu_fusao2_recortados"}, @{p = "jua_"; f2 = "jua_fusao2_recortados"}, @{p = "juanat_"; f2 = "juanat_fusao2_recortados"})) {
    $p = $c.p
    $b = Rodada "${p}bm25"; $bc = Rodada "${p}bm25_sec_sem_relatorio"; $bt = Rodada "${p}bm25_sec_sem_relatorio_toca"
    $d = Rodada "${p}dense_bge_m3"; $dc = Rodada "${p}dense_sec_sem_relatorio"; $dt = Rodada "${p}dense_sec_sem_relatorio_toca"
    if ($p) { SeFaltar "${p}fusao4_peso_igual" { & $Python -m src.fusion --metodo soma_norm --label "${p}fusao4_peso_igual" --experimentos $b $bc $d $dc } }
    SeFaltar "${p}fusao4_toca" { & $Python -m src.fusion --metodo soma_norm --label "${p}fusao4_toca" --experimentos $b $bt $d $dt }
    SeFaltar $c.f2 { & $Python -m src.fusion --metodo soma_norm --label $c.f2 --experimentos $bc $dc }
    SeFaltar "${p}fusao2_toca" { & $Python -m src.fusion --metodo soma_norm --label "${p}fusao2_toca" --experimentos $bt $dt }
}

# 5. Ranker aprendido: sinais por secao (structural_gold) e treino ------------
foreach ($c in @(@{p = "tr"; q = $TR}, @{p = "te"; q = $TE}, @{p = "jt"; q = $JT})) {
    $base = @("--strategy", "structural_gold", "--top-docs", "200")
    if ($c.p -eq "tr") {
        Busca "ltrsg_tr_bm25" $c.q ($base + @("--retriever", "bm25"))
        Busca "ltrsg_tr_bm25_semrel" $c.q ($base + @("--retriever", "bm25") + $SemRel)
        Busca "ltrsg_tr_dense" $c.q ($base + @("--retriever", "dense"))
        Busca "ltrsg_tr_dense_semrel" $c.q ($base + @("--retriever", "dense") + $SemRel)
    }
    foreach ($s in @("ementa", "relatorio", "fundamentacao", "dispositivo")) {
        Busca "ltrsg_$($c.p)_bm25_$s" $c.q ($base + @("--retriever", "bm25", "--secoes", $s))
        Busca "ltrsg_$($c.p)_dense_$s" $c.q ($base + @("--retriever", "dense", "--secoes", $s))
    }
}
SeFaltar "f7_ltr" { & $Python -m src.ltr --spec configs\f7_ltr.json --label f7_ltr }

# 6. Reranker zero-shot (cache de scores por colecao) --------------------------
function Fontes($p) {
    return @(
        "$(Rodada "${p}bm25")\runs\${Est}__bm25__chunks.jsonl",
        "$(Rodada "${p}bm25_sec_sem_relatorio")\runs\${Est}__bm25__sec-sem_relatorio__chunks.jsonl",
        "$(Rodada "${p}dense_bge_m3")\runs\${Est}__dense-bge_m3__chunks.jsonl",
        "$(Rodada "${p}dense_sec_sem_relatorio")\runs\${Est}__dense-bge_m3__sec-sem_relatorio__chunks.jsonl"
    )
}
foreach ($c in @(@{n = "juristcu"; p = ""; f4 = "fusao4_peso_igual"; q = $JT}, @{n = "jua"; p = "jua_"; f4 = "jua_fusao4_peso_igual"; q = $TE})) {
    $f4 = Rodada $c.f4; $b = Rodada "$($c.p)bm25"
    SeFaltar "$($c.n)_rerank_fusao4" {
        & $Python -m src.rerank --estrategia $Est --nome fusao4 --label "$($c.n)_rerank_fusao4" --queries $c.q `
            --candidatos "$f4\runs\${Est}__soma_norm.trec" --fontes (Fontes $c.p) `
            --cache "data\interim\rerank_cache\$($c.n)_$Est.tsv"
    }
    SeFaltar "$($c.n)_rerank_bm25" {
        & $Python -m src.rerank --estrategia $Est --nome bm25 --label "$($c.n)_rerank_bm25" --queries $c.q `
            --candidatos "$b\runs\${Est}__bm25.trec" --fontes "$b\runs\${Est}__bm25__chunks.jsonl" `
            --cache "data\interim\rerank_cache\$($c.n)_$Est.tsv"
    }
}

# 7. Reranker ajustado ao dominio (LoRA, treino do JUA) ------------------------
$modelo = "data\models\bge-reranker-v2-m3-jua-lora"
if (-not (Test-Path $modelo)) { Etapa "fine-tune do reranker" { & $Python -m src.finetune_reranker } }
foreach ($c in @(@{n = "juristcu"; p = ""; f4 = "fusao4_peso_igual"; q = $JT}, @{n = "jua"; p = "jua_"; f4 = "jua_fusao4_peso_igual"; q = $TE})) {
    $f4 = Rodada $c.f4
    SeFaltar "$($c.n)_rerank_ft_fusao4" {
        & $Python -m src.rerank --estrategia $Est --nome fusao4ft --label "$($c.n)_rerank_ft_fusao4" --queries $c.q `
            --modelo $modelo --max-length 512 `
            --candidatos "$f4\runs\${Est}__soma_norm.trec" --fontes (Fontes $c.p) `
            --cache "data\interim\rerank_cache\$($c.n)_${Est}_ft.tsv"
    }
}

# 8. Analise: replicacao em quatro amostras e painel ---------------------------
Etapa "replicacao final (H1-H8)" { & $Python -m src.replicacao --spec configs\f7_replicacao_final.json --label f7_replicacao_final }
Etapa "painel configuracao x colecao" { & $Python -m src.painel --spec configs\f7_painel.json --label f7_painel }

Registrar "fim da rodada F7 -> log em $log"
