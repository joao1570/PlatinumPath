
import sqlite3

from flask import Flask, abort, render_template
from jogos import ligar_base_dados

app = Flask(__name__)


@app.route("/")
def inicio():
    with ligar_base_dados() as conexao:
        conexao.row_factory = sqlite3.Row

        jogos = conexao.execute("""
            SELECT
                j.id,
                j.titulo,
                j.imagem_url,
                p.nome AS plataforma,
                COUNT(t.id) AS total,
                COALESCE(SUM(t.conquistado), 0) AS conquistados,
                CASE
                    WHEN COUNT(t.id) = 0 THEN 0
                    ELSE ROUND(
                        100.0 * SUM(t.conquistado) / COUNT(t.id)
                    )
                END AS progresso,
                COALESCE(SUM(
                    CASE
                        WHEN t.tipo = 'Platina'
                        AND t.conquistado = 1
                        THEN 1 ELSE 0
                    END
                ), 0) AS platinas
            FROM jogos j
            JOIN plataformas p
                ON p.id = j.plataforma_id
            LEFT JOIN trofeus t
                ON t.jogo_id = j.id
            GROUP BY j.id, j.titulo, j.imagem_url, p.nome
            ORDER BY j.id DESC
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
        jogo = conexao.execute("""
            SELECT j.id, j.titulo, p.nome
            FROM jogos j
            JOIN plataformas p
                ON j.plataforma_id = p.id
            WHERE j.id = ?
        """, (jogo_id,)).fetchone()

        if jogo is None:
            abort(404)

        trofeus = conexao.execute("""
            SELECT nome, tipo, conquistado
            FROM trofeus
            WHERE jogo_id = ?
            ORDER BY
                CASE tipo
                    WHEN 'Platina' THEN 1
                    WHEN 'Ouro' THEN 2
                    WHEN 'Prata' THEN 3
                    WHEN 'Bronze' THEN 4
                END,
                nome
        """, (jogo_id,)).fetchall()

    total = len(trofeus)
    conquistados = sum(t[2] for t in trofeus)
    progresso = round(100 * conquistados / total) if total else 0

    return render_template(
        "jogo.html",
        jogo=jogo,
        trofeus=trofeus,
        total=total,
        conquistados=conquistados,
        progresso=progresso
    )


if __name__ == "__main__":
    app.run(debug=True)
