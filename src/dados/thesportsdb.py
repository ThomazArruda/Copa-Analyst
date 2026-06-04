"""
Cliente TheSportsDB — free tier, sem chave.
Usado exclusivamente para resultados da Copa 2026 conforme jogos são disputados.
Confirmado na Fase 0: retorna scores nulos antes do jogo, preenchidos após o apito.
"""

import time
import logging
import requests
from src.db.repositorio import Repositorio

logger = logging.getLogger(__name__)

BASE_URL = "https://www.thesportsdb.com/api/v1/json/3"
PAUSE = 0.5

COPA_2026_LEAGUE_ID = 4429
COPA_2026_SEASON = 2026


class ClienteTheSportsDB:
    def __init__(self, repo: Repositorio):
        self.repo = repo

    def _get(self, endpoint: str, params: dict, usar_cache: bool = True) -> dict | None:
        if usar_cache:
            cached = self.repo.cache_get("thesportsdb", endpoint, params)
            if cached is not None:
                return cached

        url = f"{BASE_URL}{endpoint}"
        try:
            r = requests.get(url, params=params, timeout=15)
            time.sleep(PAUSE)
            if r.status_code != 200:
                logger.warning("TheSportsDB HTTP %s: %s", r.status_code, endpoint)
                return None
            data = r.json()
            if usar_cache:
                self.repo.cache_set("thesportsdb", endpoint, params, data)
            return data
        except Exception as e:
            logger.error("TheSportsDB exceção: %s | %s", e, endpoint)
            return None

    def buscar_resultados_copa26(self) -> list[dict]:
        """
        Busca todos os jogos da Copa 2026 com scores atuais.
        NÃO usa cache — precisa de dados frescos para pegar resultados de jogos recentes.
        """
        data = self._get(
            "/eventsseason.php",
            {"id": COPA_2026_LEAGUE_ID, "s": COPA_2026_SEASON},
            usar_cache=False,
        )
        if not data:
            return []
        eventos = data.get("events") or []
        # Filtrar apenas jogos com resultado (status FT = Full Time)
        return [
            e for e in eventos
            if e.get("intHomeScore") is not None and e.get("strStatus") == "FT"
        ]

    def buscar_todos_fixtures_copa26(self) -> list[dict]:
        """
        Busca todos os 104 fixtures da Copa 2026 (incluindo futuros).
        Usa cache pois a estrutura do torneio não muda.
        """
        data = self._get(
            "/eventsseason.php",
            {"id": COPA_2026_LEAGUE_ID, "s": COPA_2026_SEASON},
            usar_cache=True,
        )
        if not data:
            return []
        return data.get("events") or []

    def buscar_ultimos_jogos_time(self, team_id: int) -> list[dict]:
        """Últimos 5 jogos de um time (inclui forma recente para qualquer competição)."""
        data = self._get("/eventslast.php", {"id": team_id}, usar_cache=False)
        if not data:
            return []
        return data.get("results") or []

    def buscar_id_time(self, nome: str) -> int | None:
        """Busca ID do time no TheSportsDB pelo nome."""
        data = self._get("/searchteams.php", {"t": nome}, usar_cache=True)
        if not data:
            return None
        times = data.get("teams") or []
        # Filtra por sport = Soccer e país do time nacional
        for t in times:
            if t.get("strSport") == "Soccer" and t.get("strLeague", "").lower() in (
                "fifa world cup", "international", "copa america", ""
            ):
                return int(t["idTeam"])
        # Fallback: primeiro resultado Soccer
        for t in times:
            if t.get("strSport") == "Soccer":
                return int(t["idTeam"])
        return None
