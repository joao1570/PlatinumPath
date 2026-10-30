
import getpass
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path

from psnawp_api import PSNAWP


BASE = Path(__file__).resolve().parent
DB = BASE / "Database" / "platinumpath.db"
BACKUPS = BASE / "Database" / "backups"


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))

    return "".join(
        c for c in texto
        if not unicodedata.combining(c)
    ).casefold().strip()


def normalizar_plataforma(valor):
    valor = getattr(valor, "value", valor)
    return str(valor).upper().replace(" ", "").replace("_", "")


def ligar_base_dados():
    conexao = sqlite3.connect(DB)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def criar_backup():
    BACKUPS.mkdir(parents=True, exist_ok=True)

    data = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    destino = BACKUPS / f"platinumpath_{data}.db"

    with sqlite3.connect(DB) as origem:
        with sqlite3.connect(destino) as copia:
            origem.backup(copia)

    print("Backup criado:", destino.name)


def preparar_base_dados(conexao):
    colunas = {
        linha["name"]
        for linha in conexao.execute("PRAGMA table_info(trofeus)")
    }

    obrigatorias = {
        "id", "jogo_id", "nome", "tipo", "conquistado"
    }

    if not obrigatorias.issubset(colunas):
        raise RuntimeError("Estrutura da tabela trofeus inválida.")

    novas_colunas = {
        "psn_trophy_id": "INTEGER",
        "psn_grupo": "TEXT",
        "imagem_url": "TEXT",
        "descricao": "TEXT"
    }

    for nome, tipo in novas_colunas.items():
        if nome not in colunas:
            conexao.execute(
                f"ALTER TABLE trofeus ADD COLUMN {nome} {tipo}"
            )

    conexao.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_trofeus_psn
        ON trofeus (jogo_id, psn_grupo, psn_trophy_id)
        WHERE psn_trophy_id IS NOT NULL
    """)

    conexao.commit()


def obter_jogos(conexao):
    return conexao.execute("""
        SELECT
            jogos.id,
            jogos.titulo,
            plataformas.nome AS plataforma
        FROM jogos
        JOIN plataformas
            ON jogos.plataforma_id = plataformas.id
        ORDER BY jogos.id
    """).fetchall()


def encontrar_jogo_psn(jogo, titulos):
    nome = normalizar(jogo["titulo"])
    plataforma = normalizar_plataforma(jogo["plataforma"])

    correspondencias = []

    for titulo in titulos:
        if normalizar(titulo.title_name) != nome:
            continue

        for p in (titulo.title_platform or []):
            if normalizar_plataforma(p) == plataforma:
                correspondencias.append((titulo, p))

    if len(correspondencias) != 1:
        return None, None

    return correspondencias[0]


def preparar_trofeus(trofeus_psn):
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

        tipo_original = getattr(
            trofeu.trophy_type, "value", ""
        )

        tipo = tipos.get(str(tipo_original).lower())

        if tipo is None:
            continue

        imagem = getattr(trofeu, "trophy_icon_url", None)
        descricao = getattr(trofeu, "trophy_detail", None)

        preparados.append({
            "psn_id": int(trofeu.trophy_id),
            "grupo": trofeu.trophy_group_id or "default",
            "nome": trofeu.trophy_name or "Troféu oculto",
            "tipo": tipo,
            "conquistado": 1 if trofeu.earned else 0,
            "imagem_url": imagem,
            "descricao": descricao
        })

    return preparados


def guardar_trofeus(conexao, jogo_id, trofeus):
    adicionados = 0
    atualizados = 0

    # Uma transação por jogo: evita guardar apenas
    # parte dos troféus se ocorrer um erro.
    with conexao:
        for t in trofeus:
            existente = conexao.execute("""
                SELECT id
                FROM trofeus
                WHERE jogo_id = ?
                  AND psn_trophy_id = ?
                  AND COALESCE(psn_grupo, 'default') = ?
            """, (
                jogo_id,
                t["psn_id"],
                t["grupo"]
            )).fetchone()

            if existente:
                conexao.execute("""
                    UPDATE trofeus
                    SET nome = ?,
                        tipo = ?,
                        conquistado = ?,
                        imagem_url = COALESCE(?, imagem_url),
                        descricao = COALESCE(?, descricao)
                    WHERE id = ?
                """, (
                    t["nome"],
                    t["tipo"],
                    t["conquistado"],
                    t["imagem_url"],
                    t["descricao"],
                    existente["id"]
                ))

                atualizados += 1

            else:
                conexao.execute("""
                    INSERT INTO trofeus (
                        jogo_id,
                        nome,
                        tipo,
                        conquistado,
                        psn_trophy_id,
                        psn_grupo,
                        imagem_url,
                        descricao
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    jogo_id,
                    t["nome"],
                    t["tipo"],
                    t["conquistado"],
                    t["psn_id"],
                    t["grupo"],
                    t["imagem_url"],
                    t["descricao"]
                ))

                adicionados += 1

    return adicionados, atualizados


def sincronizar():
    print("\n=== PLATINUMPATH - SINCRONIZAÇÃO PSN ===")

    if not DB.exists():
        print("Erro: base de dados não encontrada.")
        print(DB)
        return

    with ligar_base_dados() as conexao:
        jogos = obter_jogos(conexao)

    if not jogos:
        print("Não existem jogos registados.")
        return

    print("\nJogos disponíveis:")

    for jogo in jogos:
        print(
            f"{jogo['id']} - {jogo['titulo']} "
            f"({jogo['plataforma']})"
        )

    print("\n0 - Sincronizar TODOS os jogos")

    escolha = input("\nEscolhe o ID ou 0: ").strip()

    if not escolha.isdigit():
        print("ID inválido.")
        return

    jogo_id = int(escolha)

    if jogo_id == 0:
        selecionados = jogos
    else:
        selecionados = [
            j for j in jogos if j["id"] == jogo_id
        ]

    if not selecionados:
        print("Jogo não encontrado.")
        return

    npsso = getpass.getpass("\nIntroduz o NPSSO: ").strip()

    if not npsso:
        print("Operação cancelada.")
        return

    try:
        psn = PSNAWP(npsso)
        del npsso

        utilizador = psn.me()

        print("\nA consultar a PSN...")
        titulos = list(utilizador.trophy_titles(limit=None))

    except Exception as erro:
        print("Erro ao autenticar ou consultar a PSN:", erro)
        return

    try:
        criar_backup()

        with ligar_base_dados() as conexao:
            preparar_base_dados(conexao)

    except Exception as erro:
        print("Erro ao preparar a base de dados:", erro)
        return

    total_novos = 0
    total_atualizados = 0
    total_imagens = 0

    for jogo in selecionados:
        print("\n" + "=" * 45)
        print("JOGO:", jogo["titulo"])

        titulo, plataforma = encontrar_jogo_psn(
            jogo, titulos
        )

        if titulo is None:
            print("Correspondência PSN não encontrada ou ambígua.")
            continue

        if not titulo.np_communication_id:
            print("Jogo sem identificador PSN.")
            continue

        try:
            lista = list(utilizador.trophies(
                np_communication_id=titulo.np_communication_id,
                platform=plataforma,
                trophy_group_id="all",
                include_progress=True
            ))

            preparados = preparar_trofeus(lista)

            if not preparados:
                print("Nenhum troféu válido recebido.")
                continue

            with ligar_base_dados() as conexao:
                novos, atualizados = guardar_trofeus(
                    conexao,
                    jogo["id"],
                    preparados
                )

            conquistados = sum(
                t["conquistado"] for t in preparados
            )

            imagens = sum(
                1 for t in preparados if t["imagem_url"]
            )

            total_novos += novos
            total_atualizados += atualizados
            total_imagens += imagens

            print("Troféus recebidos:", len(preparados))
            print("Novos:", novos)
            print("Atualizados:", atualizados)
            print("Conquistados:", conquistados)
            print("Imagens recebidas:", imagens)

        except Exception as erro:
            print("Erro neste jogo:", erro)

    print("\n" + "=" * 45)
    print("SINCRONIZAÇÃO TERMINADA")
    print("Novos troféus:", total_novos)
    print("Troféus atualizados:", total_atualizados)
    print("Imagens recebidas:", total_imagens)
    print("=" * 45)


if __name__ == "__main__":
    sincronizar()
