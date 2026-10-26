
import sqlite3
from getpass import getpass

from psnawp_api import PSNAWP
from jogos import ligar_base_dados


def sincronizar_perfil():
    print("=== PLATINUMPATH - PERFIL PSN ===")

    npsso = getpass("Introduz o NPSSO: ").strip()

    if not npsso:
        print("Erro: NPSSO vazio.")
        return

    try:
        psn = PSNAWP(npsso)
        utilizador = psn.me()

        resumo = utilizador.trophy_summary()
        trofeus = resumo.earned_trophies

        online_id = utilizador.online_id
        nivel = resumo.trophy_level
        progresso = resumo.progress

        bronze = trofeus.bronze
        prata = trofeus.silver
        ouro = trofeus.gold
        platina = trofeus.platinum

        total = bronze + prata + ouro + platina

        with ligar_base_dados() as conexao:
            conexao.execute("""
                CREATE TABLE IF NOT EXISTS perfil_psn (
                    id INTEGER PRIMARY KEY
                        CHECK (id = 1),
                    online_id TEXT NOT NULL,
                    nivel INTEGER NOT NULL,
                    progresso INTEGER NOT NULL,
                    bronze INTEGER NOT NULL,
                    prata INTEGER NOT NULL,
                    ouro INTEGER NOT NULL,
                    platina INTEGER NOT NULL,
                    atualizado_em TEXT NOT NULL
                )
            """)

            conexao.execute("""
                INSERT INTO perfil_psn (
                    id, online_id, nivel, progresso,
                    bronze, prata, ouro, platina,
                    atualizado_em
                )
                VALUES (1, ?, ?, ?, ?, ?, ?, ?,
                        CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    online_id = excluded.online_id,
                    nivel = excluded.nivel,
                    progresso = excluded.progresso,
                    bronze = excluded.bronze,
                    prata = excluded.prata,
                    ouro = excluded.ouro,
                    platina = excluded.platina,
                    atualizado_em = CURRENT_TIMESTAMP
            """, (
                online_id, nivel, progresso,
                bronze, prata, ouro, platina
            ))

        print("\n=== PERFIL SINCRONIZADO ===")
        print(f"Conta PSN: {online_id}")
        print(f"Nivel: {nivel}")
        print(f"Progresso: {progresso}%")
        print(f"Bronze: {bronze}")
        print(f"Prata: {prata}")
        print(f"Ouro: {ouro}")
        print(f"Platina: {platina}")
        print(f"Total de trofeus: {total}")
        print("\nPerfil guardado no SQLite!")

    except (sqlite3.Error, Exception) as erro:
        print(f"Erro ao sincronizar: {erro}")


if __name__ == "__main__":
    sincronizar_perfil()
