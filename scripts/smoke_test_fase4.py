"""Smoke test Fase 4 — gerador HTML de relatório."""
import json, logging, os
logging.basicConfig(level=logging.WARNING)

from src.dados.ingestao import _get_repo, pacote_jogo
from src.modelos.dixon_coles import DixonColes
from src.modelos.mercados import calcular_mercados_secundarios
from src.ia.validacao import SaidaIA, validar_saida
from src.relatorio.gerador import gerar_html_relatorio, salvar_relatorio

repo = _get_repo()
jogos = repo.listar_jogos_copa26()
assert jogos, "Nenhum jogo Copa 2026 no banco"

# Usar jogo Brasil × Marrocos como teste
jogo_br = next(
    (j for j in jogos
     if repo.buscar_time(j.time_mandante_id) and
        "Brazil" in (repo.buscar_time(j.time_mandante_id).nome or "")),
    jogos[0]
)

time_m = repo.buscar_time(jogo_br.time_mandante_id)
time_v = repo.buscar_time(jogo_br.time_visitante_id)
print(f"Gerando relatório: {time_m.nome} × {time_v.nome}")

# Síntese mock
saida_mock_json = json.dumps({
    "resumo_executivo": (
        f"{time_m.nome} entra como favorito com Elo superior, mas enfrenta um "
        f"{time_v.nome} sólido defensivamente. Previsão baseada principalmente no "
        "rating Elo — cold start, poucas partidas de Copa disponíveis."
    ),
    "fatores_avaliados": [
        "Rating Elo (prior)", "Dixon-Coles (cold start)", "Forma recente CONMEBOL 2026"
    ],
    "fatores_ausentes": [
        "Escalação não confirmada (modo mock)",
        "Árbitro designado desconhecido",
        "Dados de escanteios do Marrocos insuficientes"
    ],
    "previsoes": [
        {
            "mercado": "resultado",
            "previsao": f"vitória {time_m.nome}",
            "probabilidade_estimada": 0.54,
            "probabilidade_calculada_original": 0.54,
            "incerteza": "media",
            "origem": "calculado",
            "justificativa": f"{time_m.nome} tem Elo superior em ~62 pontos. Cold start: parâmetros baseados no prior.",
            "fontes": ["dixon-coles-v1", "elo-copa-2022"]
        },
        {
            "mercado": "total_gols",
            "previsao": "over 1.5",
            "probabilidade_estimada": 0.74,
            "probabilidade_calculada_original": 0.74,
            "incerteza": "media",
            "origem": "calculado",
            "justificativa": "Gols esperados: 1.80 + 1.03 = 2.83. Over 1.5 bem sustentado.",
            "fontes": ["dixon-coles-v1"]
        },
        {
            "mercado": "ambas_marcam",
            "previsao": "sim",
            "probabilidade_estimada": 0.58,
            "probabilidade_calculada_original": 0.58,
            "incerteza": "media",
            "origem": "calculado",
            "justificativa": "Ambos os times têm gols esperados > 0.8.",
            "fontes": ["dixon-coles-v1"]
        },
        {
            "mercado": "escanteios",
            "previsao": "over 8.5",
            "probabilidade_estimada": 0.42,
            "probabilidade_calculada_original": None,
            "incerteza": "alta",
            "origem": "qualitativo",
            "justificativa": "Baseado em médias Copa 2022. Dados de escanteios do Marrocos escassos — incerteza alta.",
            "fontes": ["api-football-copa2022"]
        },
        {
            "mercado": "cartoes_amarelos",
            "previsao": "over 2.5",
            "probabilidade_estimada": 0.35,
            "probabilidade_calculada_original": 0.30,
            "incerteza": "alta",
            "origem": "hibrido",
            "justificativa": "Modelo base: 30%. Ajustado +5pp por jogo de fase de grupos com alta pressão.",
            "fontes": ["dixon-coles-v1", "contexto-fase-grupo"]
        }
    ]
})

saida, erros = validar_saida(saida_mock_json)
assert saida is not None, f"Validação falhou: {erros}"

# Montar resultado_analise simulado
resultado = {
    "sucesso": True,
    "relatorio_id": None,
    "saida": saida,
    "jogo_id": jogo_br.id,
}

# Gerar HTML
html = gerar_html_relatorio(resultado, repo)
assert "<html" in html and len(html) > 3000
print(f"HTML gerado: {len(html):,} chars")

# Salvar
caminho = salvar_relatorio(resultado, repo)
print(f"Salvo em: {caminho}")

# Verificações básicas
assert time_m.nome in html
assert time_v.nome in html
assert "Calculado" in html
assert "Qualitativo" in html
assert "Híbrido" in html or "brido" in html
assert "Fatores NÃO avaliados" in html or "avaliados" in html
print("[OK] Fase 4 concluida")
