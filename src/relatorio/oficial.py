"""
Gestão do relatório oficial — defesa contra data leakage (PRD Seção 9).

Regra de ouro (PRD 9.1 / Decisão 10): para cada jogo existe no máximo UM relatório
com `eh_relatorio_oficial = 1`, e ele tem de ser o último gerado ANTES do apito
inicial. O par (gerado_em < kickoff) é a prova de que a previsão precedeu o resultado.

Este módulo:
  - calcula o horário de apito (kickoff) a partir de data + hora_utc do jogo;
  - `marcar_oficial_seguro`: recusa marcar como oficial um relatório gerado DEPOIS
    do apito (bloqueio anti-leakage);
  - `marcar_oficiais_automatico`: varre os jogos que já começaram e fixa, para cada
    um, o último relatório gerado antes do apito como oficial.

CLI:
    python -m src.relatorio.oficial auto [YYYY-MM-DD]   # fixa oficiais (opcional: só uma data)
    python -m src.relatorio.oficial check <relatorio_id>
"""

import sys
import logging
from datetime import datetime, timezone
from typing import Optional

from src.db.repositorio import Repositorio, Jogo

logger = logging.getLogger(__name__)


def kickoff_utc(jogo: Jogo) -> Optional[datetime]:
    """Datetime UTC do apito a partir de `data` (YYYY-MM-DD) + `hora_utc` (HH:MM)."""
    if not jogo or not jogo.data:
        return None
    hora = jogo.hora_utc or "00:00"
    try:
        return datetime.fromisoformat(f"{jogo.data}T{hora}:00+00:00")
    except ValueError:
        logger.warning("Kickoff inválido para jogo %s: data=%r hora=%r", jogo.id, jogo.data, jogo.hora_utc)
        return None


def _parse_gerado_em(valor: str) -> Optional[datetime]:
    if not valor:
        return None
    try:
        dt = datetime.fromisoformat(valor)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def pode_ser_oficial(repo: Repositorio, relatorio_id: int) -> dict:
    """
    Verifica se um relatório pode ser oficial sem violar o anti-leakage.
    Retorna dict com ok/motivo/kickoff/gerado_em.
    """
    with repo._conn() as conn:
        row = conn.execute(
            "SELECT id, jogo_id, gerado_em FROM relatorios WHERE id = ?", (relatorio_id,)
        ).fetchone()
    if row is None:
        return {"ok": False, "motivo": f"Relatório {relatorio_id} não existe."}

    jogo = repo.buscar_jogo(row["jogo_id"])
    ko = kickoff_utc(jogo)
    gerado = _parse_gerado_em(row["gerado_em"])

    if ko is None:
        # Sem horário de apito não há como provar precedência — permite, mas avisa.
        return {"ok": True, "motivo": "Jogo sem horário de apito — precedência não verificável.",
                "kickoff": None, "gerado_em": row["gerado_em"]}
    if gerado is None:
        return {"ok": False, "motivo": "Timestamp de geração inválido.",
                "kickoff": ko.isoformat(), "gerado_em": row["gerado_em"]}
    if gerado > ko:
        return {"ok": False,
                "motivo": (f"Relatório gerado em {gerado.isoformat()} é POSTERIOR ao apito "
                           f"({ko.isoformat()}). Marcar como oficial violaria o anti-leakage (PRD 9.1)."),
                "kickoff": ko.isoformat(), "gerado_em": row["gerado_em"]}
    return {"ok": True, "motivo": "Relatório precede o apito.",
            "kickoff": ko.isoformat(), "gerado_em": row["gerado_em"]}


def marcar_oficial_seguro(repo: Repositorio, relatorio_id: int) -> dict:
    """
    Marca um relatório como oficial APENAS se ele precede o apito (anti-leakage).
    Retorna {ok, motivo}.
    """
    check = pode_ser_oficial(repo, relatorio_id)
    if not check["ok"]:
        logger.warning("Recusado marcar oficial relatório %s: %s", relatorio_id, check["motivo"])
        return check
    repo.marcar_relatorio_oficial(relatorio_id)
    logger.info("Relatório %s marcado como oficial.", relatorio_id)
    return {"ok": True, "motivo": check["motivo"], "relatorio_id": relatorio_id}


def marcar_oficiais_automatico(repo: Repositorio, data: Optional[str] = None) -> dict:
    """
    Para cada jogo da Copa 2026 que JÁ começou, fixa como oficial o último relatório
    gerado antes do apito. Idempotente. Se `data` for dada (YYYY-MM-DD), limita a ela.

    Retorna resumo {marcados, sem_relatorio_valido, ignorados_futuros, detalhes}.
    """
    agora = datetime.now(timezone.utc)
    jogos = repo.listar_jogos_copa26()
    resumo = {"marcados": 0, "sem_relatorio_valido": 0, "ignorados_futuros": 0, "detalhes": []}

    for jogo in jogos:
        if data and jogo.data != data:
            continue
        ko = kickoff_utc(jogo)
        if ko is None or agora < ko:
            resumo["ignorados_futuros"] += 1
            continue  # ainda não começou (ou sem horário) → não fixar oficial

        with repo._conn() as conn:
            relatorios = conn.execute(
                "SELECT id, gerado_em FROM relatorios WHERE jogo_id = ? ORDER BY gerado_em DESC",
                (jogo.id,),
            ).fetchall()

        # Último relatório com gerado_em <= apito
        escolhido = None
        for r in relatorios:
            g = _parse_gerado_em(r["gerado_em"])
            if g is not None and g <= ko:
                escolhido = r
                break  # já está ordenado desc → o primeiro que passa é o mais recente válido

        if escolhido is None:
            resumo["sem_relatorio_valido"] += 1
            if relatorios:
                resumo["detalhes"].append(
                    f"jogo {jogo.id}: {len(relatorios)} relatório(s), nenhum antes do apito {ko.isoformat()}"
                )
            continue

        repo.marcar_relatorio_oficial(escolhido["id"])
        resumo["marcados"] += 1
        resumo["detalhes"].append(
            f"jogo {jogo.id}: oficial = relatório {escolhido['id']} (gerado {escolhido['gerado_em']})"
        )

    return resumo


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from src.dados.ingestao import _get_repo
    repo = _get_repo()

    cmd = sys.argv[1] if len(sys.argv) > 1 else "auto"

    if cmd == "auto":
        data = sys.argv[2] if len(sys.argv) > 2 else None
        resumo = marcar_oficiais_automatico(repo, data)
        print(f"Oficiais marcados: {resumo['marcados']}")
        print(f"Jogos sem relatório válido antes do apito: {resumo['sem_relatorio_valido']}")
        print(f"Jogos ainda não iniciados (ignorados): {resumo['ignorados_futuros']}")
        for d in resumo["detalhes"]:
            print("  -", d)

    elif cmd == "check" and len(sys.argv) > 2:
        check = pode_ser_oficial(repo, int(sys.argv[2]))
        print("OK" if check["ok"] else "BLOQUEADO", "—", check["motivo"])

    else:
        print("Uso: python -m src.relatorio.oficial [auto [YYYY-MM-DD] | check <relatorio_id>]")


if __name__ == "__main__":
    _main()
