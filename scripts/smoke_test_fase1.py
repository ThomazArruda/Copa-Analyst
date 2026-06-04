"""Smoke test da Fase 1 — verifica banco e rating prior."""
import logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

from src.dados.ingestao import _get_repo
from src.modelos.rating_prior import RatingPrior

repo = _get_repo()

# Contagem por competição
with repo._conn() as conn:
    rows = conn.execute(
        "SELECT competicao, COUNT(*) as n FROM jogos GROUP BY competicao ORDER BY n DESC"
    ).fetchall()

print("=== JOGOS POR COMPETICAO ===")
total = 0
for r in rows:
    print(f"  {r['competicao']:40s}: {r['n']:4d}")
    total += r["n"]
print(f"  {'TOTAL':40s}: {total:4d}")

# Copa 2026 amostra
jogos26 = repo.listar_jogos_copa26()
print(f"\n=== COPA 2026: {len(jogos26)} fixtures ===")
for j in jogos26[:6]:
    m = repo.buscar_time(j.time_mandante_id)
    v = repo.buscar_time(j.time_visitante_id)
    print(f"  {j.data} | Grupo {j.grupo} | {m.nome} vs {v.nome} | {j.cidade}")

# Rating prior
rp = RatingPrior(repo)
rp.calcular_e_salvar()
times = sorted(repo.listar_times(), key=lambda t: t.rating_prior or 0, reverse=True)
print("\n=== TOP 15 RATING PRIOR (Elo calculado) ===")
for t in times[:15]:
    print(f"  {t.nome:25s}: {t.rating_prior:.0f}")

# Entregável da Fase 1
print("\n=== ENTREGAVEL FASE 1 ===")
brasil = repo.buscar_time_por_nome("Brazil")
if brasil:
    forma = repo.jogos_de_time(brasil.id, limite=5)
    print(f"Forma recente Brasil ({len(forma)} jogos):")
    for j in forma:
        m = repo.buscar_time(j.time_mandante_id)
        v = repo.buscar_time(j.time_visitante_id)
        print(f"  {j.data} | {m.nome} {j.placar_mandante}-{j.placar_visitante} {v.nome} | {j.competicao}")
print("\n[OK] Fase 1 concluida")
