"""Status completo do banco para audit de prontidao para a Copa."""
import sqlite3, json

conn = sqlite3.connect("dados/copa_analyst.db")
conn.row_factory = sqlite3.Row

print("=" * 60)
print("JOGOS COPA 2026 COM PLACAR (nao deveriam ter ainda)")
print("=" * 60)
total = conn.execute("SELECT COUNT(*) FROM jogos WHERE competicao='copa_2026'").fetchone()[0]
com_placar = conn.execute("SELECT COUNT(*) FROM jogos WHERE competicao='copa_2026' AND placar_mandante IS NOT NULL").fetchone()[0]
print(f"Total fixtures: {total} | Com placar: {com_placar}")
rows = conn.execute("""
    SELECT j.data, j.grupo, j.fase, tm.nome as m, tv.nome as v,
           j.placar_mandante, j.placar_visitante, j.fonte
    FROM jogos j JOIN times tm ON tm.id=j.time_mandante_id JOIN times tv ON tv.id=j.time_visitante_id
    WHERE j.competicao='copa_2026' AND j.placar_mandante IS NOT NULL ORDER BY j.data
""").fetchall()
for r in rows:
    print(f"  {r['data']} | Gr{r['grupo']} | {r['m']} {r['placar_mandante']}-{r['placar_visitante']} {r['v']} | fonte: {r['fonte']}")

print()
print("=" * 60)
print("STATS API-FOOTBALL POR COMPETICAO")
print("=" * 60)
comps = conn.execute("""
    SELECT j.competicao, COUNT(DISTINCT j.id) as fixtures,
           COUNT(DISTINCT e.jogo_id) as com_stats
    FROM jogos j LEFT JOIN estatisticas_jogo e ON e.jogo_id=j.id
    GROUP BY j.competicao ORDER BY j.competicao
""").fetchall()
for c in comps:
    pct = round(c['com_stats']/c['fixtures']*100) if c['fixtures'] else 0
    print(f"  {c['competicao']:<30} {c['fixtures']:>4} fixtures | {c['com_stats']:>4} com stats ({pct}%)")

print()
print("=" * 60)
print("RELATORIOS DE IA NO BANCO")
print("=" * 60)
rels = conn.execute("SELECT COUNT(*) FROM relatorios").fetchone()[0]
oficiais = conn.execute("SELECT COUNT(*) FROM relatorios WHERE eh_relatorio_oficial=1").fetchone()[0]
print(f"  Total relatórios: {rels} | Oficiais: {oficiais}")

print()
print("=" * 60)
print("TIMES - ELO STATUS")
print("=" * 60)
times_total = conn.execute("SELECT COUNT(*) FROM times").fetchone()[0]
com_elo = conn.execute("SELECT COUNT(*) FROM times WHERE rating_prior IS NOT NULL AND rating_prior != 1500").fetchone()[0]
elo_1500 = conn.execute("SELECT COUNT(*) FROM times WHERE rating_prior=1500").fetchone()[0]
print(f"  Total times: {times_total} | Com Elo calculado: {com_elo} | Default 1500: {elo_1500}")

# Times da Copa 2026 com elo 1500 (cold start total)
cold = conn.execute("""
    SELECT DISTINCT t.nome, t.rating_prior
    FROM times t
    JOIN jogos j ON (j.time_mandante_id=t.id OR j.time_visitante_id=t.id)
    WHERE j.competicao='copa_2026' AND t.rating_prior=1500 AND t.nome NOT LIKE '%1%'
    AND t.nome NOT LIKE 'W%' AND t.nome NOT LIKE 'L%'
    ORDER BY t.nome
""").fetchall()
print(f"  Times Copa 2026 com Elo=1500 (cold start): {len(cold)}")
for c in cold:
    print(f"    - {c['nome']}")

conn.close()
