"""
Regenera o banco-semente embarcado na imagem de deploy a partir do banco vivo.

Por que isto existe
-------------------
No plano free do Render o disco é EFÊMERO: quando a instância dorme (~15 min
ocioso) ou reinicia, /data é apagado e o boot recopia `deploy/seed_db/copa_analyst.db`
(ver src/api/main.py::_semear_banco). Se o seed não tiver os resultados já
catalogados, o site volta vazio após cada restart — e o auto-pull no boot, no free
tier do TheSportsDB, é truncado/rate-limited e nem sempre recupera tudo.

A correção durável é manter o SEED atualizado com os resultados reais e versioná-lo.
Rode este script antes de cada deploy (ou depois de catalogar novos resultados):

    python scripts/atualizar_seed.py
    git add deploy/seed_db/copa_analyst.db && git commit -m "chore: atualiza seed com resultados"
    git push   # autoDeploy=true no render.yaml redeploya

Usa VACUUM INTO: gera um snapshot consistente e compactado (sem lixo de WAL),
sem precisar parar quem estiver lendo o banco vivo.
"""

import os
import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
LIVE = Path(os.getenv("COPA_DB_PATH", _ROOT / "dados" / "copa_analyst.db"))
SEED = _ROOT / "deploy" / "seed_db" / "copa_analyst.db"


def _contar(path: Path) -> tuple[int, int, tuple]:
    c = sqlite3.connect(path)
    try:
        tot = c.execute("SELECT COUNT(*) FROM jogos WHERE competicao='copa_2026'").fetchone()[0]
        com = c.execute(
            "SELECT COUNT(*) FROM jogos WHERE competicao='copa_2026' AND placar_mandante IS NOT NULL"
        ).fetchone()[0]
        rng = c.execute(
            "SELECT MIN(data), MAX(data) FROM jogos "
            "WHERE competicao='copa_2026' AND placar_mandante IS NOT NULL"
        ).fetchone()
        return tot, com, rng
    finally:
        c.close()


def main() -> int:
    if not LIVE.exists():
        print(f"ERRO: banco vivo não encontrado em {LIVE}", file=sys.stderr)
        return 1

    tot, com, rng = _contar(LIVE)
    if com == 0:
        print(
            "ABORTADO: o banco vivo não tem nenhum resultado catalogado "
            "(placar_mandante IS NULL em todos os jogos). Recusando gerar um seed vazio.",
            file=sys.stderr,
        )
        return 2

    SEED.parent.mkdir(parents=True, exist_ok=True)
    if SEED.exists():
        SEED.unlink()  # VACUUM INTO falha se o destino já existe

    src = sqlite3.connect(LIVE)
    try:
        src.execute("VACUUM INTO ?", (str(SEED),))
    finally:
        src.close()

    stot, scom, srng = _contar(SEED)
    print(f"Seed regenerado: {SEED}")
    print(f"  vivo:  {tot} jogos | {com} com placar | range {rng}")
    print(f"  seed:  {stot} jogos | {scom} com placar | range {srng}")
    if scom != com:
        print("AVISO: contagem de resultados diverge entre vivo e seed!", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
