"""Remove duplicatas do banco mantendo o menor ID de cada grupo único."""
import sqlite3

conn = sqlite3.connect("dados/copa_analyst.db")

total_antes = conn.execute("SELECT COUNT(*) FROM jogos").fetchone()[0]
copa26_antes = conn.execute("SELECT COUNT(*) FROM jogos WHERE competicao='copa_2026'").fetchone()[0]
print(f"Antes: {total_antes} jogos total, {copa26_antes} copa_2026")

conn.execute("""
    DELETE FROM jogos
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM jogos
        WHERE id_externo IS NULL
        GROUP BY competicao, data, time_mandante_id, time_visitante_id
    )
    AND id_externo IS NULL
""")
conn.commit()

total_depois = conn.execute("SELECT COUNT(*) FROM jogos").fetchone()[0]
copa26_depois = conn.execute("SELECT COUNT(*) FROM jogos WHERE competicao='copa_2026'").fetchone()[0]
print(f"Depois: {total_depois} jogos total, {copa26_depois} copa_2026")
conn.close()
print("Limpeza concluída.")
