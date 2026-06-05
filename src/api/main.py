"""
Copa Analyst — FastAPI backend.
Expõe toda a lógica Python existente como uma API REST.
"""
import os
import sys
import logging
from datetime import date, datetime
from pathlib import Path

# Garante que a raiz está no sys.path
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

app = FastAPI(title="Copa Analyst API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Dependências compartilhadas
# ---------------------------------------------------------------------------

_repo = None

def get_repo():
    global _repo
    if _repo is None:
        from src.dados.ingestao import _get_repo
        _repo = _get_repo()
    return _repo


# ---------------------------------------------------------------------------
# /api/jogos — lista jogos Copa 2026
# ---------------------------------------------------------------------------

@app.get("/api/jogos")
def listar_jogos(data: str = None):
    """Retorna jogos da Copa 2026, opcionalmente filtrados por data (YYYY-MM-DD)."""
    repo = get_repo()
    jogos = repo.listar_jogos_copa26()
    result = []
    for j in jogos:
        tm = repo.buscar_time(j.time_mandante_id)
        tv = repo.buscar_time(j.time_visitante_id)
        item = {
            "id": j.id,
            "data": j.data,
            "hora": j.hora_utc or "",
            "mandante": tm.nome if tm else "?",
            "visitante": tv.nome if tv else "?",
            "mandante_elo": round(tm.rating_prior, 1) if tm and tm.rating_prior else None,
            "visitante_elo": round(tv.rating_prior, 1) if tv and tv.rating_prior else None,
            "grupo": j.grupo or "?",
            "fase": j.fase or "grupo",
            "cidade": j.cidade or "",
            "placar_m": j.placar_mandante,
            "placar_v": j.placar_visitante,
        }
        if data is None or j.data == data:
            result.append(item)
    return result


# ---------------------------------------------------------------------------
# /api/jogos/datas — datas disponíveis
# ---------------------------------------------------------------------------

@app.get("/api/jogos/datas")
def listar_datas():
    repo = get_repo()
    jogos = repo.listar_jogos_copa26()
    datas = sorted(set(j.data for j in jogos))
    return datas


# ---------------------------------------------------------------------------
# /api/jogos/{id}/previsao — previsão rápida Dixon-Coles
# ---------------------------------------------------------------------------

@app.get("/api/jogos/{jogo_id}/previsao")
def previsao_rapida(jogo_id: int):
    from src.dados.ingestao import pacote_jogo
    from src.modelos.dixon_coles import DixonColes
    from src.relatorio.email_diario import _tendencias

    repo = get_repo()
    try:
        pacote = pacote_jogo(jogo_id)
        dc = DixonColes(repo)
        prev = dc.prever_por_pacote(pacote)
        tm = pacote["time_mandante"]
        tv = pacote["time_visitante"]
        tags = _tendencias(prev, tm.nome if tm else "", tv.nome if tv else "")

        # Mercados over/under
        over = {str(k): round(v, 3) for k, v in prev.prob_over.items()}

        return {
            "ok": True,
            "mandante": tm.nome if tm else "?",
            "visitante": tv.nome if tv else "?",
            "prob_vitoria_m": round(prev.prob_vitoria_m, 3),
            "prob_empate": round(prev.prob_empate, 3),
            "prob_vitoria_v": round(prev.prob_vitoria_v, 3),
            "gols_esperados_m": round(prev.lambda_m, 2),
            "gols_esperados_v": round(prev.mu_v, 2),
            "prob_over": over,
            "cold_start": prev.cold_start,
            "tags": tags,
            "fatores_ausentes": pacote["fatores_ausentes"],
        }
    except Exception as e:
        logger.exception("Erro na previsão do jogo %d", jogo_id)
        return {"ok": False, "erro": str(e)}


# ---------------------------------------------------------------------------
# /api/jogos/{id}/analise — pacote completo de dados
# ---------------------------------------------------------------------------

@app.get("/api/jogos/{jogo_id}/analise")
def analise_completa(jogo_id: int):
    from src.dados.ingestao import pacote_jogo
    from src.modelos.dixon_coles import DixonColes
    from src.modelos.mercados import calcular_mercados_secundarios

    repo = get_repo()
    try:
        pacote = pacote_jogo(jogo_id)
        dc = DixonColes(repo)
        prev = dc.prever_por_pacote(pacote)
        mercados = calcular_mercados_secundarios(pacote)

        def _jogo_fmt(j, repo):
            tm = repo.buscar_time(j.time_mandante_id)
            tv = repo.buscar_time(j.time_visitante_id)
            return {
                "data": j.data,
                "mandante": tm.nome if tm else "?",
                "visitante": tv.nome if tv else "?",
                "placar_m": j.placar_mandante,
                "placar_v": j.placar_visitante,
                "competicao": j.competicao,
            }

        return {
            "ok": True,
            "jogo": {
                "id": jogo_id,
                "data": pacote["jogo"].data,
                "hora": pacote["jogo"].hora_utc,
                "cidade": pacote["jogo"].cidade,
                "grupo": pacote["jogo"].grupo,
                "fase": pacote["jogo"].fase,
            },
            "mandante": {
                "nome": pacote["time_mandante"].nome if pacote["time_mandante"] else "?",
                "elo": round(pacote["time_mandante"].rating_prior, 1)
                       if pacote["time_mandante"] and pacote["time_mandante"].rating_prior else None,
            },
            "visitante": {
                "nome": pacote["time_visitante"].nome if pacote["time_visitante"] else "?",
                "elo": round(pacote["time_visitante"].rating_prior, 1)
                       if pacote["time_visitante"] and pacote["time_visitante"].rating_prior else None,
            },
            "previsao": {
                "prob_vitoria_m": round(prev.prob_vitoria_m, 3),
                "prob_empate": round(prev.prob_empate, 3),
                "prob_vitoria_v": round(prev.prob_vitoria_v, 3),
                "gols_esperados_m": round(prev.lambda_m, 2),
                "gols_esperados_v": round(prev.mu_v, 2),
                "prob_over": {str(k): round(v, 3) for k, v in prev.prob_over.items()},
                "cold_start": prev.cold_start,
            },
            "mercados": {
                k: {
                    "media_esperada": m.media_esperada,
                    "prob_linhas": {str(kk): vv for kk, vv in m.prob_linhas.items()},
                    "intervalo_80pct": list(m.intervalo_80pct),
                    "ausente": m.ausente,
                }
                for k, m in mercados.items()
            },
            "forma_recente": {
                "mandante": [_jogo_fmt(j, repo) for j in pacote["forma_recente"]["mandante"][:5]],
                "visitante": [_jogo_fmt(j, repo) for j in pacote["forma_recente"]["visitante"][:5]],
            },
            "head_to_head": [_jogo_fmt(j, repo) for j in pacote["head_to_head"][:5]],
            "fatores_ausentes": pacote["fatores_ausentes"],
        }
    except Exception as e:
        logger.exception("Erro na análise do jogo %d", jogo_id)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# /api/status — status do banco
# ---------------------------------------------------------------------------

@app.get("/api/status")
def status_banco():
    import sqlite3
    db_path = os.getenv("COPA_DB_PATH", "dados/copa_analyst.db")
    try:
        conn = sqlite3.connect(db_path)
        jogos_total = conn.execute("SELECT COUNT(*) FROM jogos").fetchone()[0]
        copa26 = conn.execute(
            "SELECT COUNT(*) FROM jogos WHERE competicao='copa_2026'"
        ).fetchone()[0]
        relatorios = conn.execute("SELECT COUNT(*) FROM relatorios").fetchone()[0]
        previsoes = conn.execute(
            "SELECT COUNT(*) FROM relatorios WHERE eh_relatorio_oficial=1"
        ).fetchone()[0]
        times = conn.execute("SELECT COUNT(*) FROM times").fetchone()[0]
        conn.close()
        return {
            "jogos_total": jogos_total,
            "copa26_fixtures": copa26,
            "relatorios": relatorios,
            "previsoes_oficiais": previsoes,
            "times": times,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# /api/atualizar — dispara ingestão de resultados mais recentes
# ---------------------------------------------------------------------------

_atualizando = False

@app.post("/api/atualizar")
def atualizar_resultados(background_tasks: BackgroundTasks):
    global _atualizando
    if _atualizando:
        return {"ok": False, "msg": "Atualização já em andamento."}
    _atualizando = True

    def _run():
        global _atualizando
        try:
            from src.dados.ingestao import atualizar_resultados_copa26
            n = atualizar_resultados_copa26()
            logger.info("Copa 2026: %d resultados atualizados", n)
        finally:
            _atualizando = False

    background_tasks.add_task(_run)
    return {"ok": True, "msg": "Atualização iniciada em background."}


@app.post("/api/recalcular-elo")
def recalcular_elo():
    try:
        from src.modelos.rating_prior import RatingPrior
        repo = get_repo()
        n = RatingPrior(repo).calcular_e_salvar()
        return {"ok": True, "times_atualizados": n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# /api/calibracao — métricas de calibração
# ---------------------------------------------------------------------------

@app.get("/api/calibracao")
def calibracao():
    import sqlite3
    db_path = os.getenv("COPA_DB_PATH", "dados/copa_analyst.db")
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        # Relatórios com resultado disponível
        rows = conn.execute("""
            SELECT r.id, r.jogo_id, r.gerado_em, r.conteudo,
                   j.placar_mandante, j.placar_visitante, j.data
            FROM relatorios r
            JOIN jogos j ON j.id = r.jogo_id
            WHERE r.eh_relatorio_oficial = 1
              AND j.placar_mandante IS NOT NULL
            ORDER BY j.data DESC
            LIMIT 50
        """).fetchall()
        conn.close()
        total = len(rows)
        return {
            "total_avaliados": total,
            "relatorios_oficiais": total,
            "msg": "Painel ficará ativo após os primeiros jogos da Copa." if total == 0 else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# /api/jogos/{id}/gerar-relatorio — dispara análise completa com Claude
# ---------------------------------------------------------------------------

_gerando: dict[int, bool] = {}

@app.post("/api/jogos/{jogo_id}/gerar-relatorio")
def gerar_relatorio(jogo_id: int, background_tasks: BackgroundTasks):
    if _gerando.get(jogo_id):
        return {"ok": False, "msg": "Análise já em andamento para este jogo."}
    _gerando[jogo_id] = True

    def _run():
        try:
            from src.ia.sintese import analisar_jogo
            repo = get_repo()
            analisar_jogo(jogo_id, repo)
        except Exception:
            logger.exception("Erro na análise do jogo %d", jogo_id)
        finally:
            _gerando.pop(jogo_id, None)

    background_tasks.add_task(_run)
    return {"ok": True, "msg": "Análise iniciada. Aguarde ~30–60s e recarregue."}


@app.get("/api/jogos/{jogo_id}/relatorio")
def buscar_relatorio(jogo_id: int):
    import sqlite3
    db_path = os.getenv("COPA_DB_PATH", "dados/copa_analyst.db")
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("""
            SELECT id, jogo_id, gerado_em, prompt_versao, modelo_versao,
                   conteudo, fatores_avaliados, fatores_ausentes, eh_relatorio_oficial
            FROM relatorios
            WHERE jogo_id = ?
            ORDER BY gerado_em DESC
            LIMIT 1
        """, (jogo_id,)).fetchone()

        historico = conn.execute("""
            SELECT id, gerado_em, eh_relatorio_oficial
            FROM relatorios
            WHERE jogo_id = ?
            ORDER BY gerado_em DESC
        """, (jogo_id,)).fetchall()
        conn.close()

        gerando = _gerando.get(jogo_id, False)

        if row is None:
            return {"ok": True, "relatorio": None, "historico": [], "gerando": gerando}

        conteudo = json.loads(row["conteudo"]) if row["conteudo"] else {}
        return {
            "ok": True,
            "gerando": gerando,
            "relatorio": {
                "id": row["id"],
                "jogo_id": row["jogo_id"],
                "gerado_em": row["gerado_em"],
                "prompt_versao": row["prompt_versao"],
                "modelo_versao": row["modelo_versao"],
                "eh_relatorio_oficial": bool(row["eh_relatorio_oficial"]),
                **conteudo,
            },
            "historico": [
                {"id": h["id"], "gerado_em": h["gerado_em"], "oficial": bool(h["eh_relatorio_oficial"])}
                for h in historico
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/relatorios/{relatorio_id}/marcar-oficial")
def marcar_oficial(relatorio_id: int):
    try:
        repo = get_repo()
        repo.marcar_relatorio_oficial(relatorio_id)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# /api/top-elo — top 10 times por rating Elo
# ---------------------------------------------------------------------------

@app.get("/api/top-elo")
def top_elo(n: int = 10):
    repo = get_repo()
    times = repo.listar_times()
    com_elo = [t for t in times if t.rating_prior is not None]
    com_elo.sort(key=lambda t: t.rating_prior, reverse=True)
    return [
        {"nome": t.nome, "elo": round(t.rating_prior, 1), "grupo": t.grupo_copa26}
        for t in com_elo[:n]
    ]
