"""
Scraper Wikipedia — qualificatórias Copa 2026.
Usa o wikitext raw (action=raw) para parsear o template {{Football box}}.
Muito mais robusto que parsear HTML renderizado.
Confirmado na Fase 0: páginas têm todos os jogos de cada confederação.
"""

import re
import logging
import requests
from src.db.repositorio import Repositorio, Time, Jogo

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "CopaAnalyst/1.0 (https://github.com/ThomazArruda/Copa-Analyst; research project) "
        "Python/3.13 requests"
    )
}

# URLs do wikitext raw para cada confederação
PAGINAS_QUALIFICATORIAS = {
    "elim_conmebol_2026": (
        "https://en.wikipedia.org/w/index.php?title=2026_FIFA_World_Cup_qualification_(CONMEBOL)&action=raw",
        "CONMEBOL",
    ),
    "elim_uefa_2026": (
        "https://en.wikipedia.org/w/index.php?title=2026_FIFA_World_Cup_qualification_(UEFA)&action=raw",
        "UEFA",
    ),
    "elim_concacaf_2026": (
        "https://en.wikipedia.org/w/index.php?title=2026_FIFA_World_Cup_qualification_(CONCACAF)&action=raw",
        "CONCACAF",
    ),
    "elim_afc_2026": (
        "https://en.wikipedia.org/w/index.php?title=2026_FIFA_World_Cup_qualification_(AFC)&action=raw",
        "AFC",
    ),
    "elim_caf_2026": (
        "https://en.wikipedia.org/w/index.php?title=2026_FIFA_World_Cup_qualification_(CAF)&action=raw",
        "CAF",
    ),
}

# Mapeamento de código FIFA → nome completo
# Expandir conforme necessário com erros de parse
FIFA_CODES = {
    "ARG": "Argentina", "BRA": "Brazil", "URU": "Uruguay", "COL": "Colombia",
    "ECU": "Ecuador", "PAR": "Paraguay", "PER": "Peru", "CHI": "Chile",
    "BOL": "Bolivia", "VEN": "Venezuela",
    "GER": "Germany", "FRA": "France", "ESP": "Spain", "ENG": "England",
    "ITA": "Italy", "POR": "Portugal", "NED": "Netherlands", "BEL": "Belgium",
    "CRO": "Croatia", "SUI": "Switzerland", "AUT": "Austria", "DEN": "Denmark",
    "SWE": "Sweden", "NOR": "Norway", "POL": "Poland", "CZE": "Czech Republic",
    "HUN": "Hungary", "ROU": "Romania", "SCO": "Scotland", "WAL": "Wales",
    "NIR": "Northern Ireland", "IRL": "Ireland", "GRE": "Greece", "TUR": "Turkey",
    "SRB": "Serbia", "SVK": "Slovakia", "SVN": "Slovenia", "ALB": "Albania",
    "UKR": "Ukraine", "RUS": "Russia", "FIN": "Finland", "ISL": "Iceland",
    "USA": "United States", "MEX": "Mexico", "CAN": "Canada", "CRC": "Costa Rica",
    "JAM": "Jamaica", "PAN": "Panama", "HON": "Honduras", "GTM": "Guatemala",
    "SLV": "El Salvador", "CUB": "Cuba", "TRI": "Trinidad and Tobago",
    "JPN": "Japan", "KOR": "South Korea", "CHN": "China", "AUS": "Australia",
    "IRN": "Iran", "SAU": "Saudi Arabia", "QAT": "Qatar", "UAE": "United Arab Emirates",
    "IRQ": "Iraq", "SYR": "Syria", "JOR": "Jordan", "BHR": "Bahrain",
    "EGY": "Egypt", "NGA": "Nigeria", "GHA": "Ghana", "MAR": "Morocco",
    "SEN": "Senegal", "CMR": "Cameroon", "CIV": "Ivory Coast", "TUN": "Tunisia",
    "ALG": "Algeria", "RSA": "South Africa", "ZIM": "Zimbabwe",
    "FRA": "France", "BEL": "Belgium",
}

# Regex para extrair blocos {{Football box ... }}
# O template pode estar em várias linhas
FOOTBALL_BOX_RE = re.compile(
    r"\{\{Football box[^\}]*?\|([^{}]*(?:\{\{[^{}]*\}\}[^{}]*)*)\}\}",
    re.DOTALL | re.IGNORECASE,
)

# Extrair campos individuais de dentro do bloco
FIELD_RE = re.compile(r"\|\s*(\w+)\s*=\s*(.+?)(?=\n\s*\||\}\})", re.DOTALL)

# Score: X–Y (en-dash ou hífen)
SCORE_FIELD_RE = re.compile(r"(\d+)\s*[–\-]\s*(\d+)")

# Data: {{Start date|YYYY|M|D|...}} ou {{dts|YYYY|M|D}}
DATE_RE = re.compile(r"\{\{(?:Start date|dts)[|](\d{4})[|](\d{1,2})[|](\d{1,2})", re.IGNORECASE)

# Team: {{fb|CODE}}, {{fb-rt|CODE}}, {{fb-br|CODE}} → código FIFA
TEAM_RE = re.compile(r"\{\{fb[^|]*\|([A-Z]{2,4})\}\}", re.IGNORECASE)

# Fallback: nome direto sem template
TEAM_NAME_RE = re.compile(r"\[\[([^\]|]+)")


class ScraperWikipedia:
    def __init__(self, repo: Repositorio):
        self.repo = repo

    def _fetch_wikitext(self, url: str) -> str | None:
        cached = self.repo.cache_get("wikipedia", url, {})
        if cached is not None:
            return cached.get("wikitext")
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code != 200:
                logger.warning("Wikipedia HTTP %s: %s", r.status_code, url)
                return None
            self.repo.cache_set("wikipedia", url, {}, {"wikitext": r.text})
            return r.text
        except Exception as e:
            logger.error("Wikipedia exceção: %s | %s", e, url)
            return None

    def _codigo_para_nome(self, codigo: str) -> str:
        """Converte código FIFA para nome completo."""
        return FIFA_CODES.get(codigo.upper(), codigo)

    def _extrair_nome_time(self, valor: str) -> str | None:
        """Extrai nome do time de um valor de campo wikitext."""
        valor = valor.strip()
        # Tenta {{fb|CODE}}
        m = TEAM_RE.search(valor)
        if m:
            return self._codigo_para_nome(m.group(1))
        # Tenta [[Nome do País|...]] ou [[Nome do País]]
        m = TEAM_NAME_RE.search(valor)
        if m:
            return m.group(1).strip()
        # Texto puro (remover wikitags)
        limpo = re.sub(r"\{\{[^}]+\}\}", "", valor)
        limpo = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", limpo)
        limpo = limpo.strip()
        return limpo if limpo else None

    def _extrair_data(self, valor: str) -> str | None:
        """Extrai data ISO de um campo wikitext."""
        m = DATE_RE.search(valor)
        if m:
            ano, mes, dia = m.group(1), int(m.group(2)), int(m.group(3))
            return f"{ano}-{mes:02d}-{dia:02d}"
        # Tenta ISO direto YYYY-MM-DD
        m = re.search(r"(\d{4}-\d{2}-\d{2})", valor)
        if m:
            return m.group(1)
        return None

    def _garantir_time(self, nome: str, confederacao: str) -> int:
        nome = nome.strip()
        time = self.repo.buscar_time_por_nome(nome)
        if time:
            return time.id
        return self.repo.upsert_time(Time(id=None, nome=nome, confederacao=confederacao))

    def _parsear_football_boxes(self, wikitext: str, competicao: str,
                                 confederacao: str) -> int:
        """
        Extrai todos os {{Football box}} do wikitext e insere no banco.
        Retorna número de jogos inseridos.
        """
        inseridos = 0

        # Extrair blocos Football box manualmente (regex não lida bem com nested {{...}})
        # Vamos usar uma abordagem de busca iterativa
        pos = 0
        text_lower = wikitext.lower()
        while True:
            idx = text_lower.find("{{football box", pos)
            if idx == -1:
                break

            # Encontrar o fechamento do bloco (balancear {{ e }})
            depth = 0
            end = idx
            for i in range(idx, len(wikitext)):
                if wikitext[i:i+2] == "{{":
                    depth += 1
                    i += 1
                elif wikitext[i:i+2] == "}}":
                    depth -= 1
                    if depth == 0:
                        end = i + 2
                        break
            else:
                pos = idx + 1
                continue

            bloco = wikitext[idx:end]
            pos = end

            # Extrair campos com regex simples campo por campo
            campos = {}
            for linha in bloco.split("\n"):
                linha = linha.strip()
                m = re.match(r"\|(\w+)\s*=\s*(.*)", linha)
                if m:
                    campos[m.group(1).lower()] = m.group(2).strip()

            # Score
            score_val = campos.get("score", "")
            ms = SCORE_FIELD_RE.search(score_val)
            if not ms:
                pos = end
                continue
            placar1 = int(ms.group(1))
            placar2 = int(ms.group(2))

            # Times
            nome1 = self._extrair_nome_time(campos.get("team1", ""))
            nome2 = self._extrair_nome_time(campos.get("team2", ""))
            if not nome1 or not nome2:
                continue

            # Data
            data_str = self._extrair_data(campos.get("date", ""))
            if not data_str:
                continue

            id1 = self._garantir_time(nome1, confederacao)
            id2 = self._garantir_time(nome2, confederacao)

            jogo = Jogo(
                id=None,
                competicao=competicao,
                data=data_str,
                hora_utc=None,
                time_mandante_id=id1,
                time_visitante_id=id2,
                campo_neutro=1,
                fase="qualificacao",
                placar_mandante=placar1,
                placar_visitante=placar2,
                fonte="wikipedia",
            )
            self.repo.upsert_jogo(jogo)
            inseridos += 1

        return inseridos

    def _subpaginas_de(self, wikitext: str) -> list[str]:
        """
        Extrai nomes de sub-páginas referenciadas no wikitext.
        Padrões: {{:SubPage}}, {{main|SubPage}}, [[SubPage|...]]
        """
        subpaginas = set()
        # {{:SubPage}} — transclusion direta
        for m in re.finditer(r"\{\{:([^|}\n]+)", wikitext):
            subpaginas.add(m.group(1).strip())
        # {{main|SubPage}} — link para página principal
        for m in re.finditer(r"\{\{main\|([^|}\n]+)", wikitext, re.IGNORECASE):
            subpaginas.add(m.group(1).strip())
        # Filtrar: manter apenas páginas de qualificatórias com "qualification" no nome
        return [p for p in subpaginas if "qualification" in p.lower() or "qualifying" in p.lower()]

    def _url_raw(self, titulo: str) -> str:
        titulo_enc = titulo.replace(" ", "_")
        return f"https://en.wikipedia.org/w/index.php?title={titulo_enc}&action=raw"

    def ingerir_qualificatoria(self, competicao_key: str) -> int:
        if competicao_key not in PAGINAS_QUALIFICATORIAS:
            logger.error("Competição desconhecida: %s", competicao_key)
            return 0

        url, confederacao = PAGINAS_QUALIFICATORIAS[competicao_key]
        logger.info("Scraping Wikipedia: %s (%s)", competicao_key, confederacao)

        wikitext = self._fetch_wikitext(url)
        if not wikitext:
            return 0

        # Tentar parsear direto na página principal (CONMEBOL funciona assim)
        total = self._parsear_football_boxes(wikitext, competicao_key, confederacao)

        # Se não encontrou nada, buscar sub-páginas (UEFA, CONCACAF, CAF, AFC)
        if total == 0:
            subpaginas = self._subpaginas_de(wikitext)
            logger.info("%s: página principal sem Football box — %d sub-páginas encontradas",
                        competicao_key, len(subpaginas))
            for titulo in subpaginas:
                sub_url = self._url_raw(titulo)
                sub_wikitext = self._fetch_wikitext(sub_url)
                if sub_wikitext:
                    n = self._parsear_football_boxes(sub_wikitext, competicao_key, confederacao)
                    total += n
                    if n > 0:
                        logger.info("  %s: %d jogos", titulo, n)

        logger.info("%s: %d jogos no total", competicao_key, total)
        return total

    def ingerir_todas(self) -> dict[str, int]:
        resultados = {}
        for key in PAGINAS_QUALIFICATORIAS:
            resultados[key] = self.ingerir_qualificatoria(key)
        return resultados
