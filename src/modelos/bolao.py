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
from collections import defaultdict

import numpy as np
from scipy.stats import poisson as _poisson

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
            SELECT id, fase, grupo, campo_neutro, time_mandante_id, time_visitante_id,
                   placar_mandante, placar_visitante
            FROM jogos WHERE competicao='copa_2026' ORDER BY id
        """).fetchall()

    grupos = defaultdict(list)        # 'A' -> [team_id,...]
    jogos_grupo = []                  # (grupo, home_id, away_id, campo_neutro, placar_m|None, placar_v|None)
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
                jogos_grupo.append((g, f["time_mandante_id"], f["time_visitante_id"], f["campo_neutro"],
                                    f["placar_mandante"], f["placar_visitante"]))
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
    for g, hid, aid, neutro, pm, pv in est["jogos_grupo"]:
        if pm is not None and pv is not None:
            gh, ga = int(pm), int(pv)            # jogo já disputado → resultado real travado
        else:
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


# ---------------------------------------------------------------------------
# Chaveamento provável (determinístico: em cada jogo avança o favorito)
# ---------------------------------------------------------------------------

def _grid_1x2(params, h, a, neutro):
    lam, mu = _lambdas(params, h, a, neutro)
    ph = [_poisson.pmf(i, lam) for i in range(10)]
    pa = [_poisson.pmf(j, mu) for j in range(10)]
    pw = sum(ph[i] * pa[j] for i in range(10) for j in range(10) if i > j)
    pe = sum(ph[i] * pa[i] for i in range(10))
    pl = 1.0 - pw - pe
    return pw, pe, pl


def bracket_provavel(repo: Repositorio = None) -> dict:
    """Caminho mais provável do torneio: classifica os grupos por pontos esperados
    e, em cada jogo do mata-mata, avança o favorito. Devolve a árvore do chaveamento."""
    from src.dados.ingestao import _get_repo
    repo = repo or _get_repo()
    est = _carregar(repo)
    est["slots_terceiros"] = _slots_terceiros(est["mata"])
    params = est["params"]; nome = est["nome_por_id"]

    # --- Grupos: pontos esperados ---
    pts = {g: {tid: 0.0 for tid in ids} for g, ids in est["grupos"].items()}
    for g, hid, aid, neutro, pm, pv in est["jogos_grupo"]:
        if pm is not None and pv is not None:        # jogo já disputado → pontos reais
            if pm > pv: pts[g][hid] += 3
            elif pv > pm: pts[g][aid] += 3
            else: pts[g][hid] += 1; pts[g][aid] += 1
        else:                                         # jogo futuro → pontos esperados
            pw, pe, pl = _grid_1x2(params, hid, aid, neutro)
            pts[g][hid] += 3 * pw + pe
            pts[g][aid] += 3 * pl + pe

    def elo(tid):
        return params[tid][3]

    pos = {}; terceiros = []
    for g, teams in pts.items():
        rank = sorted(teams.items(), key=lambda kv: (kv[1], elo(kv[0])), reverse=True)
        pos[f"1{g}"] = rank[0][0]; pos[f"2{g}"] = rank[1][0]
        terceiros.append((g, rank[2][0], rank[2][1]))
    terceiros.sort(key=lambda x: (x[2], elo(x[1])), reverse=True)
    melhores = terceiros[:8]
    tid_por_grupo3 = {g: tid for g, tid, _ in melhores}
    atrib = _atribuir_terceiros(est["slots_terceiros"], [g for g, _, _ in melhores])
    for (num, lado), g in atrib.items():
        pos[est["mata"][num][lado]] = tid_por_grupo3[g]

    # --- Topologia da árvore a partir das referências W{n} ---
    filhos = {}  # num -> (num_home_child|None, num_away_child|None)
    for num, m in est["mata"].items():
        def child(ph):
            return int(ph[1:]) if ph and ph[0] in "WL" and ph[1:].isdigit() else None
        filhos[num] = (child(m["home"]), child(m["away"]))

    vencedor = {}; perdedor = {}; registro = {}
    def resolve(ph):
        if ph in pos: return pos[ph]
        if ph and ph[0] == "W": return vencedor.get(int(ph[1:]))
        if ph and ph[0] == "L": return perdedor.get(int(ph[1:]))
        return None

    for num in sorted(est["mata"]):  # ordem crescente = R32→...→final
        m = est["mata"][num]
        h = resolve(m["home"]); a = resolve(m["away"])
        if h is None or a is None:
            continue
        pw, pe, pl = _grid_1x2(params, h, a, True)
        w, l = (h, a) if pw >= pl else (a, h)
        vencedor[num] = w; perdedor[num] = l
        registro[num] = {"home": nome[h], "away": nome[a], "winner": nome[w]}

    # --- Ordena cada lado por posição na árvore (índice da folha R32) ---
    def folhas(num):
        ch = filhos.get(num, (None, None))
        if ch[0] is None and ch[1] is None:
            return [num]
        out = []
        for c in ch:
            out += folhas(c) if c is not None else []
        return out

    final_num = max(est["mata"])  # 104
    sf_h, sf_a = filhos[final_num]  # SF esquerda/direita

    def rounds_do_lado(root):
        ordem_folhas = folhas(root)
        idx = {n: i for i, n in enumerate(ordem_folhas)}
        # agrupa por rodada (profundidade) usando o tamanho do subtree
        por_rodada = defaultdict(list)
        def visita(num):
            ch = filhos.get(num, (None, None))
            if ch[0] is None and ch[1] is None:
                por_rodada[0].append((idx[num], num)); return 0
            d = 1 + max(visita(c) for c in ch if c is not None)
            minidx = min(idx[f] for f in folhas(num))
            por_rodada[d].append((minidx, num)); return d
        visita(root)
        rodadas = []
        for d in sorted(por_rodada):
            ms = [registro.get(n) for _, n in sorted(por_rodada[d])]
            rodadas.append(ms)
        return rodadas  # [R32, R16, QF, SF]

    # 3º lugar
    terc = None
    for num, m in est["mata"].items():
        if m["fase"] == "3O" and num in registro:
            terc = registro[num]

    return {
        "campeao": registro.get(final_num, {}).get("winner"),
        "final": registro.get(final_num),
        "terceiro": terc,
        "esq": rounds_do_lado(sf_h),
        "dir": rounds_do_lado(sf_a),
    }
