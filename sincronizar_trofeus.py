
from getpass import getpass

from psnawp_api import PSNAWP
from jogos import ligar_base_dados, listar_jogos


def preparar_base_dados(conexao):
    colunas = {
        coluna[1]
        for coluna in conexao.execute("PRAGMA table_info(trofeus)")
    }

    if "psn_trophy_id" not in colunas:
        conexao.execute(
            "ALTER TABLE trofeus ADD COLUMN psn_trophy_id INTEGER"
        )

    if "psn_grupo" not in colunas:
        conexao.execute(
            "ALTER TABLE trofeus ADD COLUMN psn_grupo TEXT"
        )

    conexao.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_trofeus_psn
        ON trofeus (jogo_id, psn_grupo, psn_trophy_id)
        WHERE psn_trophy_id IS NOT NULL
    """)


def sincronizar_trofeus():
    print("\n=== SINCRONIZAR TROFEUS PSN ===")
    listar_jogos()

    try:
        jogo_id = int(input("\nID do jogo: "))
    except ValueError:
        print("Erro: ID invalido.")
        return

    with ligar_base_dados() as conexao:
        jogo = conexao.execute("""
            SELECT jogos.titulo, plataformas.nome
            FROM jogos
            JOIN plataformas
                ON jogos.plataforma_id = plataformas.id
            WHERE jogos.id = ?
        """, (jogo_id,)).fetchone()

    if jogo is None:
        print("Erro: jogo nao encontrado.")
        return

    titulo_local, plataforma_local = jogo

    npsso = getpass("Introduz o NPSSO: ").strip()

    if not npsso:
        print("Erro: NPSSO vazio.")
        return

    try:
        psn = PSNAWP(npsso)
        utilizador = psn.me()

        jogo_psn = None
        plataforma_psn = None

        for titulo in utilizador.trophy_titles(limit=None):
            if (titulo.title_name or "").casefold() != titulo_local.casefold():
                continue

            for plataforma in titulo.title_platform:
                if plataforma.value.upper() == plataforma_local:
                    jogo_psn = titulo
                    plataforma_psn = plataforma
                    break

            if jogo_psn is not None:
                break

        if jogo_psn is None:
            print("Jogo nao encontrado na lista PSN.")
            return

        if not jogo_psn.np_communication_id:
            print("Jogo sem identificador PSN.")
            return

        print(f"\nA consultar: {titulo_local}")

        trofeus_psn = list(utilizador.trophies(
            np_communication_id=jogo_psn.np_communication_id,
            platform=plataforma_psn,
            trophy_group_id="all",
            include_progress=True
        ))

        tipos = {
            "bronze": "Bronze",
            "silver": "Prata",
            "gold": "Ouro",
            "platinum": "Platina"
        }

        preparados = []

        for trofeu in trofeus_psn:
            if trofeu.trophy_id is None:
                continue

            tipo_original = getattr(trofeu.trophy_type, "value", "")
            tipo = tipos.get(str(tipo_original).lower())

            if tipo is None:
                continue

            preparados.append((
                int(trofeu.trophy_id),
                trofeu.trophy_group_id or "default",
                trofeu.trophy_name or "Trofeu oculto",
                tipo,
                1 if trofeu.earned else 0
            ))

        adicionados = 0
        atualizados = 0

        with ligar_base_dados() as conexao:
            preparar_base_dados(conexao)

            for psn_id, grupo, nome, tipo, conquistado in preparados:
                existente = conexao.execute("""
                    SELECT id FROM trofeus
                    WHERE jogo_id = ?
                      AND psn_grupo = ?
                      AND psn_trophy_id = ?
                """, (jogo_id, grupo, psn_id)).fetchone()

                if existente:
                    conexao.execute("""
                        UPDATE trofeus
                        SET nome = ?, tipo = ?, conquistado = ?
                        WHERE id = ?
                    """, (nome, tipo, conquistado, existente[0]))
                    atualizados += 1
                else:
                    conexao.execute("""
                        INSERT INTO trofeus
                        (jogo_id, nome, tipo, conquistado,
                         psn_trophy_id, psn_grupo)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        jogo_id, nome, tipo, conquistado,
                        psn_id, grupo
                    ))
                    adicionados += 1

        conquistados = sum(t[4] for t in preparados)

        print("\n=== RESULTADO ===")
        print(f"Trofeus recebidos: {len(preparados)}")
        print(f"Novos: {adicionados}")
        print(f"Atualizados: {atualizados}")
        print(f"Conquistados: {conquistados}")
        print("Sincronizacao concluida!")

    except Exception as erro:
        print(f"Erro na sincronizacao: {erro}")


if __name__ == "__main__":
    sincronizar_trofeus()
