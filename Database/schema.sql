
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

INSERT OR IGNORE INTO plataformas (nome)
VALUES ('PS3'), ('PS4'), ('PS5');
