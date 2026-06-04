"""Smoke test Fase 6 — calibracao e resultado_real."""
import logging
logging.basicConfig(level=logging.WARNING)

from src.dados.ingestao import _get_repo
from src.dados.resultados import preencher_resultado_real_jogo, _resultado_de_placar
from src.validacao.calibracao import calcular_calibracao, MIN_AMOSTRAS_CONFIAVEL

repo = _get_repo()

# --- Teste 1: _resultado_de_placar ---
print("=== Teste 1: conversao placar -> resultado ===")
casos = [
    ("resultado", "vitoria mandante", 2, 0, "vitoria mandante"),
    ("resultado", "empate",           1, 1, "empate"),
    ("resultado", "vitoria visitante",0, 2, "vitoria visitante"),
    ("total_gols","over 2.5",         2, 1, "over"),
    ("total_gols","over 2.5",         1, 1, "under"),
    ("ambas_marcam","sim",            1, 1, "sim"),
    ("ambas_marcam","sim",            1, 0, "nao"),
]
for mercado, previsao, pm, pv, esperado in casos:
    resultado = _resultado_de_placar(pm, pv, mercado, previsao)
    ok = resultado == esperado
    print(f"  {'[OK]' if ok else '[FAIL]'} {mercado} | {pm}-{pv} -> {resultado} (esperado: {esperado})")

# --- Teste 2: calcular_calibracao com banco vazio ---
print("\n=== Teste 2: calibracao com banco vazio ===")
painel = calcular_calibracao(repo)
print(f"  Relatorios oficiais: {painel.total_relatorios_oficiais}")
print(f"  Previsoes avaliadas: {painel.total_previsoes_avaliadas}")
print(f"  Aviso ruido: {painel.aviso_ruido[:60] if painel.aviso_ruido else 'nenhum'}")
assert painel.total_previsoes_avaliadas == 0, "Nao deve ter previsoes avaliadas ainda"

# --- Teste 3: simular previsao + resultado_real ---
print("\n=== Teste 3: previsao mock + resultado_real ===")
from src.ia.validacao import validar_saida
import json, math

# Inserir um relatorio de teste diretamente no banco
jogos = repo.listar_jogos_copa26()
if jogos:
    jogo = jogos[0]

    # Criar relatorio marcado como oficial
    with repo._conn() as conn:
        cur = conn.execute("""
            INSERT INTO relatorios (jogo_id, gerado_em, prompt_versao, modelo_versao,
                conteudo, fatores_avaliados, fatores_ausentes, eh_relatorio_oficial)
            VALUES (?, '2026-06-11T00:00:00Z', 'v1', 'test', '{}', '[]', '[]', 1)
        """, (jogo.id,))
        rel_id = cur.lastrowid

        # Inserir previsao de resultado
        conn.execute("""
            INSERT INTO previsoes (relatorio_id, jogo_id, mercado, previsao,
                probabilidade_estimada, probabilidade_calculada_original,
                incerteza, origem, justificativa, fontes, gerado_em)
            VALUES (?, ?, 'resultado', 'vitoria mandante', 0.55, 0.55,
                    'media', 'calculado', 'Teste', '[]', '2026-06-11T00:00:00Z')
        """, (rel_id, jogo.id))

    # Preencher resultado (mandante venceu 2-1)
    n = preencher_resultado_real_jogo(jogo.id, 2, 1, repo)
    print(f"  Previsoes com resultado_real preenchido: {n}")
    assert n >= 1

    # Calcular calibracao agora com 1 amostra
    painel2 = calcular_calibracao(repo)
    print(f"  Previsoes avaliadas: {painel2.total_previsoes_avaliadas}")
    print(f"  Aviso ruido: {painel2.aviso_ruido[:80]}")
    assert painel2.total_previsoes_avaliadas >= 1
    assert painel2.aviso_ruido  # deve ter aviso de ruido com N=1

    if painel2.por_mercado:
        m = painel2.por_mercado[0]
        # Brier score: previsao 0.55, acertou (resultado=vitoria mandante) -> (0.55-1)^2 = 0.2025
        print(f"  Brier ({m.mercado}): {m.brier_score:.4f} (esperado ~0.20)")
        assert abs(m.brier_score - 0.2025) < 0.01, f"Brier incorreto: {m.brier_score}"

    # Limpar dados de teste
    with repo._conn() as conn:
        conn.execute("DELETE FROM previsoes WHERE relatorio_id = ?", (rel_id,))
        conn.execute("DELETE FROM relatorios WHERE id = ?", (rel_id,))
        conn.execute("UPDATE jogos SET placar_mandante=NULL, placar_visitante=NULL WHERE id=?",
                     (jogo.id,))

print("\n[OK] Fase 6 concluida")
