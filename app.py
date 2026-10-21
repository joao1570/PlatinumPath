
import sqlite3
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

BASE_DADOS = "platinumpath.db"


def criar_base_dados():
    conexao = sqlite3.connect(BASE_DADOS)
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jogos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            plataforma TEXT NOT NULL
        )
    """)

    conexao.commit()
    conexao.close()


@app.route("/")
def inicio():
    conexao = sqlite3.connect(BASE_DADOS)
    conexao.row_factory = sqlite3.Row

    jogos = conexao.execute(
        "SELECT * FROM jogos ORDER BY id DESC"
    ).fetchall()

    conexao.close()

    return render_template("index.html", jogos=jogos)


@app.route("/adicionar", methods=["POST"])
def adicionar_jogo():
    nome = request.form.get("nome", "").strip()
    plataforma = request.form.get("plataforma", "")

    if not nome or len(nome) > 150:
        return "Nome do jogo inválido.", 400

    if plataforma not in ["PS3", "PS4", "PS5"]:
        return "Plataforma inválida.", 400

    conexao = sqlite3.connect(BASE_DADOS)

    conexao.execute(
        "INSERT INTO jogos (nome, plataforma) VALUES (?, ?)",
        (nome, plataforma)
    )

    conexao.commit()
    conexao.close()

    return redirect(url_for("inicio"))


if __name__ == "__main__":
    criar_base_dados()
    app.run(debug=True)
