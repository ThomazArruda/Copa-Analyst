"""
Métricas de calibração: Brier score e log-loss (PRD Seção 9).

Regras:
- Calcular APENAS sobre previsões do relatório oficial (eh_relatorio_oficial=1)
- Nunca usar `acertou` como métrica — Brier/log-loss são as métricas reais
- Aviso explícito de ruído estatístico nas primeiras rodadas (PRD 9.5)
- N < 20 previsões → resultados não são acionáveis

PRD 9.2: se acurácia de resultado > 60%, presumir leakage e auditar.
"""

import math
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Amostras mínimas para resultados serem informativos (PRD 9.5)
MIN_AMOSTRAS_CONFIAVEL = 20
LIMIAR_LEAKAGE_RESULTADO = 0.60  # PRD 9.2


@dataclass
class MetricasMercado:
    mercado: str
    n: int                          # total de previsões avaliadas
    brier_score: float              # médio (0=perfeito, 1=pior)
    log_loss: float                 # médio
    acerto_binario: float           # display only — PRD proíbe usar como métrica
    ruido_alto: bool                # True se n < MIN_AMOSTRAS_CONFIAVEL
    alerta_leakage: bool = False    # True se resultado > 60%


@dataclass
class PainelCalibracao:
    total_relatorios_oficiais: int
    total_previsoes_avaliadas: int
    por_mercado: list[MetricasMercado] = field(default_factory=list)
    aviso_ruido: str = ""
    alerta_leakage: str = ""


def _brier_score(prob: float, acertou: bool) -> float:
    """Brier score para uma previsão binária: (p - resultado)²"""
    resultado = 1.0 if acertou else 0.0
    return (prob - resultado) ** 2


def _log_loss(prob: float, acertou: bool) -> float:
    """Log-loss: -log(p) se acertou, -log(1-p) se errou."""
    eps = 1e-9
    p = max(min(prob, 1 - eps), eps)
    return -math.log(p) if acertou else -math.log(1 - p)


def _resultado_real_bateu_previsao(resultado_real: str, previsao: str) -> bool:
    """Verifica se o resultado real bate com a previsão (comparação textual normalizada)."""
    return resultado_real.strip().lower() == previsao.strip().lower()


def calcular_calibracao(repo) -> PainelCalibracao:
    """
    Calcula métricas de calibração para todas as previsões com resultado_real.
    Apenas relatórios oficiais (PRD 9.1).
    """
    with repo._conn() as conn:
        # Apenas previsões do relatório oficial com resultado_real preenchido
        rows = conn.execute("""
            SELECT p.mercado, p.previsao, p.probabilidade_estimada, p.resultado_real
            FROM previsoes p
            JOIN relatorios r ON r.id = p.relatorio_id
            WHERE r.eh_relatorio_oficial = 1
              AND p.resultado_real IS NOT NULL
              AND p.probabilidade_estimada IS NOT NULL
        """).fetchall()

        n_oficiais = conn.execute(
            "SELECT COUNT(*) FROM relatorios WHERE eh_relatorio_oficial = 1"
        ).fetchone()[0]

    if not rows:
        return PainelCalibracao(
            total_relatorios_oficiais=n_oficiais,
            total_previsoes_avaliadas=0,
            aviso_ruido="Nenhuma previsão com resultado disponível ainda.",
        )

    # Agrupar por mercado
    por_mercado: dict[str, list] = {}
    for row in rows:
        mercado = row["mercado"]
        if mercado not in por_mercado:
            por_mercado[mercado] = []
        por_mercado[mercado].append(row)

    metricas = []
    alerta_leakage = ""

    for mercado, previsoes in por_mercado.items():
        n = len(previsoes)
        brier_vals = []
        ll_vals = []
        acertos = 0

        for p in previsoes:
            prob = p["probabilidade_estimada"]
            acertou = _resultado_real_bateu_previsao(p["resultado_real"], p["previsao"])
            if acertou:
                acertos += 1
            brier_vals.append(_brier_score(prob, acertou))
            ll_vals.append(_log_loss(prob, acertou))

        brier_medio = sum(brier_vals) / n
        ll_medio = sum(ll_vals) / n
        acerto_pct = acertos / n

        # Verificar leakage (PRD 9.2)
        leakage = False
        if mercado == "resultado" and acerto_pct > LIMIAR_LEAKAGE_RESULTADO:
            leakage = True
            alerta_leakage = (
                f"ALERTA: acerto de resultado = {acerto_pct:.0%} > {LIMIAR_LEAKAGE_RESULTADO:.0%}. "
                "Verificar data leakage antes de interpretar como sucesso do modelo. (PRD 9.2)"
            )
            logger.warning(alerta_leakage)

        metricas.append(MetricasMercado(
            mercado=mercado,
            n=n,
            brier_score=round(brier_medio, 4),
            log_loss=round(ll_medio, 4),
            acerto_binario=round(acerto_pct, 3),
            ruido_alto=(n < MIN_AMOSTRAS_CONFIAVEL),
            alerta_leakage=leakage,
        ))

    # Ordenar: resultado primeiro, depois os outros
    ordem = ["resultado", "total_gols", "ambas_marcam", "escanteios",
             "cartoes_amarelos", "faltas", "chutes_time"]
    metricas.sort(key=lambda m: ordem.index(m.mercado) if m.mercado in ordem else 99)

    total = len(rows)
    aviso = ""
    if total < MIN_AMOSTRAS_CONFIAVEL:
        aviso = (
            f"Apenas {total} previsão(ões) avaliada(s). "
            "Com menos de 20 amostras, Brier/log-loss são estatisticamente barulhentos "
            "e não devem motivar mudanças no modelo. (PRD 9.5)"
        )

    return PainelCalibracao(
        total_relatorios_oficiais=n_oficiais,
        total_previsoes_avaliadas=total,
        por_mercado=metricas,
        aviso_ruido=aviso,
        alerta_leakage=alerta_leakage,
    )


def pontos_calibracao(repo) -> list[dict]:
    """
    Retorna pares (probabilidade_prevista, frequência_real) para gráfico de calibração.
    Agrupa previsões em bins de 10pp.
    """
    with repo._conn() as conn:
        rows = conn.execute("""
            SELECT p.probabilidade_estimada, p.resultado_real, p.previsao
            FROM previsoes p
            JOIN relatorios r ON r.id = p.relatorio_id
            WHERE r.eh_relatorio_oficial = 1
              AND p.resultado_real IS NOT NULL
              AND p.probabilidade_estimada IS NOT NULL
        """).fetchall()

    if not rows:
        return []

    bins: dict[float, list[bool]] = {}
    for row in rows:
        prob = row["probabilidade_estimada"]
        acertou = _resultado_real_bateu_previsao(row["resultado_real"], row["previsao"])
        bin_key = round(round(prob * 10) / 10, 1)
        bins.setdefault(bin_key, []).append(acertou)

    return sorted([
        {"prob_prevista": k, "freq_real": sum(v) / len(v), "n": len(v)}
        for k, v in bins.items()
    ], key=lambda x: x["prob_prevista"])
