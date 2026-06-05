"""
Camada de acesso ao banco SQLite.
Toda leitura e escrita no banco passa por aqui — nunca acesso direto de outros módulos.
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Dataclasses (espelham as tabelas principais)
# ---------------------------------------------------------------------------

@dataclass
class Time:
    id: Optional[int]
    nome: str
    codigo_fifa: Optional[str] = None
    grupo_copa26: Optional[str] = None
    confederacao: Optional[str] = None
    rating_prior: Optional[float] = None
    rating_prior_atualizado_em: Optional[str] = None


@dataclass
class Jogo:
    id: Optional[int]
    competicao: str
    data: str
    hora_utc: Optional[str]
    time_mandante_id: Optional[int]
    time_visitante_id: Optional[int]
    campo_neutro: int = 1
    fase: Optional[str] = None
    grupo: Optional[str] = None
    estadio: Optional[str] = None
    cidade: Optional[str] = None
    altitude_m: Optional[float] = None
    placar_mandante: Optional[int] = None
    placar_visitante: Optional[int] = None
    id_externo: Optional[str] = None
    fonte: Optional[str] = None


@dataclass
class EstatisticaJogo:
    jogo_id: int
    time_id: int
    gols: Optional[int] = None
    escanteios: Optional[int] = None
    chutes: Optional[int] = None
    chutes_no_alvo: Optional[int] = None
    faltas: Optional[int] = None
    cartoes_amarelos: Optional[int] = None
    cartoes_vermelhos: Optional[int] = None
    posse: Optional[float] = None
    xg: Optional[float] = None
    fonte: Optional[str] = None


# ---------------------------------------------------------------------------
# Repositório
# ---------------------------------------------------------------------------

class Repositorio:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self):
        schema_path = Path(__file__).parent / "schema.sql"
        with self._conn() as conn:
            conn.executescript(schema_path.read_text(encoding="utf-8"))

    # --- Times ---

    def upsert_time(self, time: Time) -> int:
        with self._conn() as conn:
            cur = conn.execute("""
                INSERT INTO times (nome, codigo_fifa, grupo_copa26, confederacao,
                                   rating_prior, rating_prior_atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(nome) DO UPDATE SET
                    codigo_fifa                = excluded.codigo_fifa,
                    grupo_copa26               = excluded.grupo_copa26,
                    confederacao               = excluded.confederacao,
                    rating_prior               = COALESCE(excluded.rating_prior, rating_prior),
                    rating_prior_atualizado_em = COALESCE(excluded.rating_prior_atualizado_em, rating_prior_atualizado_em)
            """, (time.nome, time.codigo_fifa, time.grupo_copa26, time.confederacao,
                  time.rating_prior, time.rating_prior_atualizado_em))
            if cur.lastrowid:
                return cur.lastrowid
            row = conn.execute("SELECT id FROM times WHERE nome = ?", (time.nome,)).fetchone()
            return row["id"]

    def buscar_time_por_nome(self, nome: str) -> Optional[Time]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM times WHERE nome = ?", (nome,)).fetchone()
            return self._row_to_time(row) if row else None

    def buscar_time(self, time_id: int) -> Optional[Time]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM times WHERE id = ?", (time_id,)).fetchone()
            return self._row_to_time(row) if row else None

    def listar_times(self) -> list[Time]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM times ORDER BY nome").fetchall()
            return [self._row_to_time(r) for r in rows]

    def _row_to_time(self, row) -> Time:
        return Time(
            id=row["id"], nome=row["nome"], codigo_fifa=row["codigo_fifa"],
            grupo_copa26=row["grupo_copa26"], confederacao=row["confederacao"],
            rating_prior=row["rating_prior"],
            rating_prior_atualizado_em=row["rating_prior_atualizado_em"],
        )

    # --- Jogos ---

    def upsert_jogo(self, jogo: Jogo) -> int:
        with self._conn() as conn:
            # Deduplicação por id_externo (fontes com ID externo definido)
            if jogo.id_externo and jogo.competicao:
                row = conn.execute(
                    "SELECT id FROM jogos WHERE id_externo = ? AND competicao = ?",
                    (jogo.id_externo, jogo.competicao)
                ).fetchone()
                if row:
                    conn.execute("""
                        UPDATE jogos SET placar_mandante=?, placar_visitante=?
                        WHERE id = ?
                    """, (jogo.placar_mandante, jogo.placar_visitante, row["id"]))
                    return row["id"]

            # Deduplicação por combinação natural quando não há id_externo (ex: openfootball)
            if not jogo.id_externo and jogo.competicao and jogo.time_mandante_id and jogo.time_visitante_id:
                row = conn.execute("""
                    SELECT id FROM jogos
                    WHERE competicao = ? AND data = ? AND time_mandante_id = ? AND time_visitante_id = ?
                """, (jogo.competicao, jogo.data, jogo.time_mandante_id, jogo.time_visitante_id)).fetchone()
                if row:
                    conn.execute("""
                        UPDATE jogos SET hora_utc=?, campo_neutro=?, fase=?, grupo=?, cidade=?,
                                         altitude_m=?, placar_mandante=?, placar_visitante=?, fonte=?
                        WHERE id = ?
                    """, (jogo.hora_utc, jogo.campo_neutro, jogo.fase, jogo.grupo, jogo.cidade,
                          jogo.altitude_m, jogo.placar_mandante, jogo.placar_visitante, jogo.fonte,
                          row["id"]))
                    return row["id"]

            cur = conn.execute("""
                INSERT INTO jogos (competicao, data, hora_utc, time_mandante_id, time_visitante_id,
                                   campo_neutro, fase, grupo, estadio, cidade, altitude_m,
                                   placar_mandante, placar_visitante, id_externo, fonte)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (jogo.competicao, jogo.data, jogo.hora_utc, jogo.time_mandante_id,
                  jogo.time_visitante_id, jogo.campo_neutro, jogo.fase, jogo.grupo,
                  jogo.estadio, jogo.cidade, jogo.altitude_m, jogo.placar_mandante,
                  jogo.placar_visitante, jogo.id_externo, jogo.fonte))
            return cur.lastrowid

    def buscar_jogo(self, jogo_id: int) -> Optional[Jogo]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM jogos WHERE id = ?", (jogo_id,)).fetchone()
            return self._row_to_jogo(row) if row else None

    def listar_jogos_copa26(self) -> list[Jogo]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM jogos WHERE competicao = 'copa_2026' ORDER BY data, hora_utc"
            ).fetchall()
            return [self._row_to_jogo(r) for r in rows]

    def jogos_de_time(self, time_id: int, competicoes: list[str] = None,
                      limite: int = 15) -> list[Jogo]:
        """Últimos N jogos de um time (para cálculo de forma)."""
        params: list = [time_id, time_id]
        filtro = ""
        if competicoes:
            ph = ",".join("?" * len(competicoes))
            filtro = f"AND competicao IN ({ph})"
            params.extend(competicoes)
        params.append(limite)
        with self._conn() as conn:
            rows = conn.execute(f"""
                SELECT * FROM jogos
                WHERE (time_mandante_id = ? OR time_visitante_id = ?)
                  AND placar_mandante IS NOT NULL
                  {filtro}
                ORDER BY data DESC, hora_utc DESC
                LIMIT ?
            """, params).fetchall()
            return [self._row_to_jogo(r) for r in rows]

    def head_to_head(self, time_a_id: int, time_b_id: int, limite: int = 10) -> list[Jogo]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM jogos
                WHERE ((time_mandante_id = ? AND time_visitante_id = ?)
                    OR (time_mandante_id = ? AND time_visitante_id = ?))
                  AND placar_mandante IS NOT NULL
                ORDER BY data DESC
                LIMIT ?
            """, (time_a_id, time_b_id, time_b_id, time_a_id, limite)).fetchall()
            return [self._row_to_jogo(r) for r in rows]

    def _row_to_jogo(self, row) -> Jogo:
        return Jogo(
            id=row["id"], competicao=row["competicao"], data=row["data"],
            hora_utc=row["hora_utc"], time_mandante_id=row["time_mandante_id"],
            time_visitante_id=row["time_visitante_id"], campo_neutro=row["campo_neutro"],
            fase=row["fase"], grupo=row["grupo"], estadio=row["estadio"],
            cidade=row["cidade"], altitude_m=row["altitude_m"],
            placar_mandante=row["placar_mandante"], placar_visitante=row["placar_visitante"],
            id_externo=row["id_externo"], fonte=row["fonte"],
        )

    # --- Estatísticas ---

    def upsert_estatistica(self, est: EstatisticaJogo):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO estatisticas_jogo
                    (jogo_id, time_id, gols, escanteios, chutes, chutes_no_alvo,
                     faltas, cartoes_amarelos, cartoes_vermelhos, posse, xg, fonte)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(jogo_id, time_id) DO UPDATE SET
                    gols              = COALESCE(excluded.gols, gols),
                    escanteios        = COALESCE(excluded.escanteios, escanteios),
                    chutes            = COALESCE(excluded.chutes, chutes),
                    chutes_no_alvo    = COALESCE(excluded.chutes_no_alvo, chutes_no_alvo),
                    faltas            = COALESCE(excluded.faltas, faltas),
                    cartoes_amarelos  = COALESCE(excluded.cartoes_amarelos, cartoes_amarelos),
                    cartoes_vermelhos = COALESCE(excluded.cartoes_vermelhos, cartoes_vermelhos),
                    posse             = COALESCE(excluded.posse, posse),
                    xg                = COALESCE(excluded.xg, xg),
                    fonte             = COALESCE(excluded.fonte, fonte)
            """, (est.jogo_id, est.time_id, est.gols, est.escanteios, est.chutes,
                  est.chutes_no_alvo, est.faltas, est.cartoes_amarelos,
                  est.cartoes_vermelhos, est.posse, est.xg, est.fonte))

    def estatisticas_de_time(self, time_id: int, competicoes: list[str] = None) -> list[dict]:
        """Retorna lista de dicts com stats por jogo para cálculo de médias."""
        filtro = ""
        params: list = [time_id]
        if competicoes:
            ph = ",".join("?" * len(competicoes))
            filtro = f"AND j.competicao IN ({ph})"
            params.extend(competicoes)
        with self._conn() as conn:
            rows = conn.execute(f"""
                SELECT e.*, j.data, j.competicao
                FROM estatisticas_jogo e
                JOIN jogos j ON j.id = e.jogo_id
                WHERE e.time_id = ? {filtro}
                ORDER BY j.data DESC
            """, params).fetchall()
            return [dict(r) for r in rows]

    # --- Cache ---

    def _cache_chave(self, fonte: str, endpoint: str, params: dict) -> str:
        raw = f"{fonte}:{endpoint}:{json.dumps(params, sort_keys=True)}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def cache_get(self, fonte: str, endpoint: str, params: dict) -> Optional[dict]:
        chave = self._cache_chave(fonte, endpoint, params)
        with self._conn() as conn:
            row = conn.execute(
                "SELECT dados FROM cache_requisicoes WHERE chave = ?", (chave,)
            ).fetchone()
            if row:
                return json.loads(row["dados"])
        return None

    def cache_set(self, fonte: str, endpoint: str, params: dict, dados: dict):
        chave = self._cache_chave(fonte, endpoint, params)
        agora = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO cache_requisicoes (fonte, chave, dados, coletado_em)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chave) DO UPDATE SET dados = excluded.dados, coletado_em = excluded.coletado_em
            """, (fonte, chave, json.dumps(dados, ensure_ascii=False), agora))

    # --- Relatórios e previsões (Fase 3) ---

    def salvar_relatorio(self, relatorio: dict) -> int:
        with self._conn() as conn:
            cur = conn.execute("""
                INSERT INTO relatorios (jogo_id, gerado_em, prompt_versao, modelo_versao,
                                        conteudo, fatores_avaliados, fatores_ausentes,
                                        eh_relatorio_oficial)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """, (relatorio["jogo_id"], relatorio["gerado_em"], relatorio["prompt_versao"],
                  relatorio["modelo_versao"], relatorio["conteudo"],
                  json.dumps(relatorio.get("fatores_avaliados", []), ensure_ascii=False),
                  json.dumps(relatorio.get("fatores_ausentes", []), ensure_ascii=False)))
            return cur.lastrowid

    def marcar_relatorio_oficial(self, relatorio_id: int):
        with self._conn() as conn:
            jogo_id = conn.execute(
                "SELECT jogo_id FROM relatorios WHERE id = ?", (relatorio_id,)
            ).fetchone()["jogo_id"]
            conn.execute(
                "UPDATE relatorios SET eh_relatorio_oficial = 0 WHERE jogo_id = ?", (jogo_id,)
            )
            conn.execute(
                "UPDATE relatorios SET eh_relatorio_oficial = 1 WHERE id = ?", (relatorio_id,)
            )
