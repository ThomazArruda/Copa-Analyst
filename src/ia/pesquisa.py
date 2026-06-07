"""
Pesquisa qualitativa via Claude com web search.
Coleta: escalação provável, lesões, suspensões, árbitro, notícias, contexto.
"""

import os
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
import anthropic

from src.ia._retry import criar_mensagem_com_retry

load_dotenv()
logger = logging.getLogger(__name__)

MODELO = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
MAX_BUSCAS_PESQUISA = 6


def _cliente() -> anthropic.Anthropic:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")
    return anthropic.Anthropic(api_key=key)


def pesquisar_jogo(
    nome_mandante: str,
    nome_visitante: str,
    data_jogo: str,
    fase: str = "grupo",
) -> dict:
    """
    Pesquisa qualitativa para um jogo via Claude com web search.
    Retorna dict estruturado com os achados.

    nome_mandante, nome_visitante: nomes completos das seleções
    data_jogo: ISO date YYYY-MM-DD
    fase: 'grupo' | 'oitavas' | etc.
    """
    if os.getenv("MOCK_AI", "").lower() == "true":
        logger.info("MOCK_AI=true — retornando pesquisa mockada")
        return _pesquisa_mock(nome_mandante, nome_visitante)

    cliente = _cliente()

    prompt = f"""Você é um analista de futebol preparando informações qualitativas para uma análise pré-jogo.

Pesquise e colete as seguintes informações para o jogo:
**{nome_mandante} × {nome_visitante}** — Copa do Mundo 2026, {fase}, {data_jogo}

Busque especificamente:
1. **Escalação provável** de cada time (titulares confirmados ou prováveis)
2. **Lesões e suspensões** (jogadores ausentes confirmados ou em dúvida)
3. **Árbitro designado** para o jogo (nome e confederação)
4. **Notícias relevantes** das últimas 48h sobre cada time (clima interno, declarações, condição física)
5. **Situação no grupo** — cada time já está classificado? Precisa de resultado específico?
6. **Contexto físico** — distância percorrida desde o jogo anterior, fuso horário, tempo de descanso

Para cada informação, indique a **qualidade da fonte**: primária (oficial/veículo estabelecido), secundária (jornalismo esportivo), fraca (rumor/blog).

Se uma informação não for encontrada, declare explicitamente como "não encontrada".
Seja objetivo e factual. Não invente informações."""

    try:
        resposta = criar_mensagem_com_retry(
            cliente,
            model=MODELO,
            max_tokens=2048,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": MAX_BUSCAS_PESQUISA}],
            messages=[{"role": "user", "content": prompt}],
        )

        # Extrair texto e fontes usadas
        texto = ""
        fontes = []
        for bloco in resposta.content:
            if hasattr(bloco, "text"):
                texto += bloco.text
            if hasattr(bloco, "type") and bloco.type == "tool_result":
                if hasattr(bloco, "url"):
                    fontes.append(bloco.url)

        logger.info("Pesquisa concluída: %d chars, %d fontes", len(texto), len(fontes))

        return {
            "texto_bruto": texto,
            "fontes": fontes,
            "modelo": MODELO,
            "coletado_em": datetime.now(timezone.utc).isoformat(),
            "mock": False,
        }

    except Exception as e:
        logger.error("Erro na pesquisa qualitativa: %s", e)
        return {
            "texto_bruto": f"Pesquisa falhou: {e}",
            "fontes": [],
            "modelo": MODELO,
            "coletado_em": datetime.now(timezone.utc).isoformat(),
            "mock": False,
            "erro": str(e),
        }


def _pesquisa_mock(mandante: str, visitante: str) -> dict:
    return {
        "texto_bruto": f"""## Pesquisa Mock: {mandante} × {visitante}

**Escalação provável {mandante}:** Titular 1, Titular 2, ... (mock)
**Escalação provável {visitante}:** Titular A, Titular B, ... (mock)

**Lesões/Suspensões:** Nenhuma confirmada (mock)
**Árbitro:** A definir (mock)
**Notícias:** Nenhuma notícia relevante encontrada (mock)
**Situação no grupo:** Primeiro jogo do grupo — nenhum classificado ainda (mock)
**Contexto físico:** Times descansados, sem jogos recentes (mock)
""",
        "fontes": ["mock_source_1", "mock_source_2"],
        "modelo": "mock",
        "coletado_em": datetime.now(timezone.utc).isoformat(),
        "mock": True,
    }
