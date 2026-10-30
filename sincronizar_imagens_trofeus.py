
import sqlite3
import getpass
import unicodedata
from pathlib import Path

from psnawp_api import PSNAWP


BASE = Path(__file__).resolve().parent
DB = BASE / "Database" / "platinumpath.db"


def normalizar(texto):
    texto = unicodedata.normalize(
        "NFKD", str(texto or "")
    )

    return "".join(
        letra
        for letra in texto
        if not unicodedata.combining(letra)
    ).casefold().strip()


def nome_plataforma(valor):
    valor = getattr(valor, "value", valor)
    texto = str(valor).upper().replace("_", "")

    if "VITA" in texto:
        return "PSVITA"

    return texto.replace(" ", "")


def colunas(con, tabela):
    return {
        linha["name"]
        for linha in con.execute(
            f"PRAGMA table_info({tabela})"
        )
    }


def obter_jogos(con):
    jogos = con.execute(
        """
        SELECT id, titulo, plataforma_id
        FROM jogos
        ORDER BY id
        """
    ).fetchall()

    campos = colunas(con, "plataformas")

    campo_nome = next(
        (
            campo
            for campo in (
                "nome",
                "sigla",
                "designacao",
                "plataforma"
            )
            if campo in campos
        ),
        None
    )

    plataformas = {}

    if campo_nome:
        for linha in con.execute(
            f'SELECT id, "{campo_nome}" FROM plataformas'
        ):
            plataformas[linha[0]] = linha[1]

    return jogos, plataformas


def preparar_database(con):
    campos = colunas(con, "trofeus")

    obrigatorios = {
        "id",
        "jogo_id",
        "nome",
        "tipo",
        "conquistado",
        "psn_trophy_id",
        "psn_grupo",
    }

    if not obrigatorios.issubset(campos):
        raise RuntimeError(
            "A estrutura da tabela trofeus não corresponde "
            "à estrutura esperada."
        )

    if "imagem_url" not in campos:
        con.execute(
            "ALTER TABLE trofeus "
            "ADD COLUMN imagem_url TEXT"
        )

    if "descricao" not in campos:
        con.execute(
            "ALTER TABLE trofeus "
            "ADD COLUMN descricao TEXT"
        )

    con.commit()


def atualizar_trofeus(con, cliente, jogo, titulo):
    plataformas = list(titulo.title_platform or [])

    if not plataformas:
        return 0

    plataforma = plataformas[0]

    lista_psn = cliente.trophies(
        titulo.np_communication_id,
        plataforma,
        trophy_group_id="all",
        include_progress=False,
    )

    atualizados = 0

    for trofeu in lista_psn:
        trophy_id = trofeu.trophy_id
        grupo = trofeu.trophy_group_id or "default"
        imagem = trofeu.trophy_icon_url
        descricao = trofeu.trophy_detail

        if trophy_id is None:
            continue

        if not imagem or not imagem.startswith("https://"):
            continue

        cursor = con.execute(
            """
            UPDATE trofeus
            SET imagem_url = ?,
                descricao = ?
            WHERE jogo_id = ?
              AND psn_trophy_id = ?
              AND COALESCE(psn_grupo, 'default') = ?
            """,
            (
                imagem,
                descricao,
                jogo["id"],
                trophy_id,
                grupo,
            )
        )

        atualizados += cursor.rowcount

    con.commit()

    return atualizados


def main():
    if not DB.exists():
        print("Base de dados não encontrada.")
        print(DB)
        return

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    try:
        preparar_database(con)

        jogos, plataformas = obter_jogos(con)

        print("Base de dados:", DB)
        print("Jogos encontrados:", len(jogos))

        if not jogos:
            print("Não existem jogos registados.")
            return

        print()
        print("Autenticação PlayStation Network")

        credencial = getpass.getpass("NPSSO: ").strip()

        if not credencial:
            print("Operação cancelada.")
            return

        psn = PSNAWP(credencial)
        del credencial

        cliente = psn.me()

        print()
        print("A consultar a biblioteca de troféus PSN...")

        titulos_psn = list(
            cliente.trophy_titles(limit=None)
        )

        indice = {}

        for titulo in titulos_psn:
            chave = normalizar(titulo.title_name)
            indice.setdefault(chave, []).append(titulo)

        total_atualizados = 0

        for jogo in jogos:
            nome = jogo["titulo"]
            chave = normalizar(nome)

            candidatos = indice.get(chave, [])

            plataforma_local = plataformas.get(
                jogo["plataforma_id"]
            )

            if plataforma_local:
                plataforma_local = nome_plataforma(
                    plataforma_local
                )

                candidatos = [
                    titulo
                    for titulo in candidatos
                    if plataforma_local in [
                        nome_plataforma(p)
                        for p in (titulo.title_platform or [])
                    ]
                ]

            if len(candidatos) != 1:
                print(
                    "[IGNORADO]",
                    nome,
                    "- correspondência PSN não única"
                )
                continue

            print()
            print("[JOGO]", nome)

            try:
                quantidade = atualizar_trofeus(
                    con,
                    cliente,
                    jogo,
                    candidatos[0],
                )

                total_atualizados += quantidade

                print(
                    "Imagens associadas:",
                    quantidade
                )

            except Exception as erro:
                print(
                    "Erro ao sincronizar:",
                    nome,
                    erro
                )

        print()
        print("=" * 40)
        print("SINCRONIZAÇÃO TERMINADA")
        print("Total de imagens:", total_atualizados)
        print("=" * 40)

    finally:
        con.close()


if __name__ == "__main__":
    main()
