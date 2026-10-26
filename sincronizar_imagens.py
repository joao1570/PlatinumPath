
from getpass import getpass
from urllib.parse import urlparse

from psnawp_api import PSNAWP
from jogos import ligar_base_dados


def sincronizar_imagens():
    print("=== PLATINUMPATH - IMAGENS PSN ===")

    npsso = getpass("Introduz o NPSSO: ").strip()

    if not npsso:
        print("Erro: NPSSO vazio.")
        return

    try:
        psn = PSNAWP(npsso)
        utilizador = psn.me()

        with ligar_base_dados() as conexao:
            colunas = {
                coluna[1]
                for coluna in conexao.execute(
                    "PRAGMA table_info(jogos)"
                )
            }

            if "imagem_url" not in colunas:
                conexao.execute(
                    "ALTER TABLE jogos ADD COLUMN imagem_url TEXT"
                )

            imagens = 0

            for jogo in utilizador.trophy_titles(limit=None):
                titulo = (jogo.title_name or "").strip()
                url = jogo.title_icon_url

                if not titulo or not url:
                    continue

                parsed = urlparse(url)

                if parsed.scheme != "https":
                    continue

                for plataforma in jogo.title_platform:
                    resultado = conexao.execute(
                        """
                        UPDATE jogos
                        SET imagem_url = ?
                        WHERE titulo = ? COLLATE NOCASE
                        AND plataforma_id IN (
                            SELECT id
                            FROM plataformas
                            WHERE nome = ?
                        )
                        """,
                        (url, titulo, plataforma.value.upper())
                    )

                    if resultado.rowcount:
                        imagens += resultado.rowcount
                        print(f"Imagem encontrada: {titulo}")

        print("\n=== RESULTADO ===")
        print(f"Jogos atualizados: {imagens}")
        print("Imagens guardadas na base de dados!")

    except Exception as erro:
        print(f"Erro: {erro}")


if __name__ == "__main__":
    sincronizar_imagens()
