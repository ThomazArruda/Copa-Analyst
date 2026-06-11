"""
Remove jogos duplicados (mesma competição+data+mandante+visitante vindos de
fontes diferentes: openfootball sem id_externo × API-Football com stats).
Mantém um sobrevivente por grupo, re-aponta estatísticas, apaga os demais.
Idempotente.
"""
import os
import sqlite3

db = os.getenv("COPA_DB_PATH", "dados/copa_analyst.db")
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

antes = conn.execute("SELECT COUNT(*) FROM jogos").fetchone()[0]

grupos = conn.execute("""
    SELECT competicao, data, time_mandante_id, time_visitante_id, COUNT(*) n
    FROM jogos
    GROUP BY competicao, data, time_mandante_id, time_visitante_id
    HAVING n > 1
""").fetchall()

removidos = 0
for g in grupos:
    rows = conn.execute("""
        SELECT id FROM jogos
        WHERE competicao=? AND data=? AND time_mandante_id=? AND time_visitante_id=?
        ORDER BY id
    """, (g["competicao"], g["data"], g["time_mandante_id"], g["time_visitante_id"])).fetchall()
    ids = [r["id"] for r in rows]

    # Sobrevivente = o que tem mais estatísticas (preserva dados); empate → menor id
    def n_stats(jid):
        return conn.execute("SELECT COUNT(*) FROM estatisticas_jogo WHERE jogo_id=?", (jid,)).fetchone()[0]
    survivor = max(ids, key=lambda j: (n_stats(j), -j))

    for jid in ids:
        if jid == survivor:
            continue
        # Re-aponta estatísticas que o sobrevivente ainda não tem (por time_id)
        for s in conn.execute("SELECT id, time_id FROM estatisticas_jogo WHERE jogo_id=?", (jid,)).fetchall():
            ja = conn.execute(
                "SELECT 1 FROM estatisticas_jogo WHERE jogo_id=? AND time_id=?",
                (survivor, s["time_id"])).fetchone()
            if ja:
                conn.execute("DELETE FROM estatisticas_jogo WHERE id=?", (s["id"],))
            else:
                conn.execute("UPDATE estatisticas_jogo SET jogo_id=? WHERE id=?", (survivor, s["id"]))
        # Preenche id_externo/placar no sobrevivente se faltar
        conn.execute("""
            UPDATE jogos SET
                id_externo = COALESCE(id_externo, (SELECT id_externo FROM jogos WHERE id=?)),
                placar_mandante = COALESCE(placar_mandante, (SELECT placar_mandante FROM jogos WHERE id=?)),
                placar_visitante = COALESCE(placar_visitante, (SELECT placar_visitante FROM jogos WHERE id=?))
            WHERE id=?
        """, (jid, jid, jid, survivor))
        conn.execute("DELETE FROM jogos WHERE id=?", (jid,))
        removidos += 1

conn.commit()
depois = conn.execute("SELECT COUNT(*) FROM jogos").fetchone()[0]
print(f"Grupos duplicados: {len(grupos)} | jogos removidos: {removidos}")
print(f"Jogos: {antes} -> {depois}")
conn.close()
