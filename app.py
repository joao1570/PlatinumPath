
import sqlite3

from flask import Flask, abort, render_template
from jogos import ligar_base_dados

app = Flask(__name__)

from amigos import amigos_bp
app.register_blueprint(amigos_bp)



def coluna_existe(conexao, tabela, coluna):
    colunas = conexao.execute(
        f"PRAGMA table_info({tabela})"
    ).fetchall()

    return any(c["name"] == coluna for c in colunas)


@app.route("/")
def inicio():
    with ligar_base_dados() as conexao:
        conexao.row_factory = sqlite3.Row

        tem_data = coluna_existe(
            conexao, "trofeus", "data_conquista"
        )

        if tem_data:
            ultima_conquista_sql = """
                MAX(
                    CASE
                        WHEN t.conquistado = 1
                        THEN t.data_conquista
                        ELSE NULL
                    END
                )
            """
        else:
            ultima_conquista_sql = "NULL"

        jogos = conexao.execute(f"""
            SELECT
                j.id,
                j.titulo,
                j.imagem_url,
                p.nome AS plataforma,
                COUNT(t.id) AS total,
                COALESCE(SUM(t.conquistado), 0)
                    AS conquistados,
                CASE
                    WHEN COUNT(t.id) = 0 THEN 0
                    ELSE ROUND(
                        100.0 *
                        COALESCE(SUM(t.conquistado), 0)
                        / COUNT(t.id)
                    )
                END AS progresso,
                COALESCE(SUM(
                    CASE
                        WHEN t.tipo = 'Platina'
                        AND t.conquistado = 1
                        THEN 1 ELSE 0
                    END
                ), 0) AS platinas,
                {ultima_conquista_sql} AS ultima_conquista

            FROM jogos j

            JOIN plataformas p
                ON p.id = j.plataforma_id

            LEFT JOIN trofeus t
                ON t.jogo_id = j.id

            GROUP BY
                j.id,
                j.titulo,
                j.imagem_url,
                p.nome

            ORDER BY
                CASE
                    WHEN ultima_conquista IS NULL THEN 1
                    ELSE 0
                END,
                ultima_conquista DESC,
                j.titulo COLLATE NOCASE ASC
        """).fetchall()

        perfil = conexao.execute("""
            SELECT *
            FROM perfil_psn
            WHERE id = 1
        """).fetchone()

    return render_template(
        "index.html",
        jogos=jogos,
        perfil=perfil,
        total_jogos=len(jogos)
    )


@app.route("/jogo/<int:jogo_id>")
def detalhe_jogo(jogo_id):
    with ligar_base_dados() as conexao:
        conexao.row_factory = sqlite3.Row

        jogo = conexao.execute("""
            SELECT
                j.id,
                j.titulo,
                p.nome AS plataforma,
                j.imagem_url

            FROM jogos j

            JOIN plataformas p
                ON j.plataforma_id = p.id

            WHERE j.id = ?
        """, (jogo_id,)).fetchone()

        if jogo is None:
            abort(404)

        tem_data = coluna_existe(
            conexao, "trofeus", "data_conquista"
        )

        if tem_data:
            data_sql = "data_conquista"
            ordenacao_sql = """
                CASE
                    WHEN conquistado = 1 THEN 0
                    ELSE 1
                END,
                CASE
                    WHEN conquistado = 1
                    THEN data_conquista
                    ELSE NULL
                END DESC,
            """
        else:
            data_sql = "NULL AS data_conquista"
            ordenacao_sql = """
                CASE
                    WHEN conquistado = 1 THEN 0
                    ELSE 1
                END,
            """

        trofeus = conexao.execute(f"""
            SELECT
                id,
                nome,
                tipo,
                conquistado,
                imagem_url,
                descricao,
                psn_trophy_id,
                psn_grupo,
                {data_sql}

            FROM trofeus

            WHERE jogo_id = ?

            ORDER BY
                {ordenacao_sql}
                CASE tipo
                    WHEN 'Platina' THEN 1
                    WHEN 'Ouro' THEN 2
                    WHEN 'Prata' THEN 3
                    WHEN 'Bronze' THEN 4
                    ELSE 5
                END,
                nome COLLATE NOCASE ASC
        """, (jogo_id,)).fetchall()

    total = len(trofeus)

    conquistados = sum(
        t["conquistado"] for t in trofeus
    )

    progresso = (
        round(100 * conquistados / total)
        if total else 0
    )

    estatisticas = {}

    for tipo in ("Platina", "Ouro", "Prata", "Bronze"):
        lista = [
            t for t in trofeus
            if t["tipo"] == tipo
        ]

        estatisticas[tipo] = {
            "total": len(lista),
            "conquistados": sum(
                t["conquistado"] for t in lista
            )
        }

    return render_template(
        "jogo.html",
        jogo=jogo,
        trofeus=trofeus,
        total=total,
        conquistados=conquistados,
        progresso=progresso,
        estatisticas=estatisticas
    )


if __name__ == "__main__":
    app.run(debug=True)
