"""
Ingestão do openfootball/worldcup.json.
Fonte: https://github.com/openfootball/worldcup.json
Fornece: calendário Copa 2026 (104 fixtures) + histórico de Copas anteriores.
Sem chave de API, dados de domínio público.
"""

import logging
import requests
from src.db.repositorio import Repositorio, Time, Jogo

logger = logging.getLogger(__name__)

BASE_RAW = "https://raw.githubusercontent.com/openfootball/worldcup.json/master"

# Copa 2022 para histórico (stats virão do API-Football)
COPA_2022_URL = f"{BASE_RAW}/2022/worldcup.json"
# Copa 2026 para calendário completo
COPA_2026_URL = f"{BASE_RAW}/2026/worldcup.json"

# Altitude aproximada das cidades-sede (metros) — relevante para o modelo (PRD 7.4)
ALTITUDE_CIDADES = {
    "Mexico City": 2240, "Guadalajara": 1560, "Monterrey": 538,
    "Dallas": 139, "Atlanta": 320, "Houston": 15,
    "Kansas City": 279, "Los Angeles": 93, "San Francisco": 16,
    "Seattle": 10, "New York": 10, "Boston": 14,
    "Philadelphia": 12, "Miami": 2,
    "Toronto": 76, "Vancouver": 70,
}


class IngestorOpenfootball:
    def __init__(self, repo: Repositorio):
        self.repo = repo

    def _fetch_json(self, url: str) -> dict | None:
        cached = self.repo.cache_get("openfootball", url, {})
        if cached is not None:
            return cached
        try:
            r = requests.get(url, timeout=20)
            if r.status_code != 200:
                logger.error("openfootball HTTP %s: %s", r.status_code, url)
                return None
            data = r.json()
            self.repo.cache_set("openfootball", url, {}, data)
            return data
        except Exception as e:
            logger.error("openfootball exceção: %s | %s", e, url)
            return None

    def _garantir_time(self, nome: str, grupo: str = None) -> int:
        time = self.repo.buscar_time_por_nome(nome)
        if time:
            if grupo and not time.grupo_copa26:
                time.grupo_copa26 = grupo
                self.repo.upsert_time(time)
            return time.id
        return self.repo.upsert_time(Time(
            id=None, nome=nome, grupo_copa26=grupo
        ))

    def _parse_rounds(self, data: dict, competicao: str) -> int:
        """Processa matches do JSON e insere jogos. Retorna quantidade inserida."""
        inseridos = 0
        # worldcup.json usa lista plana em "matches" — cada item tem campo "round"
        matches = data.get("matches") or []
        for m in matches:
            fase = m.get("round", "").lower()

            # team1/team2 são strings diretas
            nome1 = m.get("team1", "")
            nome2 = m.get("team2", "")
            if isinstance(nome1, dict):
                nome1 = nome1.get("name", "")
            if isinstance(nome2, dict):
                nome2 = nome2.get("name", "")
            if not nome1 or not nome2:
                continue

            # grupo: campo "group" direto no match, ex: "Group A"
            grupo = None
            grupo_raw = m.get("group", "")
            if grupo_raw:
                partes = grupo_raw.split()
                grupo = partes[-1].upper() if partes else None
            elif "group" in fase:
                partes = fase.split()
                grupo = partes[-1].upper() if len(partes) >= 2 else None

            id1 = self._garantir_time(nome1, grupo)
            id2 = self._garantir_time(nome2, grupo)

            # cidade e altitude
            ground = m.get("ground", "")
            # "ground" pode ser "City" ou "Stadium, City" — pegar a parte antes da vírgula
            cidade = ground.split(",")[0].strip() if ground else ""
            altitude = ALTITUDE_CIDADES.get(cidade)

            # placar (Copa 2026 não tem resultados ainda)
            score = m.get("score") or {}
            ft = score.get("ft") or []
            placar1 = ft[0] if len(ft) > 0 else None
            placar2 = ft[1] if len(ft) > 1 else None

            # hora — formato "13:00 UTC-6", extrair HH:MM
            hora_raw = m.get("time", "")
            hora_utc = hora_raw[:5] if hora_raw and len(hora_raw) >= 5 else None

            jogo = Jogo(
                id=None,
                competicao=competicao,
                data=m.get("date", ""),
                hora_utc=hora_utc,
                time_mandante_id=id1,
                time_visitante_id=id2,
                campo_neutro=1,
                fase=fase,
                grupo=grupo,
                cidade=cidade,
                altitude_m=altitude,
                placar_mandante=placar1,
                placar_visitante=placar2,
                id_externo=None,
                fonte="openfootball",
            )
            self.repo.upsert_jogo(jogo)
            inseridos += 1
        return inseridos

    def ingerir_copa2026(self) -> int:
        logger.info("Ingerindo Copa 2026 via openfootball...")
        data = self._fetch_json(COPA_2026_URL)
        if not data:
            logger.error("Falha ao buscar Copa 2026 do openfootball")
            return 0
        n = self._parse_rounds(data, "copa_2026")
        logger.info("Copa 2026: %d fixtures inseridos/atualizados", n)
        return n

    def ingerir_copa2022(self) -> int:
        logger.info("Ingerindo Copa 2022 via openfootball (estrutura)...")
        data = self._fetch_json(COPA_2022_URL)
        if not data:
            logger.error("Falha ao buscar Copa 2022 do openfootball")
            return 0
        n = self._parse_rounds(data, "copa_2022")
        logger.info("Copa 2022: %d fixtures inseridos/atualizados", n)
        return n
