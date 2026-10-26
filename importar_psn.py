
from getpass import getpass

from psnawp_api import PSNAWP
from jogos import ligar_base_dados


def importar_jogos():
    print("=== IMPORTAR JOGOS DA PSN ===")

    npsso = getpass("Introduz o NPSSO: ").strip()

    if not npsso:
        print("Erro: NPSSO vazio.")
        return

    try:
        psn = PSNAWP(npsso)
        utilizador = psn.me()

        jogos_psn = list(utilizador.trophy_titles(limit=5))

        adicionados = 0
        existentes = 0

        with ligar_base_dados() as conexao:
            for jogo in jogos_psn:
                titulo = (jogo.title_name or "").strip()

                plataformas = {
                    str(p.value).upper()
                    for p in jogo.title_platform
                }

                for plataforma in ("PS5", "PS4", "PS3"):
                    if plataforma not in plataformas:
                        continue

                    if not titulo:
                        continue

                    resultado = conexao.execute(
                        """
                        SELECT id FROM plataformas
                        WHERE nome = ?
                        """,
                        (plataforma,)
                    ).fetchone()

                    if resultado is None:
                        continue

                    plataforma_id = resultado[0]

                    existente = conexao.execute(
                        """
                        SELECT id FROM jogos
                        WHERE titulo = ? COLLATE NOCASE
                        AND plataforma_id = ?
                        """,
                        (titulo, plataforma_id)
                    ).fetchone()

                    if existente:
                        print(f"Já existe: {titulo} ({plataforma})")
                        existentes += 1
                        continue

                    conexao.execute(
                        """
                        INSERT INTO jogos (titulo, plataforma_id)
                        VALUES (?, ?)
                        """,
                        (titulo, plataforma_id)
                    )

                    print(f"Importado: {titulo} ({plataforma})")
                    adicionados += 1

        print("\n=== RESULTADO ===")
        print(f"Jogos adicionados: {adicionados}")
        print(f"Jogos já existentes: {existentes}")
        print("Importação concluída!")

    except Exception as erro:
        print(f"Erro na importação: {erro}")


if __name__ == "__main__":
    importar_jogos()
