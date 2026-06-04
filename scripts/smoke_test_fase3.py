"""Smoke test Fase 3 — validação pydantic + digest email."""
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# -----------------------------------------------------------------------
# Teste 1: Validação pydantic (PRD 6.8)
# -----------------------------------------------------------------------
print("=== TESTE 1: Validacao pydantic ===")
from src.ia.validacao import validar_saida, BANDA_AJUSTE
import json

casos = [
    ("JSON invalido", "isso nao e json", False),
    ("calculado valido", json.dumps({
        "resumo_executivo": "Jogo equilibrado.",
        "fatores_avaliados": ["elo", "dixon-coles"],
        "fatores_ausentes": [],
        "previsoes": [{
            "mercado": "resultado",
            "previsao": "vitoria mandante",
            "probabilidade_estimada": 0.55,
            "probabilidade_calculada_original": 0.55,
            "incerteza": "media",
            "origem": "calculado",
            "justificativa": "Elo superior.",
            "fontes": ["dixon-coles"]
        }]
    }), True),
    ("hibrido dentro da banda", json.dumps({
        "resumo_executivo": "Lesao do artilheiro reduz ataque.",
        "fatores_avaliados": ["elo", "lesao"],
        "fatores_ausentes": ["escalacao nao confirmada"],
        "previsoes": [{
            "mercado": "resultado",
            "previsao": "vitoria mandante",
            "probabilidade_estimada": 0.48,
            "probabilidade_calculada_original": 0.55,
            "incerteza": "media",
            "origem": "hibrido",
            "justificativa": "Rebaixado 7pp por lesao do artilheiro.",
            "fontes": ["dixon-coles", "fonte-noticia"]
        }]
    }), True),
    ("hibrido fora da banda (deve virar qualitativo)", json.dumps({
        "resumo_executivo": "Ajuste muito grande.",
        "fatores_avaliados": ["elo"],
        "fatores_ausentes": [],
        "previsoes": [{
            "mercado": "resultado",
            "previsao": "vitoria mandante",
            "probabilidade_estimada": 0.30,
            "probabilidade_calculada_original": 0.55,
            "incerteza": "media",
            "origem": "hibrido",
            "justificativa": "Ajuste de 25pp.",
            "fontes": []
        }]
    }), True),  # deve validar mas virar qualitativo
    ("mercado invalido", json.dumps({
        "resumo_executivo": "X",
        "fatores_avaliados": [],
        "fatores_ausentes": [],
        "previsoes": [{
            "mercado": "gols_do_jogador",  # invalido
            "previsao": "x",
            "probabilidade_estimada": 0.5,
            "probabilidade_calculada_original": 0.5,
            "incerteza": "baixa",
            "origem": "calculado",
            "justificativa": "x",
            "fontes": []
        }]
    }), False),
]

for nome, entrada, esperado_ok in casos:
    saida, erros = validar_saida(entrada)
    ok = saida is not None
    status = "[OK]" if ok == esperado_ok else "[FAIL]"
    detalhe = ""
    if ok and nome == "hibrido fora da banda (deve virar qualitativo)":
        origem_resultado = saida.previsoes[0].origem
        detalhe = f" -> origem={origem_resultado} (esperado: qualitativo)"
        assert origem_resultado == "qualitativo", f"Deveria ter virado qualitativo: {origem_resultado}"
    print(f"  {status} {nome}{detalhe}")
    if erros and not ok:
        print(f"       Erros: {erros[:1]}")

# -----------------------------------------------------------------------
# Teste 2: Digest email (sem envio real)
# -----------------------------------------------------------------------
print("\n=== TESTE 2: Digest email HTML ===")
from src.relatorio.email_diario import gerar_html_digest, _calcular_prev_jogo, enviar_digest_diario
from src.dados.ingestao import _get_repo

repo = _get_repo()
jogos = repo.listar_jogos_copa26()

# Pegar o primeiro jogo disponível
jogo = jogos[0] if jogos else None
if jogo:
    time_m = repo.buscar_time(jogo.time_mandante_id)
    time_v = repo.buscar_time(jogo.time_visitante_id)
    print(f"  Calculando previsao para: {time_m.nome if time_m else '?'} x {time_v.nome if time_v else '?'}")
    info = _calcular_prev_jogo(jogo.id, repo)
    if info:
        print(f"  Tendencias: {info['tendencias'] or ['(nenhuma tendencia clara)']}")
        html = gerar_html_digest(jogo.data, [info])
        assert "<html>" in html
        assert len(html) > 1000
        print(f"  HTML gerado: {len(html)} chars [OK]")

# Testar digest completo do dia 1 da Copa (sem enviar email)
data_teste = "2026-06-11"
jogos_dia = [j for j in jogos if j.data == data_teste]
print(f"\n  Jogos em {data_teste}: {len(jogos_dia)}")

if jogos_dia:
    infos = [_calcular_prev_jogo(j.id, repo) for j in jogos_dia]
    infos = [i for i in infos if i]
    interessantes = [i for i in infos if i["interessante"]]
    html = gerar_html_digest(data_teste, infos)
    print(f"  {len(infos)} previsoes calculadas, {len(interessantes)} com tendencia clara")
    print(f"  HTML gerado: {len(html)} chars [OK]")

    # Salvar para inspecao visual
    import os
    os.makedirs("relatorios", exist_ok=True)
    with open(f"relatorios/digest_{data_teste}_teste.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Salvo em relatorios/digest_{data_teste}_teste.html")

    for i in infos:
        prev = i["previsao"]
        tags = i["tendencias"]
        tag_str = " | ".join(tags) if tags else "sem tendencia"
        print(f"  {i['mandante']:20s} vs {i['visitante']:20s} "
              f"| {prev.prob_vitoria_m:.0%}/{prev.prob_empate:.0%}/{prev.prob_vitoria_v:.0%} "
              f"| {tag_str}")

print("\n[OK] Fase 3 concluida")
