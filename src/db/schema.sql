-- Copa Analyst — Schema SQLite
-- Baseado no PRD Seção 5 + Decisão 11 (arquitetura de fontes)

CREATE TABLE IF NOT EXISTS times (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome                        TEXT    NOT NULL UNIQUE,
    codigo_fifa                 TEXT    UNIQUE,
    grupo_copa26                TEXT,   -- grupo na Copa 2026 (A-L)
    confederacao                TEXT,   -- CONMEBOL | UEFA | CONCACAF | AFC | CAF | OFC
    rating_prior                REAL,   -- escala Elo (eloratings.net)
    rating_prior_atualizado_em  TEXT    -- ISO-8601
);

-- Cobre todos os jogos: Copa 2026 + Copa 2022 + qualificatórias (para forma)
CREATE TABLE IF NOT EXISTS jogos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    competicao          TEXT    NOT NULL, -- 'copa_2026'|'copa_2022'|'elim_conmebol_2022'|'elim_uefa_2024'|...
    data                TEXT    NOT NULL, -- YYYY-MM-DD
    hora_utc            TEXT,             -- HH:MM
    time_mandante_id    INTEGER REFERENCES times(id),
    time_visitante_id   INTEGER REFERENCES times(id),
    -- PRD 7.1: campo_neutro=1 para quase todos os jogos da Copa
    campo_neutro        INTEGER NOT NULL DEFAULT 1,
    fase                TEXT,             -- 'grupo'|'oitavas'|'quartas'|'semi'|'final'|'qualificacao'
    grupo               TEXT,
    estadio             TEXT,
    cidade              TEXT,
    altitude_m          REAL,
    placar_mandante     INTEGER,          -- NULL até o jogo acontecer
    placar_visitante    INTEGER,          -- NULL até o jogo acontecer
    id_externo          TEXT,             -- ID na fonte original
    fonte               TEXT              -- 'openfootball'|'api_football'|'thesportsdb'|'wikipedia'
);

-- Muitos campos nullable — ausência é esperada e tratada (PRD 5.3)
CREATE TABLE IF NOT EXISTS estatisticas_jogo (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    jogo_id             INTEGER NOT NULL REFERENCES jogos(id),
    time_id             INTEGER NOT NULL REFERENCES times(id),
    gols                INTEGER,
    escanteios          INTEGER,
    chutes              INTEGER,
    chutes_no_alvo      INTEGER,
    faltas              INTEGER,
    cartoes_amarelos    INTEGER,
    cartoes_vermelhos   INTEGER,
    posse               REAL,
    xg                  REAL,   -- majoritariamente NULL (PRD 5.3, Decisão 6)
    fonte               TEXT,
    UNIQUE(jogo_id, time_id)
);

-- Append-only: cada análise gera um novo registro (PRD 5.4)
CREATE TABLE IF NOT EXISTS relatorios (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    jogo_id                 INTEGER NOT NULL REFERENCES jogos(id),
    gerado_em               TEXT    NOT NULL, -- ISO-8601 timestamp
    prompt_versao           TEXT    NOT NULL, -- ex: 'v1'
    modelo_versao           TEXT    NOT NULL, -- ex: 'claude-sonnet-4-6'
    conteudo                TEXT    NOT NULL, -- HTML do relatório
    fatores_avaliados       TEXT,             -- JSON array
    fatores_ausentes        TEXT,             -- JSON array (PRD 2.4)
    -- Apenas um relatório por jogo tem este flag = 1 (o último antes do apito)
    eh_relatorio_oficial    INTEGER NOT NULL DEFAULT 0
);

-- Tabela central: materializa PRD 2.2, 2.3, 2.4 e habilita Seção 9
CREATE TABLE IF NOT EXISTS previsoes (
    id                              INTEGER PRIMARY KEY AUTOINCREMENT,
    relatorio_id                    INTEGER NOT NULL REFERENCES relatorios(id),
    jogo_id                         INTEGER NOT NULL REFERENCES jogos(id),
    mercado                         TEXT    NOT NULL, -- enum: resultado|total_gols|ambas_marcam|escanteios|cartoes_amarelos|faltas|chutes_time
    entidade                        TEXT,             -- reservado para v2 (mercados de jogador)
    previsao                        TEXT    NOT NULL,
    probabilidade_estimada          REAL,             -- [0,1] ou NULL
    -- PRD 2.2: preservado para auditoria da banda de ajuste
    probabilidade_calculada_original REAL,            -- NULL quando origem=qualitativo
    incerteza                       TEXT    NOT NULL CHECK(incerteza IN ('baixa','media','alta')),
    origem                          TEXT    NOT NULL CHECK(origem IN ('calculado','qualitativo','hibrido')),
    justificativa                   TEXT    NOT NULL,
    fontes                          TEXT,             -- JSON array de links/inputs
    gerado_em                       TEXT    NOT NULL,
    resultado_real                  TEXT              -- preenchido após o jogo (Fase 6)
);

-- Cache de requisições externas — imutáveis não são re-buscados (PRD 4.4)
CREATE TABLE IF NOT EXISTS cache_requisicoes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fonte       TEXT    NOT NULL, -- 'api_football'|'thesportsdb'|'wikipedia'|'eloratings'|'openfootball'
    chave       TEXT    NOT NULL UNIQUE, -- hash determinístico de fonte+endpoint+params
    dados       TEXT    NOT NULL, -- JSON serializado
    coletado_em TEXT    NOT NULL  -- ISO-8601
);

-- Índices para queries frequentes
CREATE INDEX IF NOT EXISTS idx_jogos_competicao ON jogos(competicao);
CREATE INDEX IF NOT EXISTS idx_jogos_mandante    ON jogos(time_mandante_id);
CREATE INDEX IF NOT EXISTS idx_jogos_visitante   ON jogos(time_visitante_id);
CREATE INDEX IF NOT EXISTS idx_estatisticas_jogo ON estatisticas_jogo(jogo_id);
CREATE INDEX IF NOT EXISTS idx_previsoes_jogo    ON previsoes(jogo_id);
CREATE INDEX IF NOT EXISTS idx_relatorios_jogo   ON relatorios(jogo_id);
