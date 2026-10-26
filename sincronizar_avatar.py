
from getpass import getpass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from psnawp_api import PSNAWP
from jogos import ligar_base_dados


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


def validar_url(url):
    if not isinstance(url, str):
        return None

    partes = urlsplit(url)
    dominio = (partes.hostname or "").lower()

    dominios_permitidos = (
        "playstation.net",
        "playstation.com",
    )

    permitido = any(
        dominio == d or dominio.endswith("." + d)
        for d in dominios_permitidos
    )

    if not permitido or partes.scheme not in ("http", "https"):
        return None

    if partes.username or partes.password or partes.port:
        return None

    return urlunsplit((
        "https",
        partes.netloc,
        partes.path,
        partes.query,
        ""
    ))


def sincronizar_avatar():
    print("=== PLATINUMPATH - AVATAR PSN ===")

    npsso = getpass("Introduz o NPSSO: ").strip()

    if not npsso:
        print("Erro: NPSSO vazio.")
        return

    try:
        psn = PSNAWP(npsso)
        cliente = psn.me()

        utilizador = psn.user(online_id=cliente.online_id)
        dados = utilizador.profile()

        imagens = dados.get("avatars", [])

        imagens = sorted(
            imagens,
            key=lambda i: {
                "xl": 0, "l": 1, "m": 2, "s": 3
            }.get(i.get("size"), 4)
        )

        for imagem in imagens:
            url_original = imagem.get("url")
            url = validar_url(url_original)

            if not url:
                dominio = urlsplit(url_original or "").hostname
                print(f"URL nao suportado. Dominio: {dominio}")
                continue

            try:
                print("A tentar descarregar o avatar por HTTPS...")

                pedido = Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0"}
                )

                with urlopen(pedido, timeout=15) as resposta:
                    dados_imagem = resposta.read(2 * 1024 * 1024 + 1)

                if len(dados_imagem) > 2 * 1024 * 1024:
                    continue

                if dados_imagem.startswith(b"\x89PNG\r\n\x1a\n"):
                    extensao = "png"
                elif dados_imagem.startswith(b"\xff\xd8\xff"):
                    extensao = "jpg"
                elif (
                    dados_imagem[:4] == b"RIFF"
                    and dados_imagem[8:12] == b"WEBP"
                ):
                    extensao = "webp"
                else:
                    print("Formato de imagem nao reconhecido.")
                    continue

                STATIC_DIR.mkdir(exist_ok=True)

                nome = f"avatar_psn.{extensao}"
                caminho = STATIC_DIR / nome
                caminho.write_bytes(dados_imagem)

                with ligar_base_dados() as conexao:
                    colunas = {
                        c[1] for c in conexao.execute(
                            "PRAGMA table_info(perfil_psn)"
                        )
                    }

                    if "avatar_url" not in colunas:
                        conexao.execute(
                            "ALTER TABLE perfil_psn "
                            "ADD COLUMN avatar_url TEXT"
                        )

                    resultado = conexao.execute(
                        """
                        UPDATE perfil_psn
                        SET avatar_url = ?
                        WHERE id = 1
                        """,
                        (f"/static/{nome}",)
                    )

                    if resultado.rowcount == 0:
                        print("Perfil nao encontrado na base de dados.")
                        return

                print("\nAvatar PSN sincronizado com sucesso!")
                print(f"Imagem guardada em static/{nome}")
                return

            except Exception as erro:
                print(
                    f"Falha nesta imagem: "
                    f"{type(erro).__name__}"
                )

        print("\nNao foi possivel descarregar o avatar.")
        print("A base de dados nao foi alterada.")

    except Exception as erro:
        print(f"Erro: {type(erro).__name__}: {erro}")


if __name__ == "__main__":
    sincronizar_avatar()
