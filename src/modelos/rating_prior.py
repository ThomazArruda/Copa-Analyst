"""
Rating prior de seleções nacionais.
Estratégia (v2): semear com os ratings reais do eloratings.net (scraped em
06/jun/2026) e depois ajustar com os jogos da Copa 2022 disponíveis no banco.

Isso resolve o cold start de times como México, Colômbia, Noruega etc. que
não têm jogos de Copa no free tier mas têm rating significativo no Elo global.

Referência: World Football Elo Ratings (eloratings.net), metodologia pública.
"""

import logging
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

# ---------------------------------------------------------------------------
# Ratings eloratings.net — scraped em 06/jun/2026 (pré-Copa 2026)
# Nomes mapeados para o padrão do nosso banco (openfootball/API-Football).
# Atualizar rodando: python -m src.modelos.rating_prior --atualizar
# ---------------------------------------------------------------------------
ELORATINGS_SEED: dict[str, float] = {
    "Spain": 2155, "Argentina": 2113, "France": 2062, "England": 2020,
    "Brazil": 1988, "Portugal": 1984, "Colombia": 1977, "Netherlands": 1944,
    "Ecuador": 1935, "Germany": 1925, "Norway": 1917, "Croatia": 1908,
    "Turkey": 1906, "Japan": 1906, "Switzerland": 1894, "Belgium": 1893,
    "Uruguay": 1892, "Mexico": 1875, "Senegal": 1867, "Denmark": 1864,
    "Italy": 1859, "Paraguay": 1833, "Austria": 1830, "Morocco": 1824,
    "Canada": 1788, "Ukraine": 1785, "Australia": 1774, "Iran": 1772,
    "Scotland": 1770, "Nigeria": 1770, "Algeria": 1760, "South Korea": 1758,
    # "Czechia" no eloratings = "Czech Republic" no nosso banco
    "Czech Republic": 1740,
    "Serbia": 1734, "Panama": 1734, "United States": 1733, "Venezuela": 1727,
    "Uzbekistan": 1718, "Sweden": 1712, "Poland": 1710, "Chile": 1710,
    "Hungary": 1707, "Peru": 1701, "Egypt": 1699, "Ireland": 1699,
    "Ivory Coast": 1695, "Wales": 1691, "Slovenia": 1685, "Jordan": 1685,
    "Slovakia": 1667, "DR Congo": 1661, "Israel": 1647, "Bolivia": 1645,
    "Albania": 1633, "Romania": 1630, "Tunisia": 1628, "Iraq": 1618,
    "Cameroon": 1613, "Costa Rica": 1611, "Greece": 1754,
    "Bosnia & Herzegovina": 1591, "Bosnia and Herzegovina": 1591,
    "Mali": 1588, "Cape Verde": 1576, "Honduras": 1571, "Saudi Arabia": 1569,
    "New Zealand": 1563, "Haiti": 1548, "United Arab Emirates": 1540,
    "Jamaica": 1527, "South Africa": 1518, "Ghana": 1510,
    "Guatemala": 1507, "Qatar": 1423, "Curacao": 1433, "Curaçao": 1433,
    "Trinidad and Tobago": 1388, "El Salvador": 1340,
    # China PR no nosso banco
    "China PR": 1428,
    "Indonesia": 1362, "Vietnam": 1351, "Thailand": 1372,
}


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

        Semente: eloratings.net (ratings reais, pré-Copa 2026).
        Para times sem seed, usa ELO_INICIAL=1500.
        Ajusta com Copa 2022 por cima.
        """
        times = {t.id: t for t in self.repo.listar_times()}

        # Semear com eloratings.net onde disponível
        elos: dict[int, float] = {}
        seed_count = 0
        for tid, t in times.items():
            seed = ELORATINGS_SEED.get(t.nome)
            if seed:
                elos[tid] = float(seed)
                seed_count += 1
            else:
                elos[tid] = ELO_INICIAL
        logger.info("Elo seed: %d times com rating eloratings.net, %d com default 1500",
                    seed_count, len(times) - seed_count)

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
