
import sqlite3
import os
import secrets

from flask import Flask, abort, render_template, request, session, redirect, url_for, jsonify
import hmac
import sync_web
from init_db import criar_base_dados
from jogos import ligar_base_dados

app = Flask(__name__)
# Necessário para mensagens flash em pesquisa/guardar/remover amigos.
app.secret_key = os.environ.get("PLATINUMPATH_SECRET_KEY") or secrets.token_hex(32)

from amigos import amigos_bp
app.register_blueprint(amigos_bp)


def csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']


app.jinja_env.globals['csrf_token'] = csrf_token
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')


@app.before_request
def proteger_pedidos():
    if request.method == 'POST':
        esperado = session.get('csrf_token', '')
        recebido = request.form.get('csrf_token', '')
        if not esperado or not hmac.compare_digest(esperado.encode(), recebido.encode()):
            abort(403)


@app.after_request
def cabecalhos(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@app.post('/sincronizar')
def sincronizar_web():
    token = os.environ.get('PSN_NPSSO', '').strip()
    if not token:
        return jsonify(erro='Inicia a aplicação com INICIAR_COM_PSN.bat para autenticar.'), 400
    limite_str = request.form.get('limite', '30')
    if limite_str not in ('0', '30'):
        abort(400)
    limite = int(limite_str)
    if limite not in (0, 30):
        abort(400)
    if not sync_web.iniciar(token, limite):
        return jsonify(erro='Já existe uma sincronização em curso.'), 409
    return jsonify(sync_web.estado()), 202


@app.get('/sincronizar/estado')
def estado_sincronizacao():
    response = jsonify(sync_web.estado())
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.post('/jogo/<int:jogo_id>/objetivos')
def gerir_objetivo(jogo_id):
    acao = request.form.get('acao')
    with ligar_base_dados() as conexao:
        if not conexao.execute('SELECT 1 FROM jogos WHERE id=?', (jogo_id,)).fetchone():
            abort(404)
        if acao == 'adicionar':
            descricao = request.form.get('descricao', '').strip()
            if not 1 <= len(descricao) <= 250:
                abort(400)
            conexao.execute('INSERT INTO objetivos (jogo_id, descricao) VALUES (?,?)', (jogo_id, descricao))
        elif acao in ('alternar', 'eliminar'):
            objetivo_id = request.form.get('objetivo_id', type=int)
            sql = ('UPDATE objetivos SET concluido=1-concluido WHERE id=? AND jogo_id=?'
                   if acao == 'alternar' else 'DELETE FROM objetivos WHERE id=? AND jogo_id=?')
            if conexao.execute(sql, (objetivo_id, jogo_id)).rowcount != 1:
                abort(404)
        else:
            abort(400)
    return redirect(url_for('detalhe_jogo', jogo_id=jogo_id) + '#objetivos')




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
        total_jogos=len(jogos),
        psn_autenticada=bool(os.environ.get("PSN_NPSSO", "").strip())
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

        objetivos = conexao.execute("SELECT * FROM objetivos WHERE jogo_id=? ORDER BY concluido, id", (jogo_id,)).fetchall()

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
        estatisticas=estatisticas,
        objetivos=objetivos
    )


if __name__ == "__main__":
    criar_base_dados()
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
