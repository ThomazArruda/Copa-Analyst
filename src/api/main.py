"""
Copa Analyst — FastAPI backend.
Expõe toda a lógica Python existente como uma API REST.
"""
import os
import sys
import json
import base64
import secrets
import shutil
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
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
# Autenticação básica (deploy público) — ativa apenas se APP_PASSWORD existir.
# Protege UI + API com um usuário/senha compartilhado (grupo fechado).
# Local (sem APP_PASSWORD) → desativada.
# ---------------------------------------------------------------------------

APP_USER = os.getenv("APP_USER", "copa")
APP_PASSWORD = os.getenv("APP_PASSWORD")


@app.middleware("http")
async def _basic_auth(request, call_next):
    if not APP_PASSWORD:
        return await call_next(request)
    # Health check do host nunca exige senha (senão o deploy é marcado unhealthy)
    if request.url.path == "/healthz":
        return await call_next(request)
    from starlette.responses import Response
    header = request.headers.get("authorization", "")
    if header.startswith("Basic "):
        try:
            user, _, pw = base64.b64decode(header[6:]).decode("utf-8").partition(":")
            if (secrets.compare_digest(user, APP_USER)
                    and secrets.compare_digest(pw, APP_PASSWORD)):
                return await call_next(request)
        except Exception:
            pass
    return Response(
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="Copa Analyst"'},
        content="Autenticação necessária.",
    )


@app.on_event("startup")
def _semear_banco():
    """Em deploy com volume vazio, copia o banco-semente embarcado na imagem
    para COPA_DB_PATH (uma vez). Local/dev: não faz nada se o banco já existe."""
    db_path = Path(os.getenv("COPA_DB_PATH", "dados/copa_analyst.db"))
    seed = _root / "deploy" / "seed_db" / "copa_analyst.db"
    if not db_path.exists() and seed.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(seed, db_path)
        logger.warning("Banco semeado a partir de %s → %s", seed, db_path)

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
                    "parcial": getattr(m, "parcial", False),
                    "nota": getattr(m, "nota", ""),
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

@app.get("/healthz")
def healthz():
    """Health check do host (sem autenticação)."""
    return {"ok": True}


# ---------------------------------------------------------------------------
# /api/bolao — simulação Monte Carlo do torneio (grupos + mata-mata)
# ---------------------------------------------------------------------------

_bolao_cache = None

@app.get("/api/bolao")
def bolao(refresh: bool = False, n: int = 10000):
    """Simula o torneio inteiro a partir das previsões do modelo. Cacheado
    em memória (recalcula com ?refresh=true)."""
    global _bolao_cache
    if _bolao_cache is None or refresh:
        from src.modelos.bolao import simular_torneio, bracket_provavel
        res = simular_torneio(get_repo(), n=n)
        try:
            res["bracket"] = bracket_provavel(get_repo())
        except Exception:
            logger.exception("Falha ao montar bracket")
            res["bracket"] = None
        _bolao_cache = res
    return _bolao_cache


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
    """
    Painel de calibração real (PRD Seção 9): Brier score + log-loss por mercado,
    apenas sobre relatórios oficiais com resultado_real. Mantém as chaves antigas
    (total_avaliados, relatorios_oficiais, msg) para compatibilidade com o frontend.
    """
    from src.validacao.calibracao import calcular_calibracao, pontos_calibracao

    repo = get_repo()
    try:
        painel = calcular_calibracao(repo)
        pontos = pontos_calibracao(repo)

        total = painel.total_previsoes_avaliadas
        if total == 0:
            msg = "Painel ficará ativo após os primeiros jogos da Copa."
        else:
            msg = painel.aviso_ruido or None

        return {
            # compatibilidade com a UI atual
            "total_avaliados": total,
            "relatorios_oficiais": painel.total_relatorios_oficiais,
            "msg": msg,
            # métricas reais (PRD 9.3)
            "por_mercado": [
                {
                    "mercado": m.mercado,
                    "n": m.n,
                    "brier_score": m.brier_score,
                    "log_loss": m.log_loss,
                    "acerto_binario": m.acerto_binario,  # display only — PRD 9.3
                    "ruido_alto": m.ruido_alto,
                    "alerta_leakage": m.alerta_leakage,
                }
                for m in painel.por_mercado
            ],
            "aviso_ruido": painel.aviso_ruido or None,
            "alerta_leakage": painel.alerta_leakage or None,
            "pontos_calibracao": pontos,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# /api/jogos/{id}/gerar-relatorio — dispara análise completa com Claude
# ---------------------------------------------------------------------------

_gerando: dict[int, bool] = {}
_erro_geracao: dict[int, str] = {}  # último erro de geração por jogo (UI mostra)

@app.post("/api/jogos/{jogo_id}/gerar-relatorio")
def gerar_relatorio(jogo_id: int, background_tasks: BackgroundTasks, modelo: str = None):
    """Dispara a análise com Claude. `modelo` opcional: 'opus' (jogos importantes)
    ou 'sonnet' (default). Sem o parâmetro, usa o default do ambiente."""
    if _gerando.get(jogo_id):
        return {"ok": False, "msg": "Análise já em andamento para este jogo."}
    _gerando[jogo_id] = True
    _erro_geracao.pop(jogo_id, None)

    def _run():
        try:
            from src.ia.sintese import analisar_jogo
            repo = get_repo()
            res = analisar_jogo(jogo_id, repo, modelo=modelo)
            if not res.get("sucesso"):
                erros = res.get("erros") or ["falha desconhecida na síntese"]
                _erro_geracao[jogo_id] = "; ".join(erros)
                logger.error("Análise do jogo %d falhou: %s", jogo_id, erros)
        except Exception as e:
            logger.exception("Erro na análise do jogo %d", jogo_id)
            _erro_geracao[jogo_id] = f"Erro inesperado: {e}"
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
        erro = _erro_geracao.get(jogo_id)

        if row is None:
            return {"ok": True, "relatorio": None, "historico": [], "gerando": gerando, "erro": erro}

        conteudo = json.loads(row["conteudo"]) if row["conteudo"] else {}
        return {
            "ok": True,
            "gerando": gerando,
            "erro": erro,
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
    """Marca relatório como oficial com guarda anti-leakage (PRD 9.1):
    recusa se o relatório foi gerado após o apito inicial."""
    try:
        from src.relatorio.oficial import marcar_oficial_seguro
        repo = get_repo()
        res = marcar_oficial_seguro(repo, relatorio_id)
        return res  # {ok, motivo, ...} — ok=False quando violaria anti-leakage
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/marcar-oficiais-automatico")
def marcar_oficiais_automatico_endpoint(data: str = None):
    """Fixa, para cada jogo já iniciado, o último relatório gerado antes do apito
    como oficial (PRD 9.1). Opcional: limitar a uma data (YYYY-MM-DD)."""
    try:
        from src.relatorio.oficial import marcar_oficiais_automatico
        repo = get_repo()
        return {"ok": True, **marcar_oficiais_automatico(repo, data)}
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


# ---------------------------------------------------------------------------
# Frontend estático (deploy simples: um único uvicorn serve API + UI)
# Servido apenas se `web/dist` existir (rodar `npm run build` em web/).
# Registrado por último → as rotas /api/* têm precedência.
# ---------------------------------------------------------------------------

_web_dist = _root / "web" / "dist"
if _web_dist.exists():
    _assets = _web_dist / "assets"
    if _assets.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/{full_path:path}")
    def servir_spa(full_path: str):
        """Serve arquivos de web/dist; faz fallback para index.html (SPA client-side routing).
        Não intercepta /api (rotas registradas antes têm precedência)."""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidato = _web_dist / full_path
        if full_path and candidato.is_file():
            return FileResponse(str(candidato))
        return FileResponse(str(_web_dist / "index.html"))
else:
    logger.warning("web/dist não encontrado — rode 'npm run build' em web/ para servir a UI pelo FastAPI.")
