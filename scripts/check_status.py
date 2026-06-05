"""Verifica o estado completo do banco para o documento de status."""
from src.dados.ingestao import _get_repo
repo = _get_repo()

with repo._conn() as conn:
    times_copa26 = conn.execute("""
        SELECT DISTINCT t.nome, t.rating_prior,
            (SELECT COUNT(*) FROM estatisticas_jogo e
             JOIN jogos j2 ON j2.id=e.jogo_id
             WHERE e.time_id=t.id AND j2.competicao IN ('copa_2022','copa_2026')) as n_stats
        FROM times t
        JOIN jogos j ON (j.time_mandante_id=t.id OR j.time_visitante_id=t.id)
        WHERE j.competicao='copa_2026'
        ORDER BY n_stats DESC, t.nome
    """).fetchall()

    jogos_copa22_sem_stats = conn.execute("""
        SELECT COUNT(*) FROM jogos j
        WHERE j.competicao='copa_2022' AND j.placar_mandante IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM estatisticas_jogo e WHERE e.jogo_id=j.id)
    """).fetchone()[0]

    jogos_elim_sem_stats = conn.execute("""
        SELECT competicao, COUNT(*) as n FROM jogos j
        WHERE j.competicao LIKE 'elim_%' AND j.placar_mandante IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM estatisticas_jogo e WHERE e.jogo_id=j.id)
        GROUP BY competicao ORDER BY n DESC
    """).fetchall()

com_stats = [t for t in times_copa26 if t[2] > 0]
sem_stats  = [t for t in times_copa26 if t[2] == 0]

print(f"Times Copa 2026 com stats de Copa: {len(com_stats)}/{len(times_copa26)}")
print(f"Com stats: {[t[0] for t in com_stats]}")
print(f"\nSem stats ({len(sem_stats)} times):")
for t in sem_stats:
    elo_str = f"{t[1]:.0f}" if t[1] else "N/A"
    print(f"  {t[0]:25s} Elo={elo_str}")

print(f"\nJogos Copa 2022 ainda sem stats: {jogos_copa22_sem_stats} (cada um = 1 request)")
print("\nJogos de eliminatórias sem stats por competição:")
total_elim = 0
for r in jogos_elim_sem_stats:
    print(f"  {r[0]:40s}: {r[1]} jogos")
    total_elim += r[1]

print(f"\nTotal requests ainda necessários para stats completas:")
print(f"  Copa 2022 faltando:         {jogos_copa22_sem_stats} requests")
print(f"  Eliminatórias (fixtures):   {len(jogos_elim_sem_stats)} requests (1 por competição para listar)")
print(f"  Stats por jogo eliminat.:   ~{total_elim} requests (1 por jogo)")
print(f"  TOTAL estimado:             ~{jogos_copa22_sem_stats + len(jogos_elim_sem_stats) + total_elim} requests")
print(f"  Com 100/dia:                ~{((jogos_copa22_sem_stats + total_elim) // 85) + 1} dias")
