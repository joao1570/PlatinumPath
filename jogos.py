
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "database" / "platinumpath.db"


def ligar_base_dados():
    conexao = sqlite3.connect(DATABASE_PATH)
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def obter_plataforma(conexao, plataforma):
    resultado = conexao.execute(
        "SELECT id FROM plataformas WHERE nome = ?",
        (plataforma.strip().upper(),)
    ).fetchone()

    return resultado[0] if resultado else None


def adicionar_jogo(titulo, plataforma):
    titulo = titulo.strip()

    if not titulo:
        print("Erro: o título não pode estar vazio.")
        return

    with ligar_base_dados() as conexao:
        plataforma_id = obter_plataforma(conexao, plataforma)

        if plataforma_id is None:
            print("Erro: usa PS3, PS4 ou PS5.")
            return

        conexao.execute(
            "INSERT INTO jogos (titulo, plataforma_id) VALUES (?, ?)",
            (titulo, plataforma_id)
        )

    print(f"Jogo '{titulo}' adicionado com sucesso!")


def listar_jogos():
    with ligar_base_dados() as conexao:
        jogos = conexao.execute(
            """
            SELECT jogos.id, jogos.titulo,
                   plataformas.nome, jogos.estado
            FROM jogos
            JOIN plataformas
                ON jogos.plataforma_id = plataformas.id
            ORDER BY jogos.id
            """
        ).fetchall()

    if not jogos:
        print("Ainda não existem jogos registados.")
        return

    print("\n--- JOGOS REGISTADOS ---")

    for jogo in jogos:
        print(
            f"{jogo[0]} - {jogo[1]} "
            f"({jogo[2]}) - {jogo[3]}"
        )


def editar_jogo():
    listar_jogos()

    try:
        jogo_id = int(input("\nID do jogo a editar: "))
    except ValueError:
        print("Erro: introduz um ID numérico.")
        return

    with ligar_base_dados() as conexao:
        jogo = conexao.execute(
            "SELECT titulo, plataforma_id FROM jogos WHERE id = ?",
            (jogo_id,)
        ).fetchone()

        if jogo is None:
            print("Erro: jogo não encontrado.")
            return

        novo_titulo = input("Novo título (Enter para manter): ").strip()
        nova_plataforma = input(
            "Nova plataforma PS3/PS4/PS5 (Enter para manter): "
        ).strip()

        titulo = novo_titulo if novo_titulo else jogo[0]
        plataforma_id = jogo[1]

        if nova_plataforma:
            plataforma_id = obter_plataforma(conexao, nova_plataforma)

            if plataforma_id is None:
                print("Erro: plataforma inválida.")
                return

        conexao.execute(
            """
            UPDATE jogos
            SET titulo = ?, plataforma_id = ?
            WHERE id = ?
            """,
            (titulo, plataforma_id, jogo_id)
        )

    print("Jogo atualizado com sucesso!")


def eliminar_jogo():
    listar_jogos()

    try:
        jogo_id = int(input("\nID do jogo a eliminar: "))
    except ValueError:
        print("Erro: introduz um ID numérico.")
        return

    with ligar_base_dados() as conexao:
        jogo = conexao.execute(
            "SELECT titulo FROM jogos WHERE id = ?",
            (jogo_id,)
        ).fetchone()

        if jogo is None:
            print("Erro: jogo não encontrado.")
            return

        confirmacao = input(
            f"Tens a certeza que queres eliminar '{jogo[0]}'? (s/n): "
        ).strip().lower()

        if confirmacao != "s":
            print("Operação cancelada.")
            return

        conexao.execute(
            "DELETE FROM jogos WHERE id = ?",
            (jogo_id,)
        )

    print("Jogo eliminado com sucesso!")


def menu():
    while True:
        print("\n=== PLATINUMPATH ===")
        print("1 - Adicionar jogo")
        print("2 - Listar jogos")
        print("3 - Editar jogo")
        print("4 - Eliminar jogo")
        print("0 - Sair")

        opcao = input("Escolhe uma opção: ").strip()

        if opcao == "1":
            titulo = input("Nome do jogo: ")
            plataforma = input("Plataforma (PS3/PS4/PS5): ")
            adicionar_jogo(titulo, plataforma)

        elif opcao == "2":
            listar_jogos()

        elif opcao == "3":
            editar_jogo()

        elif opcao == "4":
            eliminar_jogo()

        elif opcao == "0":
            print("Até à próxima!")
            break

        else:
            print("Opção inválida.")


if __name__ == "__main__":
    menu()
