"""
Orquestrador de síntese — Fase 3.
Monta o contexto completo, chama Claude, valida o output, persiste no banco.
"""

import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
import anthropic

from src.ia.validacao import validar_saida, saida_para_dict, SaidaIA
from src.ia.pesquisa import pesquisar_jogo
from src.ia._retry import criar_mensagem_com_retry
from src.db.repositorio import Repositorio, Jogo, Time
from src.modelos.dixon_coles import DixonColes, PrevisaoCalculada
from src.modelos.mercados import calcular_mercados_secundarios

load_dotenv()
logger = logging.getLogger(__name__)

MODELO = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
MAX_BUSCAS_SINTESE = 3
# Folga para 7 mercados com justificativas (4096 truncava jogos "ricos" → JSON
# cortado → falha de validação/repair). 8192 é seguro sem streaming.
MAX_TOKENS_SINTESE = int(os.getenv("MAX_TOKENS_SINTESE", "8192"))
PROMPT_VERSAO = "v1"

# Apelidos de modelo aceitos pela API/UI (jogos importantes → Opus).
# IDs conferidos na referência da Claude API (claude-opus-4-8 = mais capaz atual).
MODELOS_DISPONIVEIS = {
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-8",
}


def resolver_modelo(modelo: str | None) -> str:
    """Resolve apelido ('opus'/'sonnet') ou id completo para um id de modelo válido.
    None → default do ambiente (CLAUDE_MODEL ou sonnet)."""
    if not modelo:
        return MODELO
    return MODELOS_DISPONIVEIS.get(modelo.lower(), modelo)
PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / f"sintese_{PROMPT_VERSAO}.md"


def _cliente() -> anthropic.Anthropic:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")
    return anthropic.Anthropic(api_key=key)


def _carregar_prompt() -> str:
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"Prompt não encontrado: {PROMPT_PATH}")
    return PROMPT_PATH.read_text(encoding="utf-8")


def _montar_contexto(
    jogo: Jogo,
    time_m: Time,
    time_v: Time,
    pacote: dict,
    previsao_dc: PrevisaoCalculada,
    mercados_sec: dict,
    pesquisa: dict,
    repo: "Repositorio" = None,
) -> str:
    """
    Monta o bloco de contexto que vai no prompt de síntese.
    """
    # Forma recente (últimos 5 jogos)
    def _resumir_forma(jogos: list, time_id: int, repo: Repositorio) -> str:
        linhas = []
        for j in jogos[:5]:
            m = repo.buscar_time(j.time_mandante_id)
            v = repo.buscar_time(j.time_visitante_id)
            nm = m.nome if m else "?"
            nv = v.nome if v else "?"
            pl = f"{j.placar_mandante}-{j.placar_visitante}" if j.placar_mandante is not None else "?"
            linhas.append(f"  {j.data} | {nm} {pl} {nv} | {j.competicao}")
        return "\n".join(linhas) if linhas else "  (sem dados)"

    elo_m = pacote["rating_prior"]["mandante"]
    elo_v = pacote["rating_prior"]["visitante"]

    # Médias de mercados secundários
    def _fmt_medias(medias: dict) -> str:
        if not medias:
            return "  (sem dados)"
        campos = ["escanteios", "chutes", "faltas", "cartoes_amarelos"]
        return "\n".join(
            f"  {c}: {medias[c]:.1f}/jogo" for c in campos if c in medias
        )

    # Mercados secundários calculados
    def _fmt_mkt_sec(mercados: dict) -> str:
        linhas = []
        for nome, prev in mercados.items():
            if prev.ausente:
                linhas.append(f"  {nome}: AUSENTE (sem dados)")
            else:
                probs_str = ", ".join(f">{k}: {v:.1%}" for k, v in list(prev.prob_linhas.items())[:3])
                linhas.append(f"  {nome}: media={prev.media_esperada:.1f} | {probs_str}")
        return "\n".join(linhas) if linhas else "  (sem dados)"

    # Cabeçalho do jogo
    ha_info = f"HA aplicado: {previsao_dc.ha_aplicado:.2f} log-odds" if previsao_dc.ha_aplicado else "Campo neutro (HA=0)"

    ctx = f"""## CONTEXTO DO JOGO

**Jogo:** {time_m.nome} × {time_v.nome}
**Data:** {jogo.data} {jogo.hora_utc or ''}
**Fase:** {jogo.fase or 'grupo'}
**Grupo:** {jogo.grupo or 'N/A'}
**Local:** {jogo.cidade or 'N/A'} | Altitude: {jogo.altitude_m or 0:.0f}m
**Campo neutro:** {'Sim' if jogo.campo_neutro else 'Não'} | {ha_info}

---

## RATING PRIOR (Elo)

{time_m.nome}: {elo_m:.0f} Elo
{time_v.nome}: {elo_v:.0f} Elo
Diferença: {(elo_m or 0) - (elo_v or 0):.0f} pontos a favor de {time_m.nome if (elo_m or 0) >= (elo_v or 0) else time_v.nome}

---

## MODELO DIXON-COLES (previsões calculadas)

Gols esperados: {time_m.nome} {previsao_dc.lambda_m:.2f} | {time_v.nome} {previsao_dc.mu_v:.2f}
Cold start: {'SIM — parâmetros baseados quase só no prior Elo' if previsao_dc.cold_start else 'Não — dados de Copa disponíveis'}

Resultado (1X2):
  {time_m.nome}: {previsao_dc.prob_vitoria_m:.1%}
  Empate: {previsao_dc.prob_empate:.1%}
  {time_v.nome}: {previsao_dc.prob_vitoria_v:.1%}

Total de gols:
  Over 0.5: {previsao_dc.prob_over.get(0.5, 0):.1%}
  Over 1.5: {previsao_dc.prob_over.get(1.5, 0):.1%}
  Over 2.5: {previsao_dc.prob_over.get(2.5, 0):.1%}
  Over 3.5: {previsao_dc.prob_over.get(3.5, 0):.1%}

Ambas marcam: {previsao_dc.prob_ambas_marcam:.1%}
Placar mais provável: {previsao_dc.placar_mais_provavel[0]}-{previsao_dc.placar_mais_provavel[1]}

Jogos de Copa usados para parâmetros:
  {time_m.nome}: {previsao_dc.params_m.n_jogos if previsao_dc.params_m else 0} jogos
  {time_v.nome}: {previsao_dc.params_v.n_jogos if previsao_dc.params_v else 0} jogos

---

## MERCADOS SECUNDÁRIOS (Poisson sobre médias históricas)

{_fmt_mkt_sec(mercados_sec)}

Médias brutas {time_m.nome}:
{_fmt_medias(pacote['medias_stats']['mandante'])}

Médias brutas {time_v.nome}:
{_fmt_medias(pacote['medias_stats']['visitante'])}

---

## FORMA RECENTE

{time_m.nome} (últimos 5 com resultado):
{_resumir_forma(pacote['forma_copa']['mandante'] + pacote['forma_recente']['mandante'], time_m.id if time_m else 0, repo)}

{time_v.nome} (últimos 5 com resultado):
{_resumir_forma(pacote['forma_copa']['visitante'] + pacote['forma_recente']['visitante'], time_v.id if time_v else 0, repo)}

---

## HEAD-TO-HEAD (peso baixo — seleções se enfrentam raramente)

{_resumir_h2h(pacote['head_to_head'], pacote)}

---

## PESQUISA QUALITATIVA

{pesquisa.get('texto_bruto', 'Pesquisa não disponível')}

Fontes consultadas: {', '.join(pesquisa.get('fontes', [])) or 'Nenhuma'}

---

## FATORES AUSENTES (do pipeline de dados)

{chr(10).join('- ' + f for f in pacote['fatores_ausentes']) if pacote['fatores_ausentes'] else '- Nenhum registrado pelo pipeline (verificar manualmente)'}

---

## PARÂMETROS DO MODELO

Decaimento temporal: 0.005
Shrinkage prior: 0.70
Janela forma: 10 jogos
Banda ajuste qualitativo: ±10pp
"""
    return ctx


def _resumir_h2h(jogos: list, pacote: dict) -> str:
    if not jogos:
        return "  (sem histórico direto disponível)"
    linhas = []
    for j in jogos[:5]:
        pl = f"{j.placar_mandante}-{j.placar_visitante}" if j.placar_mandante is not None else "?"
        linhas.append(f"  {j.data} | placar: {pl} | {j.competicao}")
    return "\n".join(linhas)


def _chamar_claude(sistema: str, contexto: str, modelo: str = None) -> str:
    """Chama Claude com o prompt de síntese. Sem web search — só raciocínio sobre o contexto."""
    if os.getenv("MOCK_AI", "").lower() == "true":
        return _sintese_mock()

    cliente = _cliente()
    resposta = criar_mensagem_com_retry(
        cliente,
        model=modelo or MODELO,
        max_tokens=MAX_TOKENS_SINTESE,
        system=sistema,
        messages=[{"role": "user", "content": contexto}],
    )
    if resposta.stop_reason == "max_tokens":
        logger.warning("Síntese truncada (max_tokens) — JSON pode falhar na validação")
    return resposta.content[0].text if resposta.content else ""


def _sintese_mock() -> str:
    return json.dumps({
        "resumo_executivo": "Jogo de exemplo com dados mockados. Nenhuma análise real foi executada.",
        "fatores_avaliados": ["rating prior (Elo)", "Dixon-Coles", "mock"],
        "fatores_ausentes": ["escalação não verificada (MOCK_AI=true)", "árbitro não verificado"],
        "previsoes": [
            {
                "mercado": "resultado",
                "previsao": "vitória mandante",
                "probabilidade_estimada": 0.45,
                "probabilidade_calculada_original": 0.45,
                "incerteza": "alta",
                "origem": "calculado",
                "justificativa": "Baseado no prior Elo. Modo mock ativo.",
                "fontes": ["dixon-coles-mock"]
            },
            {
                "mercado": "total_gols",
                "previsao": "over 1.5",
                "probabilidade_estimada": 0.72,
                "probabilidade_calculada_original": 0.72,
                "incerteza": "alta",
                "origem": "calculado",
                "justificativa": "Baseado nos gols esperados do modelo. Modo mock ativo.",
                "fontes": ["dixon-coles-mock"]
            }
        ]
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Ponto de entrada principal
# ---------------------------------------------------------------------------

def analisar_jogo(jogo_id: int, repo: Repositorio, modelo: str = None) -> dict:
    """
    Pipeline completo de análise para um jogo.
    `modelo`: apelido ('opus'/'sonnet') ou id; None → default do ambiente.
    Retorna dict com relatório_id e a SaidaIA validada.
    """
    from src.dados.ingestao import pacote_jogo, COMPETICOES_FORMA
    from src.modelos.mercados import calcular_mercados_secundarios

    modelo_usado = resolver_modelo(modelo)

    # 1. Coletar dados
    pacote = pacote_jogo(jogo_id)
    jogo   = pacote["jogo"]
    time_m = pacote["time_mandante"]
    time_v = pacote["time_visitante"]

    if not time_m or not time_v:
        raise ValueError(f"Times não encontrados para jogo {jogo_id}")

    # 2. Modelo estatístico
    dc = DixonColes(repo)
    previsao_dc = dc.prever_por_pacote(pacote)

    # 3. Mercados secundários
    mercados_sec = calcular_mercados_secundarios(pacote)

    # 4. Pesquisa qualitativa
    pesquisa = pesquisar_jogo(
        nome_mandante=time_m.nome,
        nome_visitante=time_v.nome,
        data_jogo=jogo.data,
        fase=jogo.fase or "grupo",
    )

    # 5. Montar contexto + prompt
    sistema = _carregar_prompt()
    contexto = _montar_contexto(
        jogo, time_m, time_v,
        pacote, previsao_dc, mercados_sec, pesquisa,
        repo=repo,
    )

    # 6. Chamar Claude
    logger.info("Chamando Claude (%s) para síntese: %s × %s", modelo_usado, time_m.nome, time_v.nome)
    texto_saida = _chamar_claude(sistema, contexto, modelo_usado)

    # 7. Validar output (com 1 tentativa de repair)
    saida, erros = validar_saida(texto_saida)

    if saida is None and not os.getenv("MOCK_AI", "").lower() == "true":
        logger.warning("Validação falhou, tentando repair...")
        repair_prompt = f"""A sua resposta anterior falhou na validação com estes erros:
{chr(10).join(erros)}

Por favor, corrija e retorne APENAS o JSON válido, sem nenhum texto fora do bloco JSON."""

        cliente = _cliente()
        resposta_repair = criar_mensagem_com_retry(
            cliente,
            model=modelo_usado,
            max_tokens=MAX_TOKENS_SINTESE,
            system=sistema,
            messages=[
                {"role": "user", "content": contexto},
                {"role": "assistant", "content": texto_saida},
                {"role": "user", "content": repair_prompt},
            ],
        )
        texto_saida = resposta_repair.content[0].text if resposta_repair.content else ""
        saida, erros = validar_saida(texto_saida)

    if saida is None:
        logger.error("Repair falhou. Erros: %s", erros)
        # Não grava dado malformado — registra o erro
        return {
            "sucesso": False,
            "erros": erros,
            "jogo_id": jogo_id,
            "relatorio_id": None,
        }

    # 8. Persistir no banco
    saida_dict = saida_para_dict(saida)
    agora = datetime.now(timezone.utc).isoformat()

    relatorio_id = repo.salvar_relatorio({
        "jogo_id": jogo_id,
        "gerado_em": agora,
        "prompt_versao": PROMPT_VERSAO,
        "modelo_versao": modelo_usado,
        "conteudo": json.dumps(saida_dict, ensure_ascii=False),
        "fatores_avaliados": saida.fatores_avaliados,
        "fatores_ausentes": saida.fatores_ausentes,
    })

    # Persistir previsões individuais
    from src.db.repositorio import EstatisticaJogo
    with repo._conn() as conn:
        for prev in saida.previsoes:
            conn.execute("""
                INSERT INTO previsoes
                    (relatorio_id, jogo_id, mercado, previsao,
                     probabilidade_estimada, probabilidade_calculada_original,
                     incerteza, origem, justificativa, fontes, gerado_em)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                relatorio_id, jogo_id, prev.mercado, prev.previsao,
                prev.probabilidade_estimada, prev.probabilidade_calculada_original,
                prev.incerteza, prev.origem, prev.justificativa,
                json.dumps(prev.fontes, ensure_ascii=False), agora,
            ))

    logger.info("Análise salva: relatorio_id=%d", relatorio_id)

    return {
        "sucesso": True,
        "relatorio_id": relatorio_id,
        "saida": saida,
        "previsao_dc": previsao_dc,
        "mercados_sec": mercados_sec,
        "jogo_id": jogo_id,
    }
