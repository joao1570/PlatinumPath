"""Create or migrate the local database without deleting user data."""
import sqlite3
from contextlib import closing
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / 'Database'
DATABASE_PATH = DATABASE_DIR / 'platinumpath.db'
SCHEMA_PATH = DATABASE_DIR / 'schema.sql'


def criar_base_dados(path=None):
    path = Path(path or DATABASE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=15)) as conexao, conexao:
        conexao.execute('PRAGMA foreign_keys = ON')
        conexao.executescript(SCHEMA_PATH.read_text(encoding='utf-8'))
        campos = {
            'jogos': {'imagem_url': 'TEXT', 'ultima_conquista': 'TEXT'},
            'trofeus': {'psn_trophy_id': 'INTEGER', 'psn_grupo': 'TEXT', 'imagem_url': 'TEXT', 'descricao': 'TEXT', 'data_conquista': 'TEXT'},
            'perfil_psn': {'avatar_url': 'TEXT'},
        }
        for tabela, colunas in campos.items():
            existentes = {r[1] for r in conexao.execute(f'PRAGMA table_info({tabela})')}
            for nome, tipo in colunas.items():
                if nome not in existentes:
                    conexao.execute(f'ALTER TABLE {tabela} ADD COLUMN {nome} {tipo}')
        conexao.execute('CREATE INDEX IF NOT EXISTS idx_trofeus_jogo ON trofeus(jogo_id)')
        conexao.execute('CREATE INDEX IF NOT EXISTS idx_objetivos_jogo ON objetivos(jogo_id)')
        conexao.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_trofeus_psn ON trofeus(jogo_id, psn_grupo, psn_trophy_id) WHERE psn_trophy_id IS NOT NULL')
    print('Base de dados pronta:', path.name)


if __name__ == '__main__':
    criar_base_dados()
