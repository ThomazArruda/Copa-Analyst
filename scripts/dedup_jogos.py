"""
Remove jogos duplicados. Um jogo real é único por (data, par de times) —
duas seleções não jogam duas vezes no mesmo dia. Isso captura duplicatas que
escapam da chave por competição:
  - mesmo jogo em rótulos diferentes (elim_uefa_2024 API × elim_uefa_2026 Wikipedia)
  - repescagens inter-confederação listadas em CONCACAF + AFC + CAF
  - orientação mandante/visitante trocada entre fontes
Mantém o sobrevivente com mais estatísticas (preserva dados), re-aponta stats,
apaga os demais. Só toca jogos com placar (não mexe nas fixtures futuras da Copa).
Idempotente.
"""
import os
import sqlite3

db = os.getenv("COPA_DB_PATH", "dados/copa_analyst.db")
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

antes = conn.execute("SELECT COUNT(*) FROM jogos").fetchone()[0]

grupos = conn.execute("""
    SELECT data,
           MIN(time_mandante_id, time_visitante_id) a,
           MAX(time_mandante_id, time_visitante_id) b,
           COUNT(*) n
    FROM jogos
    WHERE placar_mandante IS NOT NULL AND data IS NOT NULL AND data != ''
      AND time_mandante_id IS NOT NULL AND time_visitante_id IS NOT NULL
    GROUP BY data, a, b
    HAVING n > 1
""").fetchall()

def n_stats(jid):
    return conn.execute("SELECT COUNT(*) FROM estatisticas_jogo WHERE jogo_id=?", (jid,)).fetchone()[0]

removidos = 0
for g in grupos:
    rows = conn.execute("""
        SELECT id FROM jogos
        WHERE data=? AND placar_mandante IS NOT NULL
          AND MIN(time_mandante_id, time_visitante_id)=?
          AND MAX(time_mandante_id, time_visitante_id)=?
        ORDER BY id
    """, (g["data"], g["a"], g["b"])).fetchall()
    ids = [r["id"] for r in rows]
    survivor = max(ids, key=lambda j: (n_stats(j), -j))  # mais stats; empate → menor id

    for jid in ids:
        if jid == survivor:
            continue
        for s in conn.execute("SELECT id, time_id FROM estatisticas_jogo WHERE jogo_id=?", (jid,)).fetchall():
            ja = conn.execute("SELECT 1 FROM estatisticas_jogo WHERE jogo_id=? AND time_id=?",
                              (survivor, s["time_id"])).fetchone()
            if ja:
                conn.execute("DELETE FROM estatisticas_jogo WHERE id=?", (s["id"],))
            else:
                conn.execute("UPDATE estatisticas_jogo SET jogo_id=? WHERE id=?", (survivor, s["id"]))
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
restantes = conn.execute("""SELECT COUNT(*) FROM (SELECT 1 FROM jogos
    WHERE placar_mandante IS NOT NULL AND data IS NOT NULL AND data!=''
    GROUP BY data, MIN(time_mandante_id,time_visitante_id), MAX(time_mandante_id,time_visitante_id)
    HAVING COUNT(*)>1)""").fetchone()[0]
print(f"Grupos duplicados: {len(grupos)} | removidos: {removidos}")
print(f"Jogos: {antes} -> {depois} | duplicatas restantes: {restantes}")
conn.close()
