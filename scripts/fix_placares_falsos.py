"""Zera placares da Copa 2026 que vieram do openfootball (fonte errada).
Resultados reais vêm do TheSportsDB via atualizar_resultados_copa26().
"""
import sqlite3

conn = sqlite3.connect("dados/copa_analyst.db")

antes = conn.execute(
    "SELECT COUNT(*) FROM jogos WHERE competicao='copa_2026' AND placar_mandante IS NOT NULL"
).fetchone()[0]
print(f"Jogos Copa 2026 com placar antes: {antes}")

conn.execute(
    "UPDATE jogos SET placar_mandante=NULL, placar_visitante=NULL "
    "WHERE competicao='copa_2026' AND placar_mandante IS NOT NULL"
)
conn.commit()

depois = conn.execute(
    "SELECT COUNT(*) FROM jogos WHERE competicao='copa_2026' AND placar_mandante IS NOT NULL"
).fetchone()[0]
print(f"Jogos Copa 2026 com placar depois: {depois}")
print("Pronto. Resultados reais serão preenchidos pelo TheSportsDB após cada jogo.")
conn.close()
