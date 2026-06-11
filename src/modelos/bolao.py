"""
Bolão — simulação Monte Carlo do torneio inteiro a partir das previsões do
modelo (Dixon-Coles ancorado no Elo). Mostra o que os números dizem:
fase de grupos (quem avança / termina em 1º) e mata-mata (até o campeão).

Princípio: usa EXCLUSIVAMENTE os dados já no banco. O chaveamento é lido das
fixtures da Copa 2026 (times-placeholder 1A/2B/3X/W{n}/L{n}); o número de cada
partida é `id_do_banco - 28` (grupos = 1-72, R32 = 73-88, ... final = 104).
"""

import math
import logging
import random
from collections import defaultdict

import numpy as np

from src.db.repositorio import Repositorio
from src.modelos.dixon_coles import (
    DixonColes, LOG_MEDIA_GOLS, ANFITRIOES, HA_REAL, JANELA_FORMA,
)
from src.dados.ingestao import COMPETICOES_FORMA

logger = logging.getLogger(__name__)

OFFSET_ID_PARA_NUM = 28  # número da partida = id_do_banco - 28
FASES_MATA_MATA = {
    "round of 32": "R32", "round of 16": "R16", "quarter-final": "QF",
    "semi-final": "SF", "final": "FINAL", "match for third place": "3O",
}


# ---------------------------------------------------------------------------
# Carregar estrutura + parâmetros (uma vez)
# ---------------------------------------------------------------------------

def _carregar(repo: Repositorio) -> dict:
    dc = DixonColes(repo)
    with repo._conn() as conn:
        fixtures = conn.execute("""
            SELECT id, fase, grupo, campo_neutro, time_mandante_id, time_visitante_id
            FROM jogos WHERE competicao='copa_2026' ORDER BY id
        """).fetchall()

    grupos = defaultdict(list)        # 'A' -> [team_id,...]
    jogos_grupo = []                  # (grupo, home_id, away_id, campo_neutro)
    mata = {}                         # num -> dict(fase, home_ph, away_ph, neutro)
    placeholders = {}                 # team_id -> nome ('1A','W73',...)
    nomes = {}                        # team_id -> nome real (para placeholders, o próprio)

    for f in fixtures:
        num = f["id"] - OFFSET_ID_PARA_NUM
        hm = repo.buscar_time(f["time_mandante_id"])
        aw = repo.buscar_time(f["time_visitante_id"])
        hn = hm.nome if hm else "?"
        an = aw.nome if aw else "?"
        is_ph = lambda n: any(ch.isdigit() for ch in n) and (n[0] in "123WL")
        fase = f["fase"] or ""
        if fase.startswith("matchday"):
            g = f["grupo"]
            if g:
                for tid in (f["time_mandante_id"], f["time_visitante_id"]):
                    if tid not in grupos[g]:
                        grupos[g].append(tid)
                jogos_grupo.append((g, f["time_mandante_id"], f["time_visitante_id"], f["campo_neutro"]))
        elif fase in FASES_MATA_MATA:
            mata[num] = {
                "fase": FASES_MATA_MATA[fase],
                "home": hn, "away": an,        # placeholders ('1A','W73','3A/B/C/D/F')
                "neutro": 1,                    # mata-mata: sem mando definido → neutro
            }

    # Parâmetros (alpha/beta/elo) de cada seleção real, uma vez
    params = {}
    nome_por_id = {}
    todos_ids = set()
    for ids in grupos.values():
        todos_ids.update(ids)
    for tid in todos_ids:
        time = repo.buscar_time(tid)
        forma = repo.jogos_de_time(tid, COMPETICOES_FORMA, limite=JANELA_FORMA)
        p = dc._estimar_params(time, forma, tid)
        params[tid] = (p.alpha, p.beta, time.nome, time.rating_prior or 1500.0)
        nome_por_id[tid] = time.nome

    return {
        "grupos": dict(grupos), "jogos_grupo": jogos_grupo,
        "mata": mata, "params": params, "nome_por_id": nome_por_id,
    }


def _lambdas(params, hid, aid, neutro):
    a_h, b_h, _, _ = params[hid]
    a_a, b_a, _, _ = params[aid]
    ha = 0.0
    if not neutro:
        nome_h = params[hid][2]
        if nome_h in ANFITRIOES:
            ha = HA_REAL
    lam = math.exp(LOG_MEDIA_GOLS + a_h - b_a + ha)
    mu = math.exp(LOG_MEDIA_GOLS + a_a - b_h)
    return min(max(lam, 0.1), 8.0), min(max(mu, 0.1), 8.0)


# ---------------------------------------------------------------------------
# Matching dos 8 melhores terceiros nas vagas do R32
# ---------------------------------------------------------------------------

def _slots_terceiros(mata: dict) -> dict:
    """num do jogo R32 -> lista de grupos permitidos (do placeholder '3A/B/C/D/F')."""
    slots = {}
    for num, m in mata.items():
        for lado in ("home", "away"):
            ph = m[lado]
            if ph.startswith("3") and "/" in ph:
                slots[(num, lado)] = ph[1:].split("/")
    return slots


def _atribuir_terceiros(slots: dict, grupos_classificados: list) -> dict:
    """Casa cada grupo-3º classificado a uma vaga compatível (backtracking)."""
    chaves = list(slots.keys())
    usados = set()
    atrib = {}

    def bt(i):
        if i == len(chaves):
            return True
        k = chaves[i]
        permitidos = slots[k]
        for g in grupos_classificados:
            if g not in usados and g in permitidos:
                usados.add(g); atrib[k] = g
                if bt(i + 1):
                    return True
                usados.discard(g); atrib.pop(k, None)
        return False

    ordenadas = sorted(chaves, key=lambda k: len(slots[k]))  # mais restritas primeiro
    chaves = ordenadas
    bt(0)
    return atrib  # (num,lado) -> grupo


# ---------------------------------------------------------------------------
# Uma simulação completa
# ---------------------------------------------------------------------------

def _simular_uma(est: dict, rng) -> dict:
    params = est["params"]
    poisson = rng.poisson

    # --- Fase de grupos ---
    tab = {g: {tid: [0, 0, 0] for tid in ids} for g, ids in est["grupos"].items()}  # pts, gd, gf
    for g, hid, aid, neutro in est["jogos_grupo"]:
        lam, mu = _lambdas(params, hid, aid, neutro)
        gh, ga = int(poisson(lam)), int(poisson(mu))
        th, ta = tab[g][hid], tab[g][aid]
        th[1] += gh - ga; th[2] += gh; ta[1] += ga - gh; ta[2] += ga
        if gh > ga: th[0] += 3
        elif ga > gh: ta[0] += 3
        else: th[0] += 1; ta[0] += 1

    pos = {}     # placeholder '1A'/'2B' -> team_id
    terceiros = []  # (grupo, team_id, chave_ordenacao)
    for g, teams in tab.items():
        rank = sorted(teams.items(), key=lambda kv: (kv[1][0], kv[1][1], kv[1][2], rng.random()), reverse=True)
        pos[f"1{g}"] = rank[0][0]
        pos[f"2{g}"] = rank[1][0]
        t3 = rank[2]
        terceiros.append((g, t3[0], (t3[1][0], t3[1][1], t3[1][2], rng.random())))

    # 8 melhores terceiros
    terceiros.sort(key=lambda x: x[2], reverse=True)
    melhores = terceiros[:8]
    grupos_class = [g for g, _, _ in melhores]
    tid_por_grupo3 = {g: tid for g, tid, _ in melhores}

    # Atribui terceiros às vagas
    slots = est["slots_terceiros"]
    atrib = _atribuir_terceiros(slots, grupos_class)
    for (num, lado), g in atrib.items():
        pos[est["mata"][num][lado]] = tid_por_grupo3[g]  # placeholder '3X/Y/..' -> team_id

    # --- Mata-mata ---
    vencedor = {}  # num -> team_id
    perdedor = {}
    def resolve(ph):
        if ph in pos:
            return pos[ph]
        if ph.startswith("W"):
            return vencedor.get(int(ph[1:]))
        if ph.startswith("L"):
            return perdedor.get(int(ph[1:]))
        return None

    avancou = defaultdict(set)  # fase -> set(team_id)  (alcançou a fase)
    ordem = ["R32", "R16", "QF", "SF", "FINAL", "3O"]
    nums_por_fase = defaultdict(list)
    for num, m in est["mata"].items():
        nums_por_fase[m["fase"]].append(num)

    campeao = None
    for fase in ordem:
        for num in sorted(nums_por_fase[fase]):
            m = est["mata"][num]
            h = resolve(m["home"]); a = resolve(m["away"])
            if h is None or a is None:
                continue
            avancou[fase].add(h); avancou[fase].add(a)
            lam, mu = _lambdas(params, h, a, True)
            gh, ga = int(poisson(lam)), int(poisson(mu))
            if gh == ga:  # pênaltis
                gh, ga = (1, 0) if rng.random() < 0.5 else (0, 1)
            w, l = (h, a) if gh > ga else (a, h)
            vencedor[num] = w; perdedor[num] = l
            if fase == "FINAL":
                campeao = w

    return {
        "pos": pos, "avancou": avancou, "campeao": campeao,
        "primeiro_grupo": {pos[f"1{g}"] for g in tab},
        "avancou_grupo": {pos[f"1{g}"] for g in tab} | {pos[f"2{g}"] for g in tab} | set(tid_por_grupo3.values()),
        "grupo_rank": {g: sorted(teams.items(), key=lambda kv: (kv[1][0], kv[1][1], kv[1][2]), reverse=True)
                       for g, teams in tab.items()},
    }


# ---------------------------------------------------------------------------
# Agregação
# ---------------------------------------------------------------------------

def simular_torneio(repo: Repositorio = None, n: int = 10000, seed: int = 42) -> dict:
    from src.dados.ingestao import _get_repo
    repo = repo or _get_repo()
    est = _carregar(repo)
    est["slots_terceiros"] = _slots_terceiros(est["mata"])
    rng = np.random.default_rng(seed)
    nome = est["nome_por_id"]

    cont = defaultdict(lambda: defaultdict(int))  # team_id -> metric -> count
    soma_pts = defaultdict(float)
    soma_pos_grupo = defaultdict(lambda: defaultdict(int))  # team_id -> posição(1..4) -> count

    fase_metric = {"R16": "r16", "QF": "qf", "SF": "sf", "FINAL": "final"}

    for _ in range(n):
        s = _simular_uma(est, rng)
        for tid in s["avancou_grupo"]:
            cont[tid]["avanca"] += 1
        for tid in s["primeiro_grupo"]:
            cont[tid]["primeiro"] += 1
        for fase, met in fase_metric.items():
            for tid in s["avancou"].get(fase, ()):
                cont[tid][met] += 1
        if s["campeao"] is not None:
            cont[s["campeao"]]["campeao"] += 1
        for g, rank in s["grupo_rank"].items():
            for pos_idx, (tid, stats) in enumerate(rank):
                soma_pts[tid] += stats[0]
                soma_pos_grupo[tid][pos_idx + 1] += 1

    # Monta saída por grupo
    grupos_out = {}
    for g, ids in est["grupos"].items():
        linhas = []
        for tid in ids:
            linhas.append({
                "time": nome[tid],
                "pts_medio": round(soma_pts[tid] / n, 2),
                "p_1o": round(cont[tid]["primeiro"] / n, 3),
                "p_avanca": round(cont[tid]["avanca"] / n, 3),
            })
        linhas.sort(key=lambda x: x["p_avanca"], reverse=True)
        # cravado: top-2 por p_avanca
        for i, l in enumerate(linhas):
            l["cravado"] = ("1º" if i == 0 else "2º" if i == 1 else "")
        grupos_out[g] = linhas

    # Favoritos ao título
    titulo = []
    for tid in cont:
        titulo.append({
            "time": nome[tid],
            "p_campeao": round(cont[tid]["campeao"] / n, 4),
            "p_final": round(cont[tid]["final"] / n, 4),
            "p_semi": round(cont[tid]["sf"] / n, 4),
            "p_quartas": round(cont[tid]["qf"] / n, 4),
            "p_oitavas": round(cont[tid]["r16"] / n, 4),
            "p_avanca": round(cont[tid]["avanca"] / n, 4),
        })
    titulo.sort(key=lambda x: x["p_campeao"], reverse=True)

    return {
        "n_simulacoes": n,
        "grupos": {g: grupos_out[g] for g in sorted(grupos_out)},
        "favoritos": titulo,
    }
