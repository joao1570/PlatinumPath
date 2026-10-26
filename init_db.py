
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "platinumpath.db"
SCHEMA_PATH = DATABASE_DIR / "schema.sql"


def criar_base_dados():
    DATABASE_DIR.mkdir(exist_ok=True)

    with sqlite3.connect(DATABASE_PATH) as conexao:
        conexao.execute("PRAGMA foreign_keys = ON")

        with open(SCHEMA_PATH, "r", encoding="utf-8") as ficheiro:
            conexao.executescript(ficheiro.read())

        tabelas = conexao.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        ).fetchall()

    print("Base de dados criada com sucesso!")
    print("Tabelas encontradas:")

    for tabela in tabelas:
        print(f"- {tabela[0]}")


if __name__ == "__main__":
    criar_base_dados()
