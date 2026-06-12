"""
Pesquisa qualitativa via Claude com web search.

Três pesquisas por jogo:
  - uma dedicada a cada seleção (escalação, lesões, notícias de treino, últimos resultados)
  - uma de contexto do confronto (árbitro, situação no grupo, local/clima)

Cada pesquisa tem orçamento próprio de buscas, o que dá profundidade
por tópico em vez de diluir o orçamento entre dois times.

A conta opera num tier com limite de tokens de input por minuto; por isso as
chamadas rodam em sequência por padrão (PESQUISA_PARALELA=true para tiers
maiores) e todas passam pelo retry de 429.
"""

import os
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, date
from dotenv import load_dotenv
import anthropic

from src.ia._retry import criar_mensagem_com_retry

load_dotenv()
logger = logging.getLogger(__name__)

MODELO = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
# Orçamentos de busca por chamada. Total padrão: 4+4+3 = 11 buscas por jogo.
# Subir melhora a cobertura; descer alivia custo e o rate limit de input/min.
MAX_BUSCAS_TIME = int(os.getenv("MAX_BUSCAS_TIME", "4"))
MAX_BUSCAS_CONTEXTO = int(os.getenv("MAX_BUSCAS_CONTEXTO", "3"))
MAX_TOKENS_PESQUISA = 3500


def _cliente() -> anthropic.Anthropic:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")
    return anthropic.Anthropic(api_key=key)


def _extrair_texto_e_fontes(resposta) -> tuple[str, list[str]]:
    """
    Extrai texto e URLs de fontes de uma resposta com web search.
    Fontes vêm de dois lugares: blocos web_search_tool_result (resultados
    das buscas) e citations dentro dos blocos de texto (o que foi de fato citado).
    """
    texto = ""
    fontes: list[str] = []

    for bloco in resposta.content:
        tipo = getattr(bloco, "type", "")
        if tipo == "text":
            texto += bloco.text
            for cit in getattr(bloco, "citations", None) or []:
                url = getattr(cit, "url", None)
                if url and url not in fontes:
                    fontes.append(url)
        elif tipo == "web_search_tool_result":
            conteudo = getattr(bloco, "content", None) or []
            if isinstance(conteudo, list):
                for item in conteudo:
                    url = getattr(item, "url", None)
                    if url and url not in fontes:
                        fontes.append(url)

    return texto, fontes


def _regras_comuns(data_jogo: str) -> str:
    hoje = date.today().isoformat()
    return f"""REGRAS DE QUALIDADE (obrigatórias):
- Hoje é {hoje}. O jogo é em {data_jogo}. Priorize notícias das últimas 72 horas; \
informação com mais de 1 semana só vale para resultados de jogos.
- Para CADA fato, registre: a data da informação e a qualidade da fonte \
[primária = comunicado oficial/federação/FIFA; secundária = veículo esportivo estabelecido \
(Globo Esporte, ESPN, Marca, L'Équipe, BBC...); fraca = blog/rumor/rede social].
- Busque também em veículos do idioma nativo da seleção (português, espanhol, francês, etc.) — \
a imprensa local tem informação de treino mais recente que a internacional.
- Se a informação não foi encontrada após buscar, escreva exatamente "NÃO ENCONTRADO" no campo. \
NUNCA preencha com suposição ou com dados de outra Copa.
- Não invente nomes de jogadores, árbitros ou placares."""


def _pesquisar_selecao(cliente, nome: str, adversario: str, data_jogo: str, fase: str) -> dict:
    """Pesquisa focada em UMA seleção: escalação, desfalques, treino, forma."""
    prompt = f"""Você é um analista de futebol coletando informação pré-jogo sobre **{nome}**, \
que enfrenta {adversario} pela Copa do Mundo 2026 ({fase}) em {data_jogo}.

Pesquise na web e produza um dossiê APENAS sobre {nome}, neste formato:

## ESCALAÇÃO PROVÁVEL — {nome}
- Formação tática e os 11 prováveis (titulares confirmados em treino > especulação de imprensa).
- Indique a fonte e a data de cada informação de escalação.
- Dúvidas no time titular e quem disputa a vaga.

## DESFALQUES E DEPARTAMENTO MÉDICO — {nome}
- Lesionados (com tipo de lesão e prazo de retorno, se divulgado).
- Suspensos (cartões) e pendurados em risco para o próximo jogo.
- Jogadores em transição/recém-recuperados que podem começar no banco.

## NOTÍCIAS DE TREINO E BASTIDORES (últimas 72h) — {nome}
- O que saiu dos treinos: mudanças táticas testadas, time esboçado, poupados.
- Declarações relevantes do técnico ou jogadores em coletiva.
- Clima interno: atritos, motivação, pressão da imprensa local.

## ÚLTIMOS RESULTADOS — {nome}
- Os últimos 5 jogos oficiais/amistosos com data, adversário, placar e competição.
- Inclua jogos de preparação de 2026 (amistosos pré-Copa e jogos da própria Copa).
- Uma linha sobre o desempenho: como o time chegou (dominante, instável, etc.).

{_regras_comuns(data_jogo)}"""

    resposta = criar_mensagem_com_retry(
        cliente,
        model=MODELO,
        max_tokens=MAX_TOKENS_PESQUISA,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": MAX_BUSCAS_TIME}],
        messages=[{"role": "user", "content": prompt}],
    )
    texto, fontes = _extrair_texto_e_fontes(resposta)
    return {"texto": texto, "fontes": fontes}


def _pesquisar_contexto(cliente, mandante: str, visitante: str, data_jogo: str, fase: str) -> dict:
    """Pesquisa do confronto em si: árbitro, situação no grupo, local."""
    prompt = f"""Você é um analista de futebol coletando o contexto do jogo \
**{mandante} × {visitante}** — Copa do Mundo 2026, {fase}, {data_jogo}.

Pesquise na web e responda APENAS sobre o confronto (não analise os elencos):

## ARBITRAGEM
- Árbitro designado (nome e confederação) e VAR, se já divulgado pela FIFA.
- Perfil do árbitro se houver dado confiável: média de cartões/faltas por jogo.

## SITUAÇÃO NA COMPETIÇÃO
- Classificação atual do grupo (pontos, saldo) ou chaveamento do mata-mata.
- O que cada seleção precisa neste jogo (já classificada? eliminada se perder? \
combinação de resultados?). Isso muda postura tática e deve ficar explícito.

## LOCAL E CONDIÇÕES
- Estádio, cidade, altitude e previsão do tempo para o horário do jogo (calor é fator nos EUA/México).
- Logística: dias de descanso de cada time desde o último jogo e deslocamento entre sedes.

{_regras_comuns(data_jogo)}"""

    resposta = criar_mensagem_com_retry(
        cliente,
        model=MODELO,
        max_tokens=MAX_TOKENS_PESQUISA,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": MAX_BUSCAS_CONTEXTO}],
        messages=[{"role": "user", "content": prompt}],
    )
    texto, fontes = _extrair_texto_e_fontes(resposta)
    return {"texto": texto, "fontes": fontes}


def pesquisar_jogo(
    nome_mandante: str,
    nome_visitante: str,
    data_jogo: str,
    fase: str = "grupo",
) -> dict:
    """
    Pesquisa qualitativa para um jogo: 3 chamadas com web search
    (mandante, visitante, contexto do confronto).
    Retorna dict com texto_bruto consolidado, seções individuais e fontes.
    """
    if os.getenv("MOCK_AI", "").lower() == "true":
        logger.info("MOCK_AI=true — retornando pesquisa mockada")
        return _pesquisa_mock(nome_mandante, nome_visitante)

    cliente = _cliente()
    erros = []

    def _seguro(fn, *args):
        try:
            return fn(cliente, *args)
        except Exception as e:
            logger.error("Pesquisa falhou (%s): %s", args[0] if args else "?", e)
            erros.append(str(e))
            return {"texto": f"PESQUISA FALHOU: {e}", "fontes": []}

    tarefas = [
        (_pesquisar_selecao, (nome_mandante, nome_visitante, data_jogo, fase)),
        (_pesquisar_selecao, (nome_visitante, nome_mandante, data_jogo, fase)),
        (_pesquisar_contexto, (nome_mandante, nome_visitante, data_jogo, fase)),
    ]

    if os.getenv("PESQUISA_PARALELA", "").lower() == "true":
        with ThreadPoolExecutor(max_workers=3) as ex:
            futuros = [ex.submit(_seguro, fn, *args) for fn, args in tarefas]
            sec_m, sec_v, sec_c = (f.result() for f in futuros)
    else:
        # Sequencial espalha o consumo de tokens de input ao longo do tempo,
        # o que evita estourar o limite por minuto do tier atual.
        sec_m, sec_v, sec_c = (_seguro(fn, *args) for fn, args in tarefas)

    texto_bruto = f"""### DOSSIÊ {nome_mandante.upper()}

{sec_m['texto']}

---

### DOSSIÊ {nome_visitante.upper()}

{sec_v['texto']}

---

### CONTEXTO DO CONFRONTO

{sec_c['texto']}"""

    fontes = []
    for f in sec_m["fontes"] + sec_v["fontes"] + sec_c["fontes"]:
        if f not in fontes:
            fontes.append(f)

    logger.info(
        "Pesquisa concluída: %d chars, %d fontes (%d erros)",
        len(texto_bruto), len(fontes), len(erros),
    )

    resultado = {
        "texto_bruto": texto_bruto,
        "secoes": {
            "mandante": sec_m["texto"],
            "visitante": sec_v["texto"],
            "contexto": sec_c["texto"],
        },
        "fontes": fontes,
        "modelo": MODELO,
        "coletado_em": datetime.now(timezone.utc).isoformat(),
        "mock": False,
    }
    if erros:
        resultado["erro"] = "; ".join(erros)
    return resultado


def _pesquisa_mock(mandante: str, visitante: str) -> dict:
    texto = f"""### DOSSIÊ {mandante.upper()}

## ESCALAÇÃO PROVÁVEL — {mandante}
Titular 1, Titular 2, ... (mock)

## DESFALQUES E DEPARTAMENTO MÉDICO — {mandante}
Nenhum confirmado (mock)

## NOTÍCIAS DE TREINO E BASTIDORES (últimas 72h) — {mandante}
Nenhuma notícia relevante encontrada (mock)

## ÚLTIMOS RESULTADOS — {mandante}
NÃO ENCONTRADO (mock)

---

### DOSSIÊ {visitante.upper()}

## ESCALAÇÃO PROVÁVEL — {visitante}
Titular A, Titular B, ... (mock)

## DESFALQUES E DEPARTAMENTO MÉDICO — {visitante}
Nenhum confirmado (mock)

## NOTÍCIAS DE TREINO E BASTIDORES (últimas 72h) — {visitante}
Nenhuma notícia relevante encontrada (mock)

## ÚLTIMOS RESULTADOS — {visitante}
NÃO ENCONTRADO (mock)

---

### CONTEXTO DO CONFRONTO

## ARBITRAGEM
A definir (mock)

## SITUAÇÃO NA COMPETIÇÃO
Primeiro jogo do grupo (mock)

## LOCAL E CONDIÇÕES
Sem dados (mock)"""

    return {
        "texto_bruto": texto,
        "secoes": {"mandante": "(mock)", "visitante": "(mock)", "contexto": "(mock)"},
        "fontes": ["mock_source_1", "mock_source_2"],
        "modelo": "mock",
        "coletado_em": datetime.now(timezone.utc).isoformat(),
        "mock": True,
    }
