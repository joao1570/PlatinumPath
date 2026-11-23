
"""Atualizar os trofeus recentes do PlatinumPath."""

from __future__ import annotations

import argparse
import os
import getpass
import re
import sqlite3
import sys
import time
import unicodedata
from datetime import datetime, timezone
from contextlib import closing
from pathlib import Path

from psnawp_api import PSNAWP

BASE = Path(__file__).resolve().parent
CANDIDATAS = [
    BASE / "Database" / "platinumpath.db",
    BASE / "database" / "platinumpath.db",
]
DB = next(
    (p for p in CANDIDATAS if p.is_file()),
    CANDIDATAS[0],
)
BACKUP = DB.parent / "backups"


def chave(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(
        ch for ch in s
        if not unicodedata.combining(ch)
    )
    return re.sub(r"[^a-z0-9]", "", s.casefold())


def plataforma(p):
    return str(
        getattr(p, "value", p)
    ).upper().replace(" ", "").replace("_", "")


def ordem(t):
    d = getattr(t, "last_updated_datetime", None)
    if d is None:
        d = getattr(t, "last_updated_date_time", None)
    if not isinstance(d, datetime):
        return float("-inf")
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.timestamp()


def campos_trofeus(t):
    ttype = getattr(t, "trophy_type", None)
    tipo = str(
        getattr(ttype, "value", ttype)
    ).casefold()

    tipo = {
        "bronze": "Bronze",
        "silver": "Prata",
        "gold": "Ouro",
        "platinum": "Platina",
    }.get(tipo)

    trophy_id = getattr(t, "trophy_id", None)

    if tipo is None or trophy_id is None:
        raise ValueError(
            "Trofeu sem identificador ou tipo valido"
        )

    ganho = int(bool(getattr(t, "earned", False)))
    data = getattr(t, "earned_date_time", None)

    return (
        int(trophy_id),
        getattr(t, "trophy_group_id", None) or "default",
        getattr(t, "trophy_name", None) or "Trofeu oculto",
        tipo,
        ganho,
        getattr(t, "trophy_icon_url", None),
        getattr(t, "trophy_detail", None),
        data.isoformat()
        if ganho and isinstance(data, datetime)
        else None,
    )


def total_esperado(titulo):
    d = getattr(titulo, "defined_trophies", None)
    if not d:
        return 0

    return sum(
        int(
            (
                d.get(c)
                if isinstance(d, dict)
                else getattr(d, c, 0)
            ) or 0
        )
        for c in (
            "bronze", "silver", "gold", "platinum"
        )
    )


def conexao():
    db = sqlite3.connect(DB, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def confirmar_conta(db, online_id):
    try:
        existente = db.execute(
            "SELECT online_id FROM perfil_psn WHERE id=1"
        ).fetchone()
    except sqlite3.OperationalError:
        raise RuntimeError(
            "A base de dados nao contem o perfil PSN"
        ) from None

    if existente:
        if existente["online_id"].casefold() != online_id.casefold():
            raise RuntimeError(
                "Conta PSN diferente da base de dados. "
                "Nenhum dado foi alterado."
            )


def criar_backup():
    BACKUP.mkdir(exist_ok=True, parents=True)

    destino = BACKUP / (
        "platinumpath_antes_sync_"
        + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        + ".db"
    )

    with closing(sqlite3.connect(DB)) as src:
        with closing(sqlite3.connect(destino)) as dst:
            src.backup(dst)

    print("Copia de seguranca:", destino.name)


def preparar_bd(db):
    campos = (
        ("trofeus", "psn_trophy_id", "INTEGER"),
        ("trofeus", "psn_grupo", "TEXT"),
        ("trofeus", "imagem_url", "TEXT"),
        ("trofeus", "descricao", "TEXT"),
        ("trofeus", "data_conquista", "TEXT"),
        ("jogos", "ultima_conquista", "TEXT"),
    )

    for tabela, campo, tipo in campos:
        existentes = {
            r["name"]
            for r in db.execute(
                f"PRAGMA table_info({tabela})"
            )
        }

        if not existentes:
            raise RuntimeError(
                f"Tabela obrigatoria em falta: {tabela}"
            )

        if campo not in existentes:
            db.execute(
                f"ALTER TABLE {tabela} "
                f"ADD COLUMN {campo} {tipo}"
            )

    db.commit()


def atualizar_jogo(db, titulo, plat, trofeus):
    plataforma_id = db.execute(
        "SELECT id FROM plataformas WHERE UPPER(nome)=?",
        (plat,),
    ).fetchone()

    if not plataforma_id:
        raise ValueError(
            "Plataforma nao encontrada na base de dados"
        )

    pid = plataforma_id[0]

    locais = db.execute(
        "SELECT id, titulo FROM jogos WHERE plataforma_id=?",
        (pid,),
    ).fetchall()

    encontrados = [
        j for j in locais
        if chave(j["titulo"]) == chave(titulo.title_name)
    ]

    if len(encontrados) > 1:
        raise ValueError(
            "Mais de um jogo local com o mesmo nome"
        )

    with db:
        if encontrados:
            jogo = encontrados[0]["id"]
        else:
            jogo = db.execute(
                """INSERT INTO jogos
                   (titulo, plataforma_id, imagem_url)
                   VALUES (?, ?, ?)""",
                (
                    titulo.title_name,
                    pid,
                    getattr(titulo, "title_icon_url", None),
                ),
            ).lastrowid

        db.execute("UPDATE jogos SET imagem_url=COALESCE(?, imagem_url) WHERE id=?",
                   (getattr(titulo, "title_icon_url", None), jogo))

        novas = 0

        for t in trofeus:
            (
                ident, grupo, nome, tipo,
                ganho, imagem, descricao, data
            ) = campos_trofeus(t)

            anterior = db.execute(
                """SELECT id, conquistado
                   FROM trofeus
                   WHERE jogo_id=?
                   AND psn_trophy_id=?
                   AND COALESCE(
                       psn_grupo, 'default'
                   )=?""",
                (jogo, ident, grupo),
            ).fetchone()

            if anterior:
                novas += int(
                    ganho == 1
                    and anterior["conquistado"] == 0
                )

                db.execute(
                    """UPDATE trofeus
                       SET nome=?,
                           tipo=?,
                           conquistado=MAX(
                               conquistado, ?
                           ),
                           imagem_url=COALESCE(
                               ?, imagem_url
                           ),
                           descricao=COALESCE(
                               ?, descricao
                           ),
                           data_conquista=COALESCE(
                               ?, data_conquista
                           )
                       WHERE id=?""",
                    (
                        nome, tipo, ganho,
                        imagem, descricao, data,
                        anterior["id"],
                    ),
                )
            else:
                novas += ganho

                db.execute(
                    """INSERT INTO trofeus
                       (
                         jogo_id, nome, tipo,
                         conquistado, psn_trophy_id,
                         psn_grupo, imagem_url,
                         descricao, data_conquista
                       )
                       VALUES (
                         ?, ?, ?, ?, ?, ?, ?, ?, ?
                       )""",
                    (
                        jogo, nome, tipo, ganho,
                        ident, grupo, imagem,
                        descricao, data,
                    ),
                )

        ultima = db.execute(
            """SELECT MAX(data_conquista)
               FROM trofeus
               WHERE jogo_id=?
               AND conquistado=1""",
            (jogo,),
        ).fetchone()[0]

        if ultima:
            db.execute(
                """UPDATE jogos
                   SET ultima_conquista=?
                   WHERE id=?""",
                (ultima, jogo),
            )

    return novas


def atualizar_perfil(db, eu):
    resumo = eu.trophy_summary()
    t = resumo.earned_trophies

    with db:
        db.execute(
            """INSERT INTO perfil_psn
               (
                 id, online_id, nivel, progresso,
                 bronze, prata, ouro, platina,
                 atualizado_em
               )
               VALUES (
                 1, ?, ?, ?, ?, ?, ?, ?,
                 CURRENT_TIMESTAMP
               )
               ON CONFLICT(id) DO UPDATE SET
                 online_id=excluded.online_id,
                 nivel=excluded.nivel,
                 progresso=excluded.progresso,
                 bronze=excluded.bronze,
                 prata=excluded.prata,
                 ouro=excluded.ouro,
                 platina=excluded.platina,
                 atualizado_em=CURRENT_TIMESTAMP""",
            (
                eu.online_id,
                resumo.trophy_level,
                resumo.progress,
                t.bronze,
                t.silver,
                t.gold,
                t.platinum,
            ),
        )


def consultar_trofeus(eu, titulo, p, tentativas=3):
    for i in range(tentativas):
        try:
            return list(
                eu.trophies(
                    np_communication_id=(
                        titulo.np_communication_id
                    ),
                    platform=p,
                    trophy_group_id="all",
                    include_progress=True,
                    limit=None,
                )
            )
        except Exception as e:
            texto = str(e).lower()
            status = (
                getattr(e, "status_code", None)
                or getattr(e, "code", None)
            )

            if status is None:
                resposta = getattr(e, "response", None)
                if resposta is not None:
                    status = getattr(
                        resposta, "status_code", None
                    )

            temporario = (
                status in (
                    429, 500, 502, 503, 504
                )
                or any(
                    s in texto
                    for s in (
                        "too many requests",
                        "rate limit",
                        "429",
                        "server error",
                        "503",
                    )
                )
            )

            if not (temporario or type(e).__name__ in ("PSNAWPTooManyRequests", "PSNAWPServerError")) or i == tentativas - 1:
                raise

            atraso = (10, 25, 45)[i]
            print(
                "Limite temporario da PSN. "
                f"Nova tentativa em {atraso}s."
            )
            time.sleep(atraso)


def sincronizar(limite=30):
    if not DB.is_file():
        print(
            "ERRO: base de dados nao encontrada."
        )
        print(
            "Executa este ficheiro dentro "
            "da pasta original PlatinumPath."
        )
        return 1

    with closing(conexao()) as db:
        for tabela in (
            "jogos",
            "trofeus",
            "perfil_psn",
            "plataformas",
        ):
            existe = db.execute(
                """SELECT 1
                   FROM sqlite_master
                   WHERE type='table' AND name=?""",
                (tabela,),
            ).fetchone()

            if not existe:
                print(
                    "ERRO: falta a tabela",
                    tabela,
                )
                return 1

    token = os.environ.get("PSN_NPSSO", "").strip() or getpass.getpass(
        "NPSSO da PlayStation (nao e guardado): "
    ).strip()

    if not token:
        print("Cancelado: NPSSO vazio.")
        return 1

    try:
        eu = PSNAWP(token).me()
        del token

        print("Conta PSN:", eu.online_id)

        with closing(conexao()) as db:
            confirmar_conta(db, eu.online_id)

        print(
            "A consultar os jogos na PSN..."
        )

        titulos = list(
            eu.trophy_titles(
                limit=None,
                page_size=50,
            )
        )

    except Exception as e:
        print(
            "ERRO na autenticacao ou consulta PSN:",
            type(e).__name__,
        )
        return 1

    validos = [
        t for t in titulos
        if getattr(
            t, "np_communication_id", None
        )
        and getattr(t, "title_name", None)
        and getattr(t, "title_platform", None)
        and any(plataforma(p) in ("PS3", "PS4", "PS5") for p in t.title_platform)
    ]

    validos.sort(
        key=ordem,
        reverse=True,
    )

    escolhidos = (
        validos[:limite]
        if limite else validos
    )

    if not escolhidos:
        print(
            "A PSN nao devolveu jogos com trofeus."
        )
        return 1

    print(
        f"Vou verificar {len(escolhidos)} "
        "jogos (os mais recentes primeiro)."
    )

    criar_backup()

    feitos = 0
    falhas = 0
    ganhos = 0

    with closing(conexao()) as db:
        preparar_bd(db)

        for indice, titulo in enumerate(
            escolhidos, 1
        ):
            psn_platforms = sorted(
                (
                    p for p in titulo.title_platform
                    if plataforma(p) in (
                        "PS3", "PS4", "PS5"
                    )
                ),
                key=plataforma,
            )

            for p in psn_platforms:
                plat = plataforma(p)

                print(
                    f"[{indice}/{len(escolhidos)}] "
                    f"{titulo.title_name} ({plat})",
                    flush=True,
                )

                try:
                    lista = consultar_trofeus(
                        eu, titulo, p
                    )

                    esperado = total_esperado(titulo)

                    if not lista or (
                        esperado
                        and len({(campos_trofeus(t)[0], campos_trofeus(t)[1]) for t in lista}) < esperado
                    ):
                        raise ValueError(
                            "Lista incompleta: "
                            f"{len(lista)}/{esperado} "
                            "trofeus"
                        )

                    num = atualizar_jogo(
                        db, titulo, plat, lista
                    )

                    ganhos += num
                    feitos += 1

                    print(
                        f"OK: {num} conquistas novas"
                    )

                except KeyboardInterrupt:
                    print(
                        "Interrompido. Os jogos ja "
                        "concluidos ficaram guardados."
                    )
                    return 130

                except Exception as e:
                    falhas += 1
                    print(
                        "Falhou este jogo:", type(e).__name__
                    )

        try:
            atualizar_perfil(db, eu)
            print(
                "Perfil PSN atualizado."
            )
        except Exception as e:
            falhas += 1
            print(
                "Aviso: nao consegui "
                "atualizar o perfil:",
                type(e).__name__,
            )

    print(
        f"\nCONCLUIDO: {feitos} jogos atualizados, "
        f"{ganhos} conquistas novas, "
        f"{falhas} erros."
    )

    print(
        "Abre o PlatinumPath novamente "
        "e atualiza a pagina com Ctrl+F5."
    )

    return 0 if not falhas else 2


def main():
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--jogos",
        type=int,
        default=30,
        help=(
            "Quantos titulos recentes atualizar "
            "(0=todos)"
        ),
    )

    args = ap.parse_args()

    if args.jogos < 0:
        ap.error(
            "--jogos nao pode ser negativo"
        )

    return sincronizar(args.jogos)


if __name__ == "__main__":
    sys.exit(main())
