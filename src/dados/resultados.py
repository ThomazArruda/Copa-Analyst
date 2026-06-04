"""
Atualização automática de resultado_real após cada jogo (PRD Seção 9.4).
Fonte primária: TheSportsDB (grátis, atualiza automaticamente).
Fallback: entrada manual via interface.

resultado_real preenche a tabela `previsoes` com o que de fato aconteceu,
permitindo o cálculo de Brier/log-loss na Fase 6.
"""

import logging
from src.db.repositorio import Repositorio
from src.dados.thesportsdb import ClienteTheSportsDB

logger = logging.getLogger(__name__)


def _resultado_de_placar(placar_m: int, placar_v: int, mercado: str, previsao: str) -> str | None:
    """
    Converte placar real no resultado para comparar com a previsão de um mercado.
    Retorna a string do resultado real (ex: 'vitoria mandante', 'over 2.5', 'sim').
    """
    if mercado == "resultado":
        if placar_m > placar_v:
            return "vitoria mandante"
        elif placar_m == placar_v:
            return "empate"
        else:
            return "vitoria visitante"

    elif mercado == "total_gols":
        total = placar_m + placar_v
        # Detectar linha da previsão (ex: "over 2.5" → linha=2.5)
        import re
        m = re.search(r"(\d+\.?\d*)", previsao)
        if not m:
            return None
        linha = float(m.group(1))
        if "over" in previsao.lower() or "mais" in previsao.lower():
            return "over" if total > linha else "under"
        else:
            return "under" if total <= linha else "over"

    elif mercado == "ambas_marcam":
        return "sim" if placar_m > 0 and placar_v > 0 else "nao"

    # Para escanteios, cartões, faltas, chutes → não podemos derivar do placar
    return None


def preencher_resultado_real_jogo(
    jogo_id: int, placar_m: int, placar_v: int, repo: Repositorio
) -> int:
    """
    Preenche resultado_real em todas as previsoes do relatório oficial de um jogo.
    Retorna número de previsões atualizadas.
    """
    atualizadas = 0
    with repo._conn() as conn:
        # Só atualiza previsões do relatório oficial
        previsoes = conn.execute("""
            SELECT p.id, p.mercado, p.previsao
            FROM previsoes p
            JOIN relatorios r ON r.id = p.relatorio_id
            WHERE p.jogo_id = ? AND r.eh_relatorio_oficial = 1
              AND p.resultado_real IS NULL
        """, (jogo_id,)).fetchall()

        for prev in previsoes:
            resultado = _resultado_de_placar(
                placar_m, placar_v, prev["mercado"], prev["previsao"]
            )
            if resultado:
                conn.execute(
                    "UPDATE previsoes SET resultado_real = ? WHERE id = ?",
                    (resultado, prev["id"])
                )
                atualizadas += 1

        # Atualizar placar no jogo
        conn.execute(
            "UPDATE jogos SET placar_mandante=?, placar_visitante=? WHERE id=?",
            (placar_m, placar_v, jogo_id)
        )

    logger.info("Jogo %d: %d previsões com resultado_real preenchido", jogo_id, atualizadas)
    return atualizadas


def atualizar_resultados_automatico(repo: Repositorio) -> dict:
    """
    Puxar resultados finalizados da Copa 2026 via TheSportsDB e
    preencher resultado_real nas previsões correspondentes.
    """
    tsdb = ClienteTheSportsDB(repo)
    eventos = tsdb.buscar_resultados_copa26()

    total_jogos = 0
    total_previsoes = 0

    for evento in eventos:
        nome_m = evento.get("strHomeTeam", "")
        nome_v = evento.get("strAwayTeam", "")
        placar_m = evento.get("intHomeScore")
        placar_v = evento.get("intAwayScore")

        if placar_m is None or placar_v is None:
            continue

        # Encontrar jogo no banco pelo nome dos times
        time_m = repo.buscar_time_por_nome(nome_m)
        time_v = repo.buscar_time_por_nome(nome_v)
        if not time_m or not time_v:
            continue

        jogos = repo.head_to_head(time_m.id, time_v.id, limite=3)
        jogo_copa = next(
            (j for j in jogos if j.competicao == "copa_2026"), None
        )
        if not jogo_copa:
            continue

        n = preencher_resultado_real_jogo(
            jogo_copa.id, int(placar_m), int(placar_v), repo
        )
        total_jogos += 1
        total_previsoes += n

    logger.info(
        "Auto-update: %d jogos processados, %d previsoes com resultado",
        total_jogos, total_previsoes
    )
    return {"jogos": total_jogos, "previsoes": total_previsoes}
