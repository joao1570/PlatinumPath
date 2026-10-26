
from getpass import getpass
from psnawp_api import PSNAWP


def testar_psn():
    print("=== PLATINUMPATH - TESTE PSN ===")

    npsso = getpass("Introduz o NPSSO: ").strip()

    if not npsso:
        print("Erro: NPSSO vazio.")
        return

    try:
        psn = PSNAWP(npsso)
        utilizador = psn.me()

        print("\nLigação à PSN estabelecida!")
        print("\n--- ÚLTIMOS 5 JOGOS COM TROFÉUS ---")

        for jogo in utilizador.trophy_titles(limit=5):
            print(f"- {jogo.title_name}")

        print("\nTeste concluído!")

    except Exception as erro:
        print(f"\nErro ao consultar a PSN: {erro}")


if __name__ == "__main__":
    testar_psn()
