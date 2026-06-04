"""
Popula o banco com dados mock para testar todas as features da interface.
Cria: 1 relatorio oficial + previsoes + resultado_real para Brasil x Marrocos.
"""
import json, logging, sys
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from src.dados.ingestao import _get_repo, pacote_jogo
from src.ia.sintese import analisar_jogo
from src.dados.resultados import preencher_resultado_real_jogo

repo = _get_repo()

# Encontrar Brasil x Marrocos
jogos = repo.listar_jogos_copa26()
jogo_alvo = None
for j in jogos:
    tm = repo.buscar_time(j.time_mandante_id)
    tv = repo.buscar_time(j.time_visitante_id)
    if tm and tv and "Brazil" in tm.nome:
        jogo_alvo = j
        print(f"Jogo alvo: {tm.nome} x {tv.nome} ({j.data}) — id={j.id}")
        break

if not jogo_alvo:
    jogo_alvo = jogos[0]
    tm = repo.buscar_time(jogo_alvo.time_mandante_id)
    tv = repo.buscar_time(jogo_alvo.time_visitante_id)
    print(f"Usando: {tm.nome if tm else '?'} x {tv.nome if tv else '?'} ({jogo_alvo.data})")

print("Gerando analise com MOCK_AI=true...")
resultado = analisar_jogo(jogo_alvo.id, repo)

if not resultado["sucesso"]:
    print(f"ERRO: {resultado.get('erros')}")
    sys.exit(1)

rel_id = resultado["relatorio_id"]
print(f"Relatorio criado: id={rel_id}")

# Marcar como oficial
repo.marcar_relatorio_oficial(rel_id)
print("Marcado como oficial.")

# Simular resultado (Brasil ganhou 2-1)
n = preencher_resultado_real_jogo(jogo_alvo.id, 2, 1, repo)
print(f"Resultado_real preenchido em {n} previsoes.")

# Criar mais 2 relatorios para outros jogos (sem resultado — futuros)
for j in jogos[1:4]:
    tm = repo.buscar_time(j.time_mandante_id)
    tv = repo.buscar_time(j.time_visitante_id)
    if not tm or not tv:
        continue
    r = analisar_jogo(j.id, repo)
    if r["sucesso"]:
        print(f"Relatorio criado para {tm.nome} x {tv.nome}: id={r['relatorio_id']}")

print("\nDados mock prontos. Pode iniciar o Streamlit.")
