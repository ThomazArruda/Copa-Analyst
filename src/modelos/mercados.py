"""
Distribuições para mercados secundários: escanteios, cartões, faltas, chutes.
PRD Seção 7.2.

Método: Poisson sobre médias históricas das seleções.
Cartões e faltas incorporam perfil disciplinar do árbitro quando disponível.
Se não há dados de médias → retorna None (declarado como ausente, PRD 2.4).
"""

import math
import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.stats import poisson

logger = logging.getLogger(__name__)

MAX_EVENTOS = 30  # truncamento para distribuição de escanteios/chutes/faltas


@dataclass
class PrevisaoMercadoSecundario:
    """Previsão para um mercado secundário específico."""
    mercado: str              # 'escanteios' | 'cartoes_amarelos' | 'faltas' | 'chutes'
    media_esperada: float     # λ do modelo Poisson
    # Probabilidades para linhas comuns
    prob_linhas: dict = field(default_factory=dict)  # {linha: p_over}
    intervalo_80pct: tuple = (0, 0)  # intervalo de credibilidade 80%
    n_jogos_m: int = 0         # jogos com dados do mandante
    n_jogos_v: int = 0         # jogos com dados do visitante
    ausente: bool = False      # True = não há dados suficientes


def _calcular_distribuicao(media: float, linhas: list[float]) -> dict:
    """
    Calcula P(X > linha) para uma variável Poisson(media).
    """
    probs = {}
    for linha in linhas:
        p_over = float(1 - poisson.cdf(math.floor(linha), media))
        probs[linha] = round(p_over, 4)
    return probs


def _intervalo_credibilidade(media: float, pct: float = 0.80) -> tuple[int, int]:
    """Intervalo central com cobertura ≥ pct para Poisson(media)."""
    alpha = (1 - pct) / 2
    lo = int(poisson.ppf(alpha, media))
    hi = int(poisson.ppf(1 - alpha, media))
    return lo, hi


def _media_com_ajuste_arbitro(
    media_base: float,
    fator_arbitro: Optional[float],
) -> float:
    """
    Ajusta a média pelo perfil disciplinar do árbitro (quando disponível).
    fator_arbitro: razão de cartões/faltas do árbitro vs média global.
    Ex: fator=1.3 → árbitro apita 30% mais faltas que a média.
    """
    if fator_arbitro is None:
        return media_base
    return media_base * fator_arbitro


# ---------------------------------------------------------------------------
# Funções públicas por mercado
# ---------------------------------------------------------------------------

def prever_escanteios(
    medias_m: dict, medias_v: dict
) -> PrevisaoMercadoSecundario:
    """
    Escanteios totais no jogo: soma das médias de cada time.
    Linhas típicas: 7.5, 8.5, 9.5, 10.5, 11.5
    """
    val_m = medias_m.get("escanteios")
    val_v = medias_v.get("escanteios")

    if val_m is None or val_v is None:
        return PrevisaoMercadoSecundario(
            mercado="escanteios", media_esperada=0.0,
            ausente=True,
        )

    media = val_m + val_v
    linhas = [7.5, 8.5, 9.5, 10.5, 11.5]

    return PrevisaoMercadoSecundario(
        mercado="escanteios",
        media_esperada=round(media, 2),
        prob_linhas=_calcular_distribuicao(media, linhas),
        intervalo_80pct=_intervalo_credibilidade(media),
        n_jogos_m=medias_m.get("_n", 0),
        n_jogos_v=medias_v.get("_n", 0),
        ausente=False,
    )


def prever_cartoes_amarelos(
    medias_m: dict, medias_v: dict,
    fator_arbitro: Optional[float] = None,
) -> PrevisaoMercadoSecundario:
    """
    Cartões amarelos totais. Árbitro é o fator mais importante (PRD 7.2).
    Linhas típicas: 2.5, 3.5, 4.5, 5.5
    """
    val_m = medias_m.get("cartoes_amarelos")
    val_v = medias_v.get("cartoes_amarelos")

    if val_m is None or val_v is None:
        return PrevisaoMercadoSecundario(
            mercado="cartoes_amarelos", media_esperada=0.0,
            ausente=True,
        )

    media_base = val_m + val_v
    media = _media_com_ajuste_arbitro(media_base, fator_arbitro)
    linhas = [2.5, 3.5, 4.5, 5.5]

    return PrevisaoMercadoSecundario(
        mercado="cartoes_amarelos",
        media_esperada=round(media, 2),
        prob_linhas=_calcular_distribuicao(media, linhas),
        intervalo_80pct=_intervalo_credibilidade(media),
        n_jogos_m=medias_m.get("_n", 0),
        n_jogos_v=medias_v.get("_n", 0),
        ausente=False,
    )


def prever_faltas(
    medias_m: dict, medias_v: dict,
    fator_arbitro: Optional[float] = None,
) -> PrevisaoMercadoSecundario:
    """
    Faltas totais. Linhas típicas: 20.5, 24.5, 28.5
    """
    val_m = medias_m.get("faltas")
    val_v = medias_v.get("faltas")

    if val_m is None or val_v is None:
        return PrevisaoMercadoSecundario(
            mercado="faltas", media_esperada=0.0,
            ausente=True,
        )

    media_base = val_m + val_v
    media = _media_com_ajuste_arbitro(media_base, fator_arbitro)
    linhas = [20.5, 24.5, 28.5]

    return PrevisaoMercadoSecundario(
        mercado="faltas",
        media_esperada=round(media, 2),
        prob_linhas=_calcular_distribuicao(media, linhas),
        intervalo_80pct=_intervalo_credibilidade(media),
        n_jogos_m=medias_m.get("_n", 0),
        n_jogos_v=medias_v.get("_n", 0),
        ausente=False,
    )


def prever_chutes(
    medias_m: dict, medias_v: dict,
    lado: str = "total",  # 'total' | 'mandante' | 'visitante'
) -> PrevisaoMercadoSecundario:
    """
    Chutes totais ou por time. Linhas típicas: 10.5, 13.5, 16.5 (total)
    """
    val_m = medias_m.get("chutes")
    val_v = medias_v.get("chutes")

    if val_m is None and val_v is None:
        return PrevisaoMercadoSecundario(
            mercado="chutes_time", media_esperada=0.0,
            ausente=True,
        )

    if lado == "mandante":
        media = val_m or 0
        linhas = [3.5, 5.5, 7.5]
    elif lado == "visitante":
        media = val_v or 0
        linhas = [3.5, 5.5, 7.5]
    else:
        media = (val_m or 0) + (val_v or 0)
        linhas = [10.5, 13.5, 16.5, 19.5]

    return PrevisaoMercadoSecundario(
        mercado="chutes_time",
        media_esperada=round(media, 2),
        prob_linhas=_calcular_distribuicao(media, linhas),
        intervalo_80pct=_intervalo_credibilidade(media),
        n_jogos_m=medias_m.get("_n", 0),
        n_jogos_v=medias_v.get("_n", 0),
        ausente=(media == 0),
    )


# ---------------------------------------------------------------------------
# Orquestrador: todos os mercados secundários de uma vez
# ---------------------------------------------------------------------------

def calcular_mercados_secundarios(
    pacote: dict,
    fator_arbitro_cartoes: Optional[float] = None,
    fator_arbitro_faltas: Optional[float] = None,
) -> dict[str, PrevisaoMercadoSecundario]:
    """
    Calcula todos os mercados secundários a partir do pacote de ingestão.
    Retorna dict mercado → PrevisaoMercadoSecundario.
    """
    medias_m = pacote["medias_stats"]["mandante"]
    medias_v = pacote["medias_stats"]["visitante"]

    # Adicionar contagem de jogos às médias
    stats_m = pacote["medias_stats"]["mandante"].copy()
    stats_v = pacote["medias_stats"]["visitante"].copy()

    return {
        "escanteios":      prever_escanteios(stats_m, stats_v),
        "cartoes_amarelos": prever_cartoes_amarelos(
            stats_m, stats_v, fator_arbitro_cartoes
        ),
        "faltas":          prever_faltas(
            stats_m, stats_v, fator_arbitro_faltas
        ),
        "chutes_time":     prever_chutes(stats_m, stats_v, lado="total"),
    }
