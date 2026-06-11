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
    ausente: bool = False      # True = não há NENHUMA base (nem prior global)
    parcial: bool = False      # True = um ou ambos os lados usaram prior global
    nota: str = ""             # explicação (ex.: "Marrocos via média global")
    # Decomposição por time (o total é a soma): ex. 13 (mandante) + 7 (visitante)
    valor_m: float = 0.0       # parcela do mandante
    valor_v: float = 0.0       # parcela do visitante
    prior_m: bool = False      # True = parcela do mandante veio do prior global
    prior_v: bool = False      # True = parcela do visitante veio do prior global


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
# Núcleo: resolve o valor de cada lado (dado real do time OU prior global)
# ---------------------------------------------------------------------------

def _lado(medias: dict, campo: str, globais: dict, nome: str):
    """Retorna (valor, usou_prior, rotulo). Usa o dado do time; se faltar,
    cai no prior global (média do torneio). None só se nem o prior existir."""
    v = medias.get(campo)
    if v is not None:
        return v, False, None
    g = (globais or {}).get(campo)
    if g is not None:
        return g, True, f"{nome} via média global"
    return None, False, None


def _montar(mercado, valor_total, vm, vv, linhas, usou_m, usou_v, rot_m, rot_v,
            n_m, n_v) -> PrevisaoMercadoSecundario:
    parcial = usou_m or usou_v
    notas = [r for r in (rot_m, rot_v) if r]
    return PrevisaoMercadoSecundario(
        mercado=mercado,
        media_esperada=round(valor_total, 2),
        prob_linhas=_calcular_distribuicao(valor_total, linhas),
        intervalo_80pct=_intervalo_credibilidade(valor_total),
        n_jogos_m=n_m, n_jogos_v=n_v,
        ausente=False, parcial=parcial,
        nota="; ".join(notas),
        valor_m=round(vm, 2), valor_v=round(vv, 2),
        prior_m=usou_m, prior_v=usou_v,
    )


# ---------------------------------------------------------------------------
# Funções públicas por mercado — usam o dado disponível + prior global
# ---------------------------------------------------------------------------

def prever_escanteios(medias_m, medias_v, globais=None) -> PrevisaoMercadoSecundario:
    vm, um, rm = _lado(medias_m, "escanteios", globais, "mandante")
    vv, uv, rv = _lado(medias_v, "escanteios", globais, "visitante")
    if vm is None or vv is None:
        return PrevisaoMercadoSecundario(mercado="escanteios", media_esperada=0.0, ausente=True)
    return _montar("escanteios", vm + vv, vm, vv, [7.5, 8.5, 9.5, 10.5, 11.5],
                   um, uv, rm, rv, medias_m.get("_n", 0), medias_v.get("_n", 0))


def prever_cartoes_amarelos(medias_m, medias_v, fator_arbitro=None, globais=None) -> PrevisaoMercadoSecundario:
    vm, um, rm = _lado(medias_m, "cartoes_amarelos", globais, "mandante")
    vv, uv, rv = _lado(medias_v, "cartoes_amarelos", globais, "visitante")
    if vm is None or vv is None:
        return PrevisaoMercadoSecundario(mercado="cartoes_amarelos", media_esperada=0.0, ausente=True)
    esc = fator_arbitro or 1.0
    media = _media_com_ajuste_arbitro(vm + vv, fator_arbitro)
    return _montar("cartoes_amarelos", media, vm * esc, vv * esc, [2.5, 3.5, 4.5, 5.5],
                   um, uv, rm, rv, medias_m.get("_n", 0), medias_v.get("_n", 0))


def prever_faltas(medias_m, medias_v, fator_arbitro=None, globais=None) -> PrevisaoMercadoSecundario:
    vm, um, rm = _lado(medias_m, "faltas", globais, "mandante")
    vv, uv, rv = _lado(medias_v, "faltas", globais, "visitante")
    if vm is None or vv is None:
        return PrevisaoMercadoSecundario(mercado="faltas", media_esperada=0.0, ausente=True)
    esc = fator_arbitro or 1.0
    media = _media_com_ajuste_arbitro(vm + vv, fator_arbitro)
    return _montar("faltas", media, vm * esc, vv * esc, [20.5, 24.5, 28.5],
                   um, uv, rm, rv, medias_m.get("_n", 0), medias_v.get("_n", 0))


def prever_chutes(medias_m, medias_v, lado="total", globais=None) -> PrevisaoMercadoSecundario:
    vm, um, rm = _lado(medias_m, "chutes", globais, "mandante")
    vv, uv, rv = _lado(medias_v, "chutes", globais, "visitante")
    if vm is None and vv is None:
        return PrevisaoMercadoSecundario(mercado="chutes_time", media_esperada=0.0, ausente=True)
    if lado == "mandante":
        return _montar("chutes_time", vm or 0, vm or 0, 0.0, [3.5, 5.5, 7.5], um, False, rm, None,
                       medias_m.get("_n", 0), 0)
    if lado == "visitante":
        return _montar("chutes_time", vv or 0, 0.0, vv or 0, [3.5, 5.5, 7.5], False, uv, None, rv,
                       0, medias_v.get("_n", 0))
    return _montar("chutes_time", (vm or 0) + (vv or 0), vm or 0, vv or 0, [10.5, 13.5, 16.5, 19.5],
                   um, uv, rm, rv, medias_m.get("_n", 0), medias_v.get("_n", 0))


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
    stats_m = pacote["medias_stats"]["mandante"].copy()
    stats_v = pacote["medias_stats"]["visitante"].copy()
    globais = pacote.get("medias_globais") or {}

    return {
        "escanteios":      prever_escanteios(stats_m, stats_v, globais),
        "cartoes_amarelos": prever_cartoes_amarelos(
            stats_m, stats_v, fator_arbitro_cartoes, globais
        ),
        "faltas":          prever_faltas(
            stats_m, stats_v, fator_arbitro_faltas, globais
        ),
        "chutes_time":     prever_chutes(stats_m, stats_v, lado="total", globais=globais),
    }
