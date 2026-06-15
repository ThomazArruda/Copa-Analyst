"""
Orquestrador de ingestão — Fase 1.
Dois modos de uso:

  1. ingestao_inicial()     — rodar uma vez para popular o banco com todos os dados históricos
  2. pacote_jogo(jogo_id)   — dado um jogo da Copa 2026, retornar o pacote completo de dados duros
"""

import logging
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

from src.db.repositorio import Repositorio, Jogo, Time
from src.dados.openfootball import IngestorOpenfootball
from src.dados.api_football import ClienteApiFootball
from src.dados.thesportsdb import ClienteTheSportsDB, COPA_2026_LEAGUE_ID
from src.dados.wikipedia_scraper import ScraperWikipedia
from src.modelos.rating_prior import RatingPrior

load_dotenv()
logger = logging.getLogger(__name__)

# Competições usadas para calcular forma recente (Decisão 11)
COMPETICOES_FORMA = [
    "copa_2026",
    "copa_2022",
    "amistosos_2026",
    "recentes_2026",
    "elim_conmebol_2022",
    "elim_uefa_2024",
    "elim_concacaf_2022",
    "elim_asia_2022",
    "elim_africa_2022",
    "elim_conmebol_2026",
    "elim_uefa_2026",
    "elim_concacaf_2026",
    "elim_afc_2026",
    "elim_caf_2026",
    "amistosos_2024",
]

COMPETICOES_STATS = [
    "copa_2022",
    "elim_conmebol_2022",
    "elim_uefa_2024",
    "elim_concacaf_2022",
    "elim_asia_2022",
    "elim_africa_2022",
]


def _get_repo() -> Repositorio:
    db_path = os.getenv("COPA_DB_PATH", "dados/copa_analyst.db")
    return Repositorio(db_path)


# ---------------------------------------------------------------------------
# Ingestão inicial (rodar uma vez)
# ---------------------------------------------------------------------------

def _corrigir_campo_neutro_anfitrioes(repo: Repositorio):
    """
    Copa 2026: México, Canadá e EUA jogam em seus países → campo_neutro=0.
    Todos os demais jogos mantêm campo_neutro=1 (PRD 7.1).
    """
    anfitrioes = {"Mexico", "Canada", "United States"}
    jogos = repo.listar_jogos_copa26()
    corrigidos = 0
    for jogo in jogos:
        time_m = repo.buscar_time(jogo.time_mandante_id)
        if time_m and time_m.nome in anfitrioes and jogo.campo_neutro == 1:
            with repo._conn() as conn:
                conn.execute(
                    "UPDATE jogos SET campo_neutro = 0 WHERE id = ?", (jogo.id,)
                )
            corrigidos += 1
    logger.info("campo_neutro=0 aplicado para %d jogos de anfitrioes", corrigidos)


def ingestao_inicial(pular_api_football: bool = False) -> dict:
    """
    Popula o banco com todos os dados históricos.
    Idempotente: pode rodar múltiplas vezes sem duplicar dados.
    """
    repo = _get_repo()
    relatorio = {
        "copa_2026_fixtures": 0,
        "copa_2022_fixtures": 0,
        "rating_prior": 0,
        "qualificatorias_wikipedia": {},
        "stats_api_football": {},
        "erros": [],
    }

    # 1. Calendário Copa 2026 via openfootball
    logger.info("--- [1/5] Copa 2026 — openfootball ---")
    of = IngestorOpenfootball(repo)
    relatorio["copa_2026_fixtures"] = of.ingerir_copa2026()

    # 2. Copa 2022 via openfootball (estrutura + resultados)
    logger.info("--- [2/5] Copa 2022 — openfootball ---")
    relatorio["copa_2022_fixtures"] = of.ingerir_copa2022()

    # Marcar campo_neutro=0 para anfitriões jogando em casa (Copa 2026)
    _corrigir_campo_neutro_anfitrioes(repo)

    # 3. Rating prior — Elo calculado sobre jogos históricos já ingeridos
    logger.info("--- [3/5] Rating prior --- Elo calculado sobre historico ---")
    rp = RatingPrior(repo)
    relatorio["rating_prior"] = rp.calcular_e_salvar()

    # 4. Qualificatórias 2025/2026 via Wikipedia (forma recente)
    logger.info("--- [4/5] Qualificatórias — Wikipedia ---")
    scraper = ScraperWikipedia(repo)
    relatorio["qualificatorias_wikipedia"] = scraper.ingerir_todas()

    # 5. Estatísticas Copa 2022 + eliminatórias via API-Football (cache-first)
    if not pular_api_football:
        logger.info("--- [5/5] Estatísticas — API-Football ---")
        res_stats = coletar_stats_api_football(repo)
        relatorio["stats_api_football"] = res_stats["por_competicao"]
        relatorio["erros"].extend(res_stats["erros"])
    else:
        logger.info("--- [5/5] API-Football pulado (pular_api_football=True) ---")

    # 6. Jogos recentes (amistosos pré-Copa) via TheSportsDB — dados mais atuais
    logger.info("--- [6] Recentes — TheSportsDB ---")
    try:
        relatorio["recentes"] = ingerir_recentes_thesportsdb(repo)
    except Exception as e:
        relatorio["erros"].append(f"Recentes falhou: {e}")

    return relatorio


def coletar_stats_api_football(repo: Repositorio) -> dict:
    """
    Coleta estatísticas de partida via API-Football (cache-first; aborta ao bater
    o limite de 100/dia). Extraída de `ingestao_inicial` para poder rodar isolada
    na ingestão diária — sem re-scrape de Wikipedia / openfootball / Elo.
    Retorna {por_competicao, erros, limite_atingido}.
    """
    resultado = {"por_competicao": {}, "erros": [], "limite_atingido": False}
    try:
        af = ClienteApiFootball(repo)
        status = af.status_conta()
        if status:
            usados = status.get("requests", {}).get("current", "?")
            limite = status.get("requests", {}).get("limit_day", 100)
            logger.info("API-Football: %s/%s requests usados hoje", usados, limite)

        for competicao_key in COMPETICOES_STATS:
            if af.limite_diario_atingido:
                break
            fixtures = af.buscar_fixtures(competicao_key)
            logger.info("%s: %d fixtures encontrados", competicao_key, len(fixtures))
            stats_ok = 0
            for f in fixtures:
                if af.limite_diario_atingido:
                    break
                fixture_id = f["fixture"]["id"]
                status_jogo = f["fixture"]["status"]["short"]
                if status_jogo != "FT":
                    continue
                # Buscar e armazenar estatísticas (cache-first — não gasta request se já tiver)
                stats = af.buscar_estatisticas(fixture_id)
                if stats:
                    _salvar_stats_api_football(repo, f, stats, competicao_key)
                    stats_ok += 1
            resultado["por_competicao"][competicao_key] = stats_ok
            logger.info("%s: %d jogos com stats", competicao_key, stats_ok)
        if af.limite_diario_atingido:
            resultado["limite_atingido"] = True
            logger.info("Coleta de stats interrompida: limite diário da API-Football atingido.")
            resultado["erros"].append("API-Football: limite diário (100/dia) atingido — coleta parcial.")
    except Exception as e:
        msg = f"API-Football falhou: {e}"
        logger.error(msg)
        resultado["erros"].append(msg)
    return resultado


def _salvar_stats_api_football(repo: Repositorio, fixture: dict, stats: list, competicao: str):
    """Salva resultado e estatísticas de um fixture do API-Football no banco."""
    f = fixture["fixture"]
    teams = fixture["teams"]
    goals = fixture.get("goals", {})

    # Garantir times
    nome_home = teams["home"]["name"]
    nome_away = teams["away"]["name"]
    id_home = repo.upsert_time(Time(id=None, nome=nome_home))
    id_away = repo.upsert_time(Time(id=None, nome=nome_away))

    # Jogo
    data_str = f["date"][:10] if f.get("date") else ""
    hora_utc = f["date"][11:16] if f.get("date") and len(f["date"]) > 10 else None

    jogo = Jogo(
        id=None,
        competicao=competicao,
        data=data_str,
        hora_utc=hora_utc,
        time_mandante_id=id_home,
        time_visitante_id=id_away,
        campo_neutro=1,
        fase="qualificacao" if "elim" in competicao else ("grupo" if "2022" in competicao else None),
        placar_mandante=goals.get("home"),
        placar_visitante=goals.get("away"),
        id_externo=str(f["id"]),
        fonte="api_football",
    )
    jogo_id = repo.upsert_jogo(jogo)

    # Estatísticas por time
    from src.db.repositorio import EstatisticaJogo

    time_ids = {"home": id_home, "away": id_away}
    for team_stats in stats:
        lado = "home" if team_stats["team"]["name"] == nome_home else "away"
        time_id = time_ids[lado]

        def _val(tipo):
            for s in team_stats.get("statistics", []):
                if s["type"] == tipo:
                    v = s["value"]
                    if v is None:
                        return None
                    if isinstance(v, str):
                        v = v.replace("%", "").strip()
                        try:
                            return float(v)
                        except ValueError:
                            return None
                    return float(v)
            return None

        est = EstatisticaJogo(
            jogo_id=jogo_id,
            time_id=time_id,
            gols=int(_val("Ball Possession") or 0) if False else None,
            escanteios=int(_val("Corner Kicks") or 0) if _val("Corner Kicks") is not None else None,
            chutes=int(_val("Total Shots") or 0) if _val("Total Shots") is not None else None,
            chutes_no_alvo=int(_val("Shots on Goal") or 0) if _val("Shots on Goal") is not None else None,
            faltas=int(_val("Fouls") or 0) if _val("Fouls") is not None else None,
            cartoes_amarelos=int(_val("Yellow Cards") or 0) if _val("Yellow Cards") is not None else None,
            cartoes_vermelhos=int(_val("Red Cards") or 0) if _val("Red Cards") is not None else None,
            posse=_val("Ball Possession"),
            xg=None,
            fonte="api_football",
        )
        repo.upsert_estatistica(est)


# ---------------------------------------------------------------------------
# Atualizar resultados Copa 2026 (rodar antes de cada análise)
# ---------------------------------------------------------------------------

def ingerir_recentes_thesportsdb(repo: Repositorio = None, desde: str = "2025-06-01") -> dict:
    """
    Puxa os jogos recentes (amistosos pré-Copa + outros) de cada seleção da Copa
    2026 via TheSportsDB. Sem cota diária. Alimenta a forma recente — em especial
    os warm-ups de maio/junho, os dados mais atuais que temos.
    """
    from src.dados.thesportsdb import ClienteTheSportsDB
    repo = repo or _get_repo()
    tsdb = ClienteTheSportsDB(repo)

    # Times reais da Copa 2026 (exclui placeholders tipo 1A/W73)
    nomes = set()
    for j in repo.listar_jogos_copa26():
        for tid in (j.time_mandante_id, j.time_visitante_id):
            t = repo.buscar_time(tid)
            if t and not (len(t.nome) <= 4 and any(ch.isdigit() for ch in t.nome)):
                nomes.add(t.nome)

    novos = 0
    erros = []
    idx_times = _indice_times_norm(repo)  # resolução por nome normalizado (anti-clone)
    for nome in sorted(nomes):
        try:
            tid = tsdb.buscar_id_time(nome)
            if not tid:
                continue
            for e in tsdb.buscar_ultimos_jogos_time(tid):
                data = e.get("dateEvent")
                if not data or data < desde:
                    continue
                if e.get("intHomeScore") is None or e.get("strStatus") != "FT":
                    continue
                home = e.get("strHomeTeam"); away = e.get("strAwayTeam")
                if not home or not away:
                    continue
                liga = (e.get("strLeague") or "").lower()
                comp = "amistosos_2026" if "friendl" in liga else "recentes_2026"
                id_home = _resolver_time_id(repo, home, idx_times)
                id_away = _resolver_time_id(repo, away, idx_times)
                jid = repo.upsert_jogo(Jogo(
                    id=None, competicao=comp, data=data,
                    hora_utc=None, time_mandante_id=id_home, time_visitante_id=id_away,
                    campo_neutro=0, fase=None,
                    placar_mandante=int(e["intHomeScore"]), placar_visitante=int(e["intAwayScore"]),
                    id_externo=str(e.get("idEvent") or ""), fonte="thesportsdb",
                ))
                novos += 1
        except Exception as ex:
            erros.append(f"{nome}: {ex}")
            logger.warning("Recentes %s falhou: %s", nome, ex)

    # Auto-cura: remove qualquer duplicata (mesmo jogo já vindo das qualificatórias)
    rem = deduplicar_jogos(repo)
    logger.info("Recentes TheSportsDB: %d jogos upsertados, %d duplicatas limpas", novos, rem)
    return {"upsertados": novos, "duplicatas_removidas": rem, "erros": erros}


def deduplicar_jogos(repo: Repositorio = None) -> int:
    """
    Remove jogos duplicados (mesmo (data, par de times) em rótulos/fontes/orientações
    diferentes). Mantém o que tem mais estatísticas. Idempotente. Retorna nº removidos.
    """
    repo = repo or _get_repo()
    removidos = 0
    with repo._conn() as conn:
        grupos = conn.execute("""
            SELECT data, MIN(time_mandante_id, time_visitante_id) a,
                         MAX(time_mandante_id, time_visitante_id) b
            FROM jogos
            WHERE placar_mandante IS NOT NULL AND data IS NOT NULL AND data != ''
              AND time_mandante_id IS NOT NULL AND time_visitante_id IS NOT NULL
            GROUP BY data, a, b HAVING COUNT(*) > 1
        """).fetchall()
        for g in grupos:
            rows = conn.execute("""
                SELECT id FROM jogos
                WHERE data=? AND placar_mandante IS NOT NULL
                  AND MIN(time_mandante_id, time_visitante_id)=?
                  AND MAX(time_mandante_id, time_visitante_id)=? ORDER BY id
            """, (g["data"], g["a"], g["b"])).fetchall()
            ids = [r["id"] for r in rows]
            def ns(jid):
                return conn.execute("SELECT COUNT(*) FROM estatisticas_jogo WHERE jogo_id=?", (jid,)).fetchone()[0]
            survivor = max(ids, key=lambda j: (ns(j), -j))
            for jid in ids:
                if jid == survivor:
                    continue
                for s in conn.execute("SELECT id, time_id FROM estatisticas_jogo WHERE jogo_id=?", (jid,)).fetchall():
                    ja = conn.execute("SELECT 1 FROM estatisticas_jogo WHERE jogo_id=? AND time_id=?",
                                      (survivor, s["time_id"])).fetchone()
                    if ja:
                        conn.execute("DELETE FROM estatisticas_jogo WHERE id=?", (s["id"],))
                    else:
                        conn.execute("UPDATE estatisticas_jogo SET jogo_id=? WHERE id=?", (survivor, s["id"]))
                conn.execute("DELETE FROM jogos WHERE id=?", (jid,))
                removidos += 1
    return removidos


def _norm_nome(s: str) -> str:
    """Normaliza nome de time para casamento robusto entre fontes:
    minúsculas, sem acentos, sem 'and', só alfanumérico. Ex.:
    'Bosnia & Herzegovina' == 'Bosnia-Herzegovina' == 'bosnia herzegovina'."""
    if not s:
        return ""
    import unicodedata
    import re
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.lower()
    s = re.sub(r"\b(and)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def _dist_data(d1: str, d2: str) -> int:
    """Distância em dias entre duas datas ISO (absorve o deslocamento de fuso
    entre a data local do openfootball e a data UTC da TheSportsDB)."""
    from datetime import date as _date
    try:
        a = _date.fromisoformat((d1 or "")[:10])
        b = _date.fromisoformat((d2 or "")[:10])
        return abs((a - b).days)
    except Exception:
        return 9999


def _indice_times_norm(repo: Repositorio) -> dict:
    """Mapa nome-normalizado -> lista de times existentes (para resolução robusta)."""
    idx: dict = {}
    for t in repo.listar_times():
        idx.setdefault(_norm_nome(t.nome), []).append(t)
    return idx


def _resolver_time_id(repo: Repositorio, nome: str, idx: dict = None) -> int:
    """Resolve um nome de time a um id existente por nome NORMALIZADO, preferindo
    o time canônico (o que tem rating_prior). Só cria um time novo se nenhum casar.
    Evita clones como 'Bosnia-Herzegovina' vs 'Bosnia & Herzegovina'."""
    n = _norm_nome(nome)
    cands = idx.get(n) if idx is not None else [
        t for t in repo.listar_times() if _norm_nome(t.nome) == n
    ]
    if cands:
        cands = sorted(cands, key=lambda t: (t.rating_prior is None, t.id))
        return cands[0].id
    return repo.upsert_time(Time(id=None, nome=nome))


def fundir_times_clones(repo: Repositorio) -> int:
    """Auto-cura de times: funde cada time SEM rating cujo nome normalizado bate com
    um time COM rating (o canônico) — ex.: 'Bosnia-Herzegovina' → 'Bosnia & Herzegovina'.
    Reaponta jogos e estatísticas para o canônico e apaga o clone. Idempotente.
    Garante que a forma recente não fique dividida entre identidades duplicadas, mesmo
    após um reseed do deploy. Retorna o número de clones fundidos."""
    canon: dict = {}
    clones: list = []
    for t in repo.listar_times():
        n = _norm_nome(t.nome)
        if t.rating_prior is not None:
            canon.setdefault(n, t)
    for t in repo.listar_times():
        if t.rating_prior is None:
            alvo = canon.get(_norm_nome(t.nome))
            if alvo and alvo.id != t.id:
                clones.append((t.id, alvo.id))

    if not clones:
        return 0

    with repo._conn() as conn:
        for clone_id, canon_id in clones:
            for s in conn.execute(
                "SELECT id, jogo_id FROM estatisticas_jogo WHERE time_id = ?", (clone_id,)
            ).fetchall():
                ja = conn.execute(
                    "SELECT 1 FROM estatisticas_jogo WHERE jogo_id = ? AND time_id = ?",
                    (s["jogo_id"], canon_id),
                ).fetchone()
                if ja:
                    conn.execute("DELETE FROM estatisticas_jogo WHERE id = ?", (s["id"],))
                else:
                    conn.execute(
                        "UPDATE estatisticas_jogo SET time_id = ? WHERE id = ?",
                        (canon_id, s["id"]),
                    )
            conn.execute(
                "UPDATE jogos SET time_mandante_id = ? WHERE time_mandante_id = ?",
                (canon_id, clone_id),
            )
            conn.execute(
                "UPDATE jogos SET time_visitante_id = ? WHERE time_visitante_id = ?",
                (canon_id, clone_id),
            )
            conn.execute("DELETE FROM times WHERE id = ?", (clone_id,))

    deduplicar_jogos(repo)  # limpa jogos que viraram duplicados após o reaponte
    logger.info("Times: %d clone(s) fundido(s) no canônico", len(clones))
    return len(clones)


def _evento_eh_copa_ft(e: dict) -> bool:
    """True se o evento do TheSportsDB é um jogo da Copa, encerrado e com placar."""
    if e.get("intHomeScore") is None or e.get("intAwayScore") is None:
        return False
    if (e.get("strStatus") or "") != "FT":
        return False
    liga = (e.get("strLeague") or "").lower()
    return "world cup" in liga or str(e.get("idLeague") or "") == str(COPA_2026_LEAGUE_ID)


def _coletar_resultados_tsdb(repo: Repositorio, tsdb, fixtures: list) -> list[dict]:
    """Reúne os resultados FT da Copa de MÚLTIPLOS endpoints do TheSportsDB.

    Necessário porque o free tier trunca cada endpoint por-liga (~5 jogos):
    `eventsseason`/`eventsround` não trazem o torneio todo. A cobertura completa
    vem de `eventslast` por seleção — cada jogo disputado aparece nos últimos
    jogos de pelo menos um dos dois times. Faz a união e deduplica por idEvent.
    Só consulta seleções cujo fixture já começou (data <= hoje) e ainda está sem
    placar, para não desperdiçar requisições (cota TheSportsDB)."""
    from datetime import date as _date

    eventos: dict = {}

    def _add(e: dict):
        if not _evento_eh_copa_ft(e):
            return
        chave = e.get("idEvent") or (
            f"{e.get('dateEvent')}|{e.get('strHomeTeam')}|{e.get('strAwayTeam')}"
        )
        eventos[chave] = e

    # 1) Endpoints por liga, baratos (truncados pelo free tier, mas complementares):
    #    season pega os primeiros jogos; pastleague pega o(s) mais recente(s).
    for e in tsdb.buscar_resultados_copa26():
        _add(e)
    for e in tsdb.buscar_passados_liga():
        _add(e)

    # 2) Por seleção: só as que têm jogo já iniciado e ainda sem placar.
    hoje = _date.today().isoformat()
    nomes: set = set()
    for f in fixtures:
        j = f["jogo"]
        if j.placar_mandante is not None:
            continue
        if (j.data or "") > hoje:
            continue
        for nome in (f["nome_m"], f["nome_v"]):
            # ignora placeholders de chaveamento (ex.: '1A', 'W73', '3X')
            if nome and not (len(nome) <= 4 and any(c.isdigit() for c in nome)):
                nomes.add(nome)

    for nome in sorted(nomes):
        try:
            tid = tsdb.buscar_id_time(nome)
            if not tid:
                continue
            for e in tsdb.buscar_ultimos_jogos_time(tid):
                _add(e)
        except Exception:
            logger.warning("Falha ao buscar últimos jogos de %s", nome)

    return list(eventos.values())


def atualizar_resultados_copa26() -> int:
    """
    Puxa resultados mais recentes da Copa 2026 via TheSportsDB e os grava
    **no fixture canônico** (openfootball) — nunca cria fixtures nem times novos.

    O casamento é por PAR DE TIMES NORMALIZADO (qualquer orientação), com desempate
    pela data mais próxima. Isso é robusto contra (a) o deslocamento de fuso
    (TheSportsDB usa data UTC; openfootball usa data local) e (b) divergências de
    nome entre as fontes ('Bosnia-Herzegovina' vs 'Bosnia & Herzegovina'), que antes
    geravam jogos e times duplicados. Retorna número de jogos atualizados.
    """
    from src.dados.resultados import preencher_resultado_real_jogo

    repo = _get_repo()
    fundir_times_clones(repo)  # auto-cura: funde clones antes de casar fixtures
    tsdb = ClienteTheSportsDB(repo)

    # Índice dos fixtures da Copa por par de times normalizado.
    fixtures = []
    for j in repo.listar_jogos_copa26():
        tm = repo.buscar_time(j.time_mandante_id)
        tv = repo.buscar_time(j.time_visitante_id)
        nm = _norm_nome(tm.nome if tm else "")
        nv = _norm_nome(tv.nome if tv else "")
        fixtures.append({
            "jogo": j, "nm": nm, "nv": nv, "par": frozenset({nm, nv}),
            "nome_m": tm.nome if tm else "", "nome_v": tv.nome if tv else "",
        })

    resultados = _coletar_resultados_tsdb(repo, tsdb, fixtures)

    atualizados = 0
    for evento in resultados:
        ph = evento.get("intHomeScore")
        pa = evento.get("intAwayScore")
        if ph is None or pa is None:
            continue
        nh = _norm_nome(evento.get("strHomeTeam", ""))
        na = _norm_nome(evento.get("strAwayTeam", ""))
        par = frozenset({nh, na})
        if len(par) != 2:
            continue

        cands = [f for f in fixtures if f["par"] == par]
        if not cands:
            logger.warning(
                "Resultado da Copa sem fixture correspondente: %s x %s — ignorado",
                evento.get("strHomeTeam"), evento.get("strAwayTeam"),
            )
            continue
        # Preferir o fixture canônico (openfootball) sobre qualquer resíduo da TheSportsDB.
        canonicos = [f for f in cands if (f["jogo"].fonte or "") != "thesportsdb"]
        pool = canonicos or cands
        data_ev = evento.get("dateEvent", "")
        alvo = min(pool, key=lambda f: _dist_data(f["jogo"].data, data_ev))
        jogo = alvo["jogo"]

        # Orienta o placar conforme o mandante do fixture (não do evento).
        if alvo["nm"] == nh:
            pm, pv = int(ph), int(pa)
        else:
            pm, pv = int(pa), int(ph)

        # Grava o placar no fixture canônico e preenche resultado_real (relatório oficial).
        preencher_resultado_real_jogo(jogo.id, pm, pv, repo)
        atualizados += 1

    # Auto-cura: remove resíduos da TheSportsDB que duplicam um fixture canônico.
    removidos = _limpar_duplicatas_copa26(repo)
    logger.info(
        "Copa 2026: %d resultados gravados no fixture canônico; %d duplicatas removidas",
        atualizados, removidos,
    )
    return atualizados


def _limpar_duplicatas_copa26(repo: Repositorio) -> int:
    """Remove linhas copa_2026 vindas da TheSportsDB que duplicam um fixture canônico
    (mesmo par de times normalizado) e apaga times órfãos sem rating criados por engano.
    Idempotente — seguro rodar a cada atualização."""
    removidos = 0
    jogos = repo.listar_jogos_copa26()
    # Mapa par-normalizado -> fixtures canônicos (não-TheSportsDB)
    canon = {}
    for j in jogos:
        if (j.fonte or "") == "thesportsdb":
            continue
        tm = repo.buscar_time(j.time_mandante_id)
        tv = repo.buscar_time(j.time_visitante_id)
        par = frozenset({_norm_nome(tm.nome if tm else ""), _norm_nome(tv.nome if tv else "")})
        if len(par) == 2:
            canon.setdefault(par, []).append(j)

    with repo._conn() as conn:
        for j in jogos:
            if (j.fonte or "") != "thesportsdb":
                continue
            tm = repo.buscar_time(j.time_mandante_id)
            tv = repo.buscar_time(j.time_visitante_id)
            par = frozenset({_norm_nome(tm.nome if tm else ""), _norm_nome(tv.nome if tv else "")})
            if par in canon:  # existe fixture canônico → este é resíduo
                conn.execute("DELETE FROM estatisticas_jogo WHERE jogo_id = ?", (j.id,))
                conn.execute("DELETE FROM jogos WHERE id = ?", (j.id,))
                removidos += 1

        # Apaga times sem rating que ficaram sem nenhum jogo referenciando-os.
        conn.execute("""
            DELETE FROM times
            WHERE rating_prior IS NULL
              AND id NOT IN (SELECT time_mandante_id FROM jogos WHERE time_mandante_id IS NOT NULL)
              AND id NOT IN (SELECT time_visitante_id FROM jogos WHERE time_visitante_id IS NOT NULL)
        """)
    return removidos


# ---------------------------------------------------------------------------
# Pacote de dados para análise de um jogo (Fase 3)
# ---------------------------------------------------------------------------

def pacote_jogo(jogo_id: int) -> dict:
    """
    Dado um jogo_id da Copa 2026, retorna todos os dados disponíveis para análise.
    Inclui lista de fatores_ausentes quando algum dado não foi encontrado.
    """
    repo = _get_repo()
    jogo = repo.buscar_jogo(jogo_id)
    if not jogo:
        raise ValueError(f"Jogo {jogo_id} não encontrado no banco")

    time_m = repo.buscar_time(jogo.time_mandante_id)
    time_v = repo.buscar_time(jogo.time_visitante_id)
    ausentes = []

    # Rating prior
    prior_m = time_m.rating_prior if time_m else None
    prior_v = time_v.rating_prior if time_v else None
    if prior_m is None:
        ausentes.append(f"Rating prior ausente: {time_m.nome if time_m else 'mandante'}")
    if prior_v is None:
        ausentes.append(f"Rating prior ausente: {time_v.nome if time_v else 'visitante'}")

    # Forma na Copa 2026 (jogos já disputados)
    forma_copa_m = repo.jogos_de_time(jogo.time_mandante_id, ["copa_2026"], limite=10)
    forma_copa_v = repo.jogos_de_time(jogo.time_visitante_id, ["copa_2026"], limite=10)
    # Excluir o próprio jogo
    forma_copa_m = [j for j in forma_copa_m if j.id != jogo_id]
    forma_copa_v = [j for j in forma_copa_v if j.id != jogo_id]
    if not forma_copa_m and not forma_copa_v:
        ausentes.append("Forma na Copa 2026: nenhum jogo disputado ainda (primeira rodada)")

    # Forma recente (todas as competições disponíveis). Limite alto: o modelo usa
    # todos os jogos com decaimento por recência (nada é descartado).
    forma_recente_m = repo.jogos_de_time(jogo.time_mandante_id, COMPETICOES_FORMA, limite=30)
    forma_recente_v = repo.jogos_de_time(jogo.time_visitante_id, COMPETICOES_FORMA, limite=30)
    if not forma_recente_m:
        ausentes.append(f"Forma recente ausente: {time_m.nome if time_m else 'mandante'}")
    if not forma_recente_v:
        ausentes.append(f"Forma recente ausente: {time_v.nome if time_v else 'visitante'}")

    # Head-to-head
    h2h = repo.head_to_head(jogo.time_mandante_id, jogo.time_visitante_id, limite=10)

    # Médias de estatísticas (para mercados secundários)
    stats_m = repo.estatisticas_de_time(jogo.time_mandante_id, COMPETICOES_STATS)
    stats_v = repo.estatisticas_de_time(jogo.time_visitante_id, COMPETICOES_STATS)

    medias_m = _calcular_medias(stats_m)
    medias_v = _calcular_medias(stats_v)

    if not medias_m.get("escanteios"):
        ausentes.append(f"Stats de escanteios ausentes: {time_m.nome if time_m else 'mandante'}")
    if not medias_v.get("escanteios"):
        ausentes.append(f"Stats de escanteios ausentes: {time_v.nome if time_v else 'visitante'}")

    return {
        "jogo": jogo,
        "time_mandante": time_m,
        "time_visitante": time_v,
        "rating_prior": {
            "mandante": prior_m,
            "visitante": prior_v,
        },
        "forma_copa": {
            "mandante": forma_copa_m,
            "visitante": forma_copa_v,
        },
        "forma_recente": {
            "mandante": forma_recente_m,
            "visitante": forma_recente_v,
        },
        "head_to_head": h2h,
        "medias_stats": {
            "mandante": medias_m,
            "visitante": medias_v,
        },
        "medias_globais": medias_globais(repo),
        "fatores_ausentes": ausentes,
    }


def _calcular_medias(stats: list[dict]) -> dict:
    """Calcula médias por jogo para cada tipo de stat."""
    if not stats:
        return {}

    campos = ["escanteios", "chutes", "chutes_no_alvo", "faltas",
              "cartoes_amarelos", "cartoes_vermelhos", "posse"]
    medias = {}
    for campo in campos:
        valores = [s[campo] for s in stats if s.get(campo) is not None]
        if valores:
            medias[campo] = round(sum(valores) / len(valores), 2)
    return medias


_MEDIAS_GLOBAIS_CACHE = None

def medias_globais(repo: Repositorio = None) -> dict:
    """
    Médias globais por time/jogo de cada mercado, sobre TODAS as estatísticas
    coletadas. Servem de prior quando falta o dado de um time específico —
    assim nenhum dado é desperdiçado e nenhum mercado fica vazio à toa.
    Cacheado (estável durante a execução).
    """
    global _MEDIAS_GLOBAIS_CACHE
    if _MEDIAS_GLOBAIS_CACHE is not None:
        return _MEDIAS_GLOBAIS_CACHE
    repo = repo or _get_repo()
    campos = ["escanteios", "chutes", "chutes_no_alvo", "faltas",
              "cartoes_amarelos", "posse"]
    out = {}
    with repo._conn() as conn:
        for campo in campos:
            row = conn.execute(
                f"SELECT AVG({campo}) FROM estatisticas_jogo WHERE {campo} IS NOT NULL"
            ).fetchone()
            if row and row[0] is not None:
                out[campo] = round(float(row[0]), 2)
    _MEDIAS_GLOBAIS_CACHE = out
    return out


# ---------------------------------------------------------------------------
# CLI para testes manuais
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    cmd = sys.argv[1] if len(sys.argv) > 1 else "inicial"

    if cmd == "inicial":
        print("Rodando ingestao_inicial (pode demorar varios minutos)...")
        resultado = ingestao_inicial()
        print("\n=== RESULTADO DA INGESTAO ===")
        for k, v in resultado.items():
            print(f"  {k}: {v}")

    elif cmd == "atualizar":
        n = atualizar_resultados_copa26()
        print(f"Copa 2026: {n} resultados atualizados")

    elif cmd == "recentes":
        print("Puxando jogos recentes (amistosos pré-Copa) via TheSportsDB...")
        r = ingerir_recentes_thesportsdb(_get_repo())
        print(f"  upsertados: {r['upsertados']} | duplicatas removidas: {r['duplicatas_removidas']}")
        if r["erros"]:
            print(f"  erros: {len(r['erros'])}")

    elif cmd == "dedup":
        n = deduplicar_jogos(_get_repo())
        print(f"Duplicatas removidas: {n}")

    elif cmd == "stats":
        print("Coletando apenas stats da API-Football (cache-first, aborta ao bater 100/dia)...")
        res = coletar_stats_api_football(_get_repo())
        print("\n=== STATS API-FOOTBALL ===")
        for k, v in res["por_competicao"].items():
            print(f"  {k}: {v} jogos com stats nesta rodada")
        print(f"  limite_diario_atingido: {res['limite_atingido']}")
        if res["erros"]:
            for e in res["erros"]:
                print(f"  ! {e}")

    elif cmd == "jogo" and len(sys.argv) > 2:
        jogo_id = int(sys.argv[2])
        pacote = pacote_jogo(jogo_id)
        print(f"\n=== PACOTE DO JOGO {jogo_id} ===")
        print(f"  Mandante:  {pacote['time_mandante'].nome if pacote['time_mandante'] else '?'}")
        print(f"  Visitante: {pacote['time_visitante'].nome if pacote['time_visitante'] else '?'}")
        print(f"  Prior mandante:  {pacote['rating_prior']['mandante']}")
        print(f"  Prior visitante: {pacote['rating_prior']['visitante']}")
        print(f"  Forma recente mandante:  {len(pacote['forma_recente']['mandante'])} jogos")
        print(f"  Forma recente visitante: {len(pacote['forma_recente']['visitante'])} jogos")
        print(f"  Head-to-head: {len(pacote['head_to_head'])} jogos")
        print(f"  Fatores ausentes: {pacote['fatores_ausentes']}")

    elif cmd == "listar":
        repo = _get_repo()
        jogos = repo.listar_jogos_copa26()
        print(f"\n=== {len(jogos)} JOGOS COPA 2026 ===")
        for j in jogos[:20]:
            m = repo.buscar_time(j.time_mandante_id)
            v = repo.buscar_time(j.time_visitante_id)
            nm = m.nome if m else "?"
            nv = v.nome if v else "?"
            placar = f"{j.placar_mandante}-{j.placar_visitante}" if j.placar_mandante is not None else "vs"
            print(f"  [{j.id:3d}] {j.data} | {nm} {placar} {nv} | Grupo {j.grupo}")
        if len(jogos) > 20:
            print(f"  ... e mais {len(jogos) - 20} jogos")
    else:
        print("Uso: python -m src.dados.ingestao [inicial|stats|recentes|dedup|atualizar|listar|jogo <id>]")
