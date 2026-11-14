
import getpass
import sqlite3
import unicodedata
import time
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
        "descricao": "TEXT",
        "data_conquista": "TEXT"
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


def contar_trofeus(conexao, jogo_id):
    resultado = conexao.execute("""
        SELECT COUNT(*)
        FROM trofeus
        WHERE jogo_id = ?
    """, (jogo_id,)).fetchone()

    return resultado[0]


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

        tipo_original = getattr(trofeu.trophy_type, "value", trofeu.trophy_type)
        tipo = tipos.get(str(tipo_original).lower())

        if tipo is None:
            continue

        imagem = getattr(trofeu, "trophy_icon_url", None)
        descricao = getattr(trofeu, "trophy_detail", None)

        data = getattr(trofeu, 'earned_date_time', None)
        data_conquista = data.isoformat() if data is not None and getattr(trofeu, 'earned', False) else None

        preparados.append({
            "data_conquista": data_conquista,
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

    # Cada jogo é guardado numa transação independente.
    # Se ocorrer um erro, não são guardados troféus parciais.

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
                        descricao = COALESCE(?, descricao),
                        data_conquista = CASE
                            WHEN ? = 1 THEN COALESCE(?, data_conquista)
                            ELSE NULL
                        END
                    WHERE id = ?
                """, (
                    t["nome"],
                    t["tipo"],
                    t["conquistado"],
                    t["imagem_url"],
                    t["descricao"],
                    t["conquistado"],
                    t["data_conquista"],
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
                        descricao,
                        data_conquista
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    jogo_id,
                    t["nome"],
                    t["tipo"],
                    t["conquistado"],
                    t["psn_id"],
                    t["grupo"],
                    t["imagem_url"],
                    t["descricao"],
                    t["data_conquista"]
                ))

                adicionados += 1

    return adicionados, atualizados


def _limite_api(exc):
    """Só repetir throttling e erros temporários de rede/servidor."""
    status = getattr(exc, 'status_code', None) or getattr(exc, 'code', None)
    if not status and getattr(exc, 'response', None) is not None:
        status = getattr(exc.response, 'status_code', None)
    if status is None and '429' in str(exc):
        status = 429
    # PSNAWP 2.x lança exceções próprias sem status_code.
    from psnawp_api.core.psnawp_exceptions import PSNAWPTooManyRequests, PSNAWPServerError
    return (isinstance(exc, (PSNAWPTooManyRequests, PSNAWPServerError))
            or status == 429 or status in (500, 502, 503, 504))


def consultar_trofeus(utilizador, np_id, plataforma, tentativas=3):
    """Consulta completa; aguarda em 429 sem criar entradas parciais na BD."""
    for tentativa in range(tentativas):
        try:
            return list(utilizador.trophies(
                np_communication_id=np_id,
                platform=plataforma,
                trophy_group_id='all',
                include_progress=True,
                limit=None
            ))
        except Exception as erro:
            if not _limite_api(erro) or tentativa == tentativas - 1:
                raise
            pausa = (10, 25, 45)[min(tentativa, 2)]
            print(f'PSN temporariamente indisponível (429/5xx). Pausa de {pausa}s antes da nova tentativa.')
            time.sleep(pausa)


def total_esperado(titulo):
    dados = getattr(titulo, 'defined_trophies', None)
    if dados is None:
        return 0
    return sum(int(getattr(dados, k, 0) or 0) for k in ('bronze', 'silver', 'gold', 'platinum'))


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

    print(f"\nJogos disponíveis: {len(jogos)}")

    for jogo in jogos:
        print(
            f"{jogo['id']} - {jogo['titulo']} "
            f"({jogo['plataforma']})"
        )

    print("\n0 - Sincronizar apenas jogos sem troféus")
    print("A - Atualizar todos os jogos (muitos pedidos à PSN)")
    print("ID - Sincronizar ou atualizar um jogo específico")

    escolha = input("\nEscolhe 0, A ou um ID: ").strip().lower()

    if escolha not in ('0', 'a') and not escolha.isdigit():
        print("Opção inválida.")
        return

    jogo_id = int(escolha) if escolha.isdigit() else -1

    if jogo_id in (0, -1):
        selecionados = jogos
    else:
        selecionados = [j for j in jogos if j["id"] == jogo_id]

    if not selecionados:
        print("Jogo não encontrado.")
        return

    # Filtrar jogos já sincronizados antes de consultar a PSN.
    ignorados = 0

    if jogo_id == 0:
        pendentes = []

        with ligar_base_dados() as conexao:
            for jogo in selecionados:
                quantidade = contar_trofeus(
                    conexao,
                    jogo["id"]
                )

                if quantidade > 0:
                    ignorados += 1
                else:
                    pendentes.append(jogo)

        selecionados = pendentes

        print("\n=== ESTADO DA BIBLIOTECA ===")
        print("Total de jogos:", len(jogos))
        print("Jogos com troféus:", ignorados)
        print("Jogos por sincronizar:", len(selecionados))

        if not selecionados:
            print("\nTodos os jogos já têm troféus guardados.")
            return

    npsso = getpass.getpass(
        "\nIntroduz o NPSSO: "
    ).strip()

    if not npsso:
        print("Operação cancelada.")
        return

    try:
        psn = PSNAWP(npsso)
        del npsso

        utilizador = psn.me()

        print("\nA consultar o histórico PSN...")
        titulos = list(
            utilizador.trophy_titles(limit=None)
        )

        print("Títulos PSN encontrados:", len(titulos))

    except KeyboardInterrupt:
        print("\nOperação interrompida.")
        return

    except Exception as erro:
        print("Erro ao consultar a PSN:", erro)
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
    concluidos = 0
    falhados = 0
    interrompido = False

    total_jogos = len(selecionados)

    print("\n=== INÍCIO DA SINCRONIZAÇÃO ===")
    print("Jogos a processar:", total_jogos)
    print("A PSN pode impor pausas entre pedidos.")
    print("Podes interromper com Ctrl+C.\n")

    try:
        for indice, jogo in enumerate(selecionados, 1):
            print("\n" + "=" * 45, flush=True)

            print(
                f"PROGRESSO: {indice}/{total_jogos}",
                flush=True
            )

            print(
                "JOGO:", jogo["titulo"],
                flush=True
            )

            titulo, plataforma = encontrar_jogo_psn(
                jogo,
                titulos
            )

            if titulo is None:
                print(
                    "Correspondência PSN não encontrada "
                    "ou ambígua."
                )
                falhados += 1
                continue

            if not titulo.np_communication_id:
                print("Jogo sem identificador PSN.")
                falhados += 1
                continue

            try:
                print(
                    "A consultar troféus na PSN...",
                    flush=True
                )

                lista = consultar_trofeus(utilizador, titulo.np_communication_id, plataforma)
                preparados = preparar_trofeus(lista)
                esperado = total_esperado(titulo)
                if esperado and len(preparados) < esperado:
                    print(f'Resposta incompleta ({len(preparados)}/{esperado}). Sem alterar a BD.')
                    falhados += 1
                    continue

                if not preparados:
                    print("Nenhum troféu válido recebido.")
                    falhados += 1
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
                    1 for t in preparados
                    if t["imagem_url"]
                )

                total_novos += novos
                total_atualizados += atualizados
                total_imagens += imagens

                concluidos += 1

                print("Troféus recebidos:", len(preparados))
                print("Novos:", novos)
                print("Atualizados:", atualizados)
                print("Conquistados:", conquistados)
                print("Imagens recebidas:", imagens)

                print(
                    f"[OK] {concluidos} jogos "
                    "sincronizados nesta execução."
                )

            except KeyboardInterrupt:
                raise

            except Exception as erro:
                falhados += 1
                print(
                    f"[ERRO] {jogo['titulo']}: {erro}"
                )
                print(
                    "Este jogo será tentado "
                    "na próxima execução."
                )
                continue

    except KeyboardInterrupt:
        interrompido = True
        print("\n\nSincronização interrompida pelo utilizador.")
        print("Os jogos concluídos continuam guardados.")

    finally:
        print("\n" + "=" * 45)

        if interrompido:
            print("SINCRONIZAÇÃO INTERROMPIDA")
        else:
            print("SINCRONIZAÇÃO TERMINADA")

        print("Jogos sincronizados nesta execução:", concluidos)
        print("Jogos já ignorados:", ignorados)
        print("Jogos com erro ou sem correspondência:", falhados)
        print("Novos troféus:", total_novos)
        print("Troféus atualizados:", total_atualizados)
        print("Imagens recebidas:", total_imagens)

        if interrompido:
            print("\nPara continuar, executa novamente")
            print("o programa e escolhe 0.")

        print("=" * 45)


if __name__ == "__main__":
    sincronizar()
