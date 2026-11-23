"""Prepara a base de dados com um backup seguro antes de migrar o schema."""
from contextlib import closing
from datetime import datetime
from pathlib import Path
import sqlite3

from init_db import DATABASE_PATH, criar_base_dados


def main():
    caminho = Path(DATABASE_PATH)
    if caminho.exists():
        pasta_backups = caminho.parent / "backups"
        pasta_backups.mkdir(parents=True, exist_ok=True)
        destino = pasta_backups / ("platinumpath_pre_instalacao_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".db")
        # A API de backup do SQLite gera uma copia consistente, mesmo em uso.
        with closing(sqlite3.connect(caminho, timeout=30)) as origem:
            with closing(sqlite3.connect(destino, timeout=30)) as copia:
                origem.backup(copia)
        print("Backup criado:", destino)
    else:
        print("Instalacao inicial: a base de dados sera criada.")
    criar_base_dados()
    print("Instalacao de dados concluida.")


if __name__ == "__main__":
    main()
