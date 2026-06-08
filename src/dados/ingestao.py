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
from src.dados.thesportsdb import ClienteTheSportsDB
from src.dados.wikipedia_scraper import ScraperWikipedia
from src.modelos.rating_prior import RatingPrior

load_dotenv()
logger = logging.getLogger(__name__)

# Competições usadas para calcular forma recente (Decisão 11)
COMPETICOES_FORMA = [
    "copa_2026",
    "copa_2022",
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
                relatorio["stats_api_football"][competicao_key] = stats_ok
                logger.info("%s: %d jogos com stats", competicao_key, stats_ok)
            if af.limite_diario_atingido:
                logger.info("Coleta de stats interrompida: limite diário da API-Football atingido.")
                relatorio["erros"].append("API-Football: limite diário (100/dia) atingido — coleta parcial.")
        except Exception as e:
            msg = f"API-Football falhou: {e}"
            logger.error(msg)
            relatorio["erros"].append(msg)
    else:
        logger.info("--- [5/5] API-Football pulado (pular_api_football=True) ---")

    return relatorio


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

def atualizar_resultados_copa26() -> int:
    """
    Puxa resultados mais recentes da Copa 2026 via TheSportsDB.
    Retorna número de jogos atualizados.
    """
    repo = _get_repo()
    tsdb = ClienteTheSportsDB(repo)
    resultados = tsdb.buscar_resultados_copa26()
    atualizados = 0

    for evento in resultados:
        nome_home = evento.get("strHomeTeam", "")
        nome_away = evento.get("strAwayTeam", "")
        if not nome_home or not nome_away:
            continue

        id_home = repo.upsert_time(Time(id=None, nome=nome_home))
        id_away = repo.upsert_time(Time(id=None, nome=nome_away))

        data_str = evento.get("dateEvent", "")
        hora_str = evento.get("strTime", "")
        hora_utc = hora_str[:5] if hora_str else None

        jogo = Jogo(
            id=None,
            competicao="copa_2026",
            data=data_str,
            hora_utc=hora_utc,
            time_mandante_id=id_home,
            time_visitante_id=id_away,
            campo_neutro=1,
            placar_mandante=int(evento["intHomeScore"]) if evento.get("intHomeScore") is not None else None,
            placar_visitante=int(evento["intAwayScore"]) if evento.get("intAwayScore") is not None else None,
            id_externo=str(evento.get("idEvent", "")),
            fonte="thesportsdb",
        )
        repo.upsert_jogo(jogo)
        atualizados += 1

    logger.info("Copa 2026: %d resultados atualizados via TheSportsDB", atualizados)
    return atualizados


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

    # Forma recente (todas as competições disponíveis)
    forma_recente_m = repo.jogos_de_time(jogo.time_mandante_id, COMPETICOES_FORMA, limite=10)
    forma_recente_v = repo.jogos_de_time(jogo.time_visitante_id, COMPETICOES_FORMA, limite=10)
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
        print("Uso: python -m src.dados.ingestao [inicial|atualizar|listar|jogo <id>]")
