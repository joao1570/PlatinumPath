
from getpass import getpass

from psnawp_api import PSNAWP
from jogos import ligar_base_dados


def importar_jogos():
    print("=== PLATINUMPATH - BIBLIOTECA PSN ===")

    npsso = getpass("Introduz o NPSSO: ").strip()

    if not npsso:
        print("Erro: NPSSO vazio.")
        return

    try:
        psn = PSNAWP(npsso)
        utilizador = psn.me()

        print(f"\nPerfil: {utilizador.online_id}")
        print("A procurar todos os jogos da PSN...\n")

        adicionados = 0
        existentes = 0
        encontrados = 0
        ignorados = 0

        with ligar_base_dados() as conexao:
            plataformas_db = {
                nome.upper(): id_plataforma
                for id_plataforma, nome in conexao.execute(
                    "SELECT id, nome FROM plataformas"
                ).fetchall()
            }

            jogos_psn = utilizador.trophy_titles(
                limit=None,
                page_size=50
            )

            for jogo in jogos_psn:
                encontrados += 1

                titulo = (jogo.title_name or "").strip()

                if not titulo:
                    ignorados += 1
                    continue

                plataformas = {
                    str(getattr(p, "value", p)).upper()
                    for p in jogo.title_platform
                }

                for plataforma in ("PS5", "PS4", "PS3"):
                    if plataforma not in plataformas:
                        continue

                    plataforma_id = plataformas_db.get(plataforma)

                    if plataforma_id is None:
                        ignorados += 1
                        continue

                    existente = conexao.execute(
                        """
                        SELECT id FROM jogos
                        WHERE titulo = ? COLLATE NOCASE
                        AND plataforma_id = ?
                        """,
                        (titulo, plataforma_id)
                    ).fetchone()

                    if existente:
                        existentes += 1
                        print(f"[EXISTE] {titulo} ({plataforma})")
                        continue

                    conexao.execute(
                        """
                        INSERT INTO jogos (titulo, plataforma_id)
                        VALUES (?, ?)
                        """,
                        (titulo, plataforma_id)
                    )

                    adicionados += 1
                    print(f"[NOVO] {titulo} ({plataforma})")

        print("\n=== RESULTADO FINAL ===")
        print(f"Titulos PSN encontrados: {encontrados}")
        print(f"Jogos adicionados: {adicionados}")
        print(f"Registos existentes: {existentes}")
        print(f"Registos ignorados: {ignorados}")
        print("\nImportacao concluida!")

    except Exception as erro:
        print(f"\nErro na importacao: {erro}")


if __name__ == "__main__":
    importar_jogos()
