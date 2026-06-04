"""
Rating prior de seleções nacionais.
Estratégia: calcular Elo a partir dos resultados históricos de Copa do Mundo
disponíveis no banco (Copa 2022 + qualificatórias 2022-2024), usando K-factor
diferenciado por importância do jogo.

Quando não há jogos suficientes no banco ainda, usa Elo inicial de 1500
para todos os times — isso melhora conforme mais dados são ingeridos.

Referência: metodologia World Football Elo (eloratings.net), adaptada.
"""

import logging
import math
from datetime import datetime, timezone
from src.db.repositorio import Repositorio, Time

logger = logging.getLogger(__name__)

# K-factors por tipo de competição
K_FACTORS = {
    "copa_2026": 60,
    "copa_2022": 60,
    "elim_conmebol_2022": 40,
    "elim_conmebol_2026": 40,
    "elim_uefa_2024": 40,
    "elim_uefa_2026": 40,
    "elim_concacaf_2022": 40,
    "elim_concacaf_2026": 40,
    "elim_asia_2022": 40,
    "elim_afc_2026": 40,
    "elim_africa_2022": 40,
    "elim_caf_2026": 40,
    "amistosos_2024": 20,
    "default": 30,
}

ELO_INICIAL = 1500.0


class RatingPrior:
    def __init__(self, repo: Repositorio):
        self.repo = repo

    def _k_factor(self, competicao: str) -> float:
        return K_FACTORS.get(competicao, K_FACTORS["default"])

    def _probabilidade_esperada(self, elo_a: float, elo_b: float,
                                 campo_neutro: bool, lado: str) -> float:
        """
        Probabilidade de A vencer B usando fórmula Elo.
        Ha (Home Advantage): +100 Elo para o mandante se não for campo neutro.
        """
        ha = 0.0
        if not campo_neutro:
            ha = 100.0 if lado == "mandante" else -100.0
        diff = (elo_a + ha) - elo_b
        return 1.0 / (1.0 + 10 ** (-diff / 400.0))

    def _resultado_elo(self, placar_a: int, placar_b: int) -> float:
        """Resultado para o time A: 1.0 vitória, 0.5 empate, 0.0 derrota."""
        if placar_a > placar_b:
            return 1.0
        elif placar_a == placar_b:
            return 0.5
        return 0.0

    def calcular_e_salvar(self) -> int:
        """
        Calcula Elo para todos os times com base nos jogos do banco,
        em ordem cronológica. Salva o rating_prior de cada time.
        Retorna número de times atualizados.
        """
        # Buscar todos os jogos com resultado, ordenados por data
        times = {t.id: t for t in self.repo.listar_times()}
        elos: dict[int, float] = {tid: ELO_INICIAL for tid in times}

        # Usar APENAS jogos de Copa do Mundo para o prior.
        # Motivo: qualificatórias inflam times que vencem muitos jogos contra
        # oponentes fracos dentro da própria confederação (PRD 7.1).
        # Copas são inter-confederações e calibram a escala global.
        copas = ("copa_2022", "copa_2026")
        placeholders = ",".join("?" * len(copas))
        with self.repo._conn() as conn:
            rows = conn.execute(f"""
                SELECT j.*, j.time_mandante_id AS mid, j.time_visitante_id AS vid
                FROM jogos j
                WHERE j.competicao IN ({placeholders})
                  AND j.placar_mandante IS NOT NULL
                  AND j.placar_visitante IS NOT NULL
                  AND j.time_mandante_id IS NOT NULL
                  AND j.time_visitante_id IS NOT NULL
                ORDER BY j.data ASC, j.hora_utc ASC NULLS LAST
            """, copas).fetchall()

        logger.info("Calculando Elo sobre %d jogos históricos", len(rows))

        for row in rows:
            mid = row["mid"]
            vid = row["vid"]
            if mid not in elos:
                elos[mid] = ELO_INICIAL
            if vid not in elos:
                elos[vid] = ELO_INICIAL

            campo_neutro = bool(row["campo_neutro"])
            k = self._k_factor(row["competicao"])

            elo_m = elos[mid]
            elo_v = elos[vid]

            pe_m = self._probabilidade_esperada(elo_m, elo_v, campo_neutro, "mandante")
            pe_v = 1.0 - pe_m

            res_m = self._resultado_elo(row["placar_mandante"], row["placar_visitante"])
            res_v = 1.0 - res_m

            elos[mid] = elo_m + k * (res_m - pe_m)
            elos[vid] = elo_v + k * (res_v - pe_v)

        # Salvar no banco
        agora = datetime.now(timezone.utc).isoformat()
        atualizados = 0
        for tid, elo in elos.items():
            t = times.get(tid)
            if not t:
                continue
            t.rating_prior = round(elo, 1)
            t.rating_prior_atualizado_em = agora
            self.repo.upsert_time(t)
            atualizados += 1

        logger.info("Rating prior calculado para %d times. Top 5: %s",
                    atualizados,
                    sorted(
                        [(times[tid].nome, round(e, 0)) for tid, e in elos.items() if tid in times],
                        key=lambda x: x[1], reverse=True
                    )[:5])
        return atualizados

    def rating_de(self, nome_time: str) -> float | None:
        time = self.repo.buscar_time_por_nome(nome_time)
        if time and time.rating_prior:
            return time.rating_prior
        return None
