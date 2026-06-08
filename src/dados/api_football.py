"""
Cliente API-Football — free tier (100 req/dia).
Cache-first: toda resposta vai ao SQLite antes de processar.
Apenas temporadas 2022-2024 disponíveis no free tier (Decisão 2).
"""

import os
import time
import logging
import requests
from dotenv import load_dotenv
from src.db.repositorio import Repositorio

load_dotenv()
logger = logging.getLogger(__name__)

BASE_URL = "https://v3.football.api-sports.io"
PAUSE = 7.0  # segundos entre requests — free tier: 10 req/min → 6s mínimo, 7s com margem

# Leagues confirmados na Fase 0
LEAGUES = {
    "copa_2022":         {"league": 1,  "season": 2022},
    "elim_conmebol_2022": {"league": 34, "season": 2022},
    "elim_uefa_2024":    {"league": 32, "season": 2024},
    "elim_concacaf_2022": {"league": 31, "season": 2022},
    "elim_asia_2022":    {"league": 30, "season": 2022},
    "elim_africa_2022":  {"league": 29, "season": 2022},
    "amistosos_2024":    {"league": 10, "season": 2024},
}


class ClienteApiFootball:
    def __init__(self, repo: Repositorio):
        self.repo = repo
        self.api_key = os.getenv("API_FOOTBALL_KEY")
        if not self.api_key:
            raise ValueError("API_FOOTBALL_KEY não configurada no .env")
        self.headers = {"x-apisports-key": self.api_key}
        self.limite_diario_atingido = False  # set quando a cota de 100/dia esgota

    def _get(self, endpoint: str, params: dict) -> dict | None:
        cached = self.repo.cache_get("api_football", endpoint, params)
        if cached is not None:
            return cached

        url = f"{BASE_URL}{endpoint}"
        try:
            r = requests.get(url, headers=self.headers, params=params, timeout=15)
            time.sleep(PAUSE)
            if r.status_code == 429:
                logger.warning("API-Football rate limit atingido — aguardando 65s")
                time.sleep(65)
                r = requests.get(url, headers=self.headers, params=params, timeout=15)
                time.sleep(PAUSE)
            if r.status_code != 200:
                logger.warning("API-Football HTTP %s: %s %s", r.status_code, endpoint, params)
                return None
            data = r.json()
            if data.get("errors"):
                errs = data["errors"]
                errs_str = str(errs)
                # Cota diária esgotada → sinaliza para o chamador abortar cedo (não adianta
                # continuar; cada chamada só gasta os 7s de PAUSE retornando nada).
                if "limit for the day" in errs_str or "reached the request limit" in errs_str:
                    if not self.limite_diario_atingido:
                        logger.warning("API-Football: limite diário (100/dia) atingido — abortando coleta.")
                    self.limite_diario_atingido = True
                    return None
                if "rateLimit" in errs_str:
                    logger.warning("API-Football rateLimit — aguardando 65s e reintentando")
                    time.sleep(65)
                    return self._get(endpoint, params)  # retry uma vez
                logger.warning("API-Football erro: %s | %s %s", errs, endpoint, params)
                return None
            self.repo.cache_set("api_football", endpoint, params, data)
            return data
        except Exception as e:
            logger.error("API-Football exceção: %s | %s %s", e, endpoint, params)
            return None

    def buscar_fixtures(self, competicao_key: str) -> list[dict]:
        """Retorna lista de fixtures para a competição (usa cache se disponível)."""
        if competicao_key not in LEAGUES:
            logger.error("Competição desconhecida: %s", competicao_key)
            return []
        params = LEAGUES[competicao_key]
        data = self._get("/fixtures", params)
        if not data:
            return []
        return data.get("response", [])

    def buscar_estatisticas(self, fixture_id: int) -> list[dict]:
        """Retorna estatísticas por time de uma partida."""
        params = {"fixture": fixture_id}
        data = self._get("/fixtures/statistics", params)
        if not data:
            return []
        return data.get("response", [])

    def status_conta(self) -> dict | None:
        """Retorna status da conta (requests usados hoje). Não cacheia."""
        try:
            r = requests.get(f"{BASE_URL}/status", headers=self.headers, timeout=10)
            time.sleep(PAUSE)
            if r.status_code == 200:
                return r.json().get("response", {})
        except Exception:
            pass
        return None
