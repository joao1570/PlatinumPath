
from getpass import getpass
from urllib.parse import urlparse

from psnawp_api import PSNAWP


def verificar_avatar():
    print("=== DIAGNOSTICO AVATAR PSN ===")

    npsso = getpass("Introduz o NPSSO: ").strip()

    if not npsso:
        print("NPSSO vazio.")
        return

    try:
        psn = PSNAWP(npsso)
        cliente = psn.me()

        utilizador = psn.user(online_id=cliente.online_id)
        dados = utilizador.profile()

        imagens = dados.get("avatars", [])

        print(f"\nAvatares encontrados: {len(imagens)}")

        for numero, imagem in enumerate(imagens, start=1):
            print(f"\nAvatar {numero}:")

            if not isinstance(imagem, dict):
                print("Tipo:", type(imagem).__name__)
                continue

            print("Campos:", list(imagem.keys()))
            print("Tamanho:", imagem.get("size"))

            for campo in ("url", "avatarUrl", "imageUrl"):
                valor = imagem.get(campo)

                if isinstance(valor, str):
                    print(
                        f"Campo {campo}: "
                        f"protocolo={urlparse(valor).scheme!r}"
                    )

        print("\nDiagnostico concluido.")
        print("Nenhum URL completo foi apresentado.")

    except Exception as erro:
        print(f"Erro: {type(erro).__name__}")


if __name__ == "__main__":
    verificar_avatar()
