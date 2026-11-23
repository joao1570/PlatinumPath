
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS plataformas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS jogos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    plataforma_id INTEGER NOT NULL,
    estado TEXT NOT NULL DEFAULT 'Por iniciar'
        CHECK (estado IN ('Por iniciar', 'Em progresso', 'Concluido')),
    data_adicao TEXT NOT NULL DEFAULT CURRENT_DATE,
    FOREIGN KEY (plataforma_id)
        REFERENCES plataformas(id)
);

CREATE TABLE IF NOT EXISTS trofeus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jogo_id INTEGER NOT NULL,
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL
        CHECK (tipo IN ('Bronze', 'Prata', 'Ouro', 'Platina')),
    conquistado INTEGER NOT NULL DEFAULT 0
        CHECK (conquistado IN (0, 1)),
    FOREIGN KEY (jogo_id)
        REFERENCES jogos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS objetivos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jogo_id INTEGER NOT NULL,
    descricao TEXT NOT NULL,
    concluido INTEGER NOT NULL DEFAULT 0
        CHECK (concluido IN (0, 1)),
    FOREIGN KEY (jogo_id)
        REFERENCES jogos(id) ON DELETE CASCADE
);

INSERT INTO plataformas (nome) SELECT 'PS3' WHERE NOT EXISTS (SELECT 1 FROM plataformas WHERE nome='PS3');
INSERT INTO plataformas (nome) SELECT 'PS4' WHERE NOT EXISTS (SELECT 1 FROM plataformas WHERE nome='PS4');
INSERT INTO plataformas (nome) SELECT 'PS5' WHERE NOT EXISTS (SELECT 1 FROM plataformas WHERE nome='PS5');

CREATE TABLE IF NOT EXISTS perfil_psn (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    online_id TEXT NOT NULL,
    nivel INTEGER NOT NULL,
    progresso INTEGER NOT NULL,
    bronze INTEGER NOT NULL,
    prata INTEGER NOT NULL,
    ouro INTEGER NOT NULL,
    platina INTEGER NOT NULL,
    atualizado_em TEXT NOT NULL,
    avatar_url TEXT
);
CREATE TABLE IF NOT EXISTS amigos_guardados (
    online_id TEXT PRIMARY KEY COLLATE NOCASE,
    avatar_url TEXT,
    adicionado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS verificacao_datas_psn (
    jogo_id INTEGER PRIMARY KEY,
    verificado_em TEXT NOT NULL
);
