"""Verifica estado do banco."""
from src.dados.ingestao import _get_repo
repo = _get_repo()

with repo._conn() as conn:
    total = conn.execute(
        "SELECT COUNT(*) FROM jogos WHERE competicao='copa_2022' AND placar_mandante IS NOT NULL"
    ).fetchone()[0]
    print(f"Copa 2022 com placar: {total}")

br = repo.buscar_time_por_nome("Brazil")
if br:
    jogos = repo.jogos_de_time(br.id, competicoes=["copa_2022"])
    print(f"Brasil Copa 2022 ({len(jogos)} jogos):")
    for j in jogos:
        m = repo.buscar_time(j.time_mandante_id)
        v = repo.buscar_time(j.time_visitante_id)
        print(f"  {j.data} | {m.nome} {j.placar_mandante}-{j.placar_visitante} {v.nome}")
