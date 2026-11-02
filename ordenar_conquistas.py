"""PlatinumPath: acrescenta datas de conquistas, atualiza a PSN e ordena a interface.
Executar na pasta raiz do projeto: venv\\Scripts\\python.exe ordenar_conquistas.py
"""
import getpass
import re
import shutil
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path

from psnawp_api import PSNAWP

RAIZ = Path(__file__).resolve().parent
DB = RAIZ / 'database' / 'platinumpath.db'
APP = RAIZ / 'app.py'
INDEX = RAIZ / 'templates' / 'index.html'
BACKUP = RAIZ / 'database' / 'backups'


def norm(valor):
    texto = unicodedata.normalize('NFKD', str(valor or ''))
    return ''.join(c for c in texto if not unicodedata.combining(c)).casefold().strip()


def plat(valor):
    return str(getattr(valor, 'value', valor)).upper().replace(' ', '').replace('_', '')


def iso(data):
    return data.isoformat() if data else None


def adicionar_coluna(db, tabela, nome, tipo='TEXT'):
    cols = {linha[1] for linha in db.execute(f'PRAGMA table_info({tabela})')}
    if nome not in cols:
        db.execute(f'ALTER TABLE {tabela} ADD COLUMN {nome} {tipo}')


def substituir_exato(texto, antigo, novo, ficheiro):
    if novo in texto:
        return texto
    if texto.count(antigo) != 1:
        raise RuntimeError(f'Não encontrei o trecho esperado em {ficheiro}; não alterei os ficheiros.')
    return texto.replace(antigo, novo, 1)


def atualizar_interface():
    app = APP.read_text(encoding='utf-8')
    index = INDEX.read_text(encoding='utf-8')

    # Ordenação inicial da biblioteca pelo último troféu conquistado.
    app = substituir_exato(
        app,
        '                j.imagem_url,\n                p.nome AS plataforma,',
        '                j.imagem_url,\n                j.ultima_conquista,\n                p.nome AS plataforma,',
        APP
    )
    app = substituir_exato(
        app,
        'ORDER BY j.id DESC',
        'ORDER BY j.ultima_conquista IS NULL, j.ultima_conquista DESC, j.id DESC',
        APP
    )
    app = substituir_exato(
        app,
        '                psn_grupo\n            FROM trofeus',
        '                psn_grupo,\n                data_conquista\n            FROM trofeus',
        APP
    )
    if 'data_conquista IS NULL' not in app:
        # Não depender dos espaços/indentação do SQL no app.py.
        padrao = (
            r"ORDER BY\s+CASE\s+tipo\s+"
            r"WHEN\s+'Platina'\s+THEN\s+1\s+"
            r"WHEN\s+'Ouro'\s+THEN\s+2\s+"
            r"WHEN\s+'Prata'\s+THEN\s+3\s+"
            r"WHEN\s+'Bronze'\s+THEN\s+4\s+"
            r"ELSE\s+5\s+END,\s+nome"
        )
        substituicao = (
            "ORDER BY\n"
            "                data_conquista IS NULL,\n"
            "                data_conquista DESC,\n"
            "                CASE tipo\n"
            "                    WHEN 'Platina' THEN 1\n"
            "                    WHEN 'Ouro' THEN 2\n"
            "                    WHEN 'Prata' THEN 3\n"
            "                    WHEN 'Bronze' THEN 4\n"
            "                    ELSE 5\n"
            "                END,\n"
            "                nome"
        )
        app, quantidade = re.subn(padrao, substituicao, app)
        if quantidade != 1:
            raise RuntimeError(
                f'Esperava encontrar uma ordenação de troféus em app.py, encontrei {quantidade}. '
                'Não foram alterados ficheiros de interface.'
            )

    # O seletor do JavaScript já usa a ordem recebida do Flask.
    index = substituir_exato(
        index,
        '<option value="original">Ordem original</option>',
        '<option value="original">Último troféu conquistado</option>',
        INDEX
    )

    # Segurança: só escreve depois de validar todas as substituições.
    APP.write_text(app, encoding='utf-8')
    INDEX.write_text(index, encoding='utf-8')


def executar():
    if not all(p.exists() for p in (DB, APP, INDEX)):
        print('Faltam ficheiros. Guarda este script na pasta principal do PlatinumPath.')
        print('DB:', DB)
        return

    BACKUP.mkdir(parents=True, exist_ok=True)
    sufixo = datetime.now().strftime('%Y%m%d_%H%M%S')
    with sqlite3.connect(DB) as origem, sqlite3.connect(BACKUP / f'antes_datas_{sufixo}.db') as destino:
        origem.backup(destino)
    shutil.copy2(APP, BACKUP / f'app_{sufixo}.py')
    shutil.copy2(INDEX, BACKUP / f'index_{sufixo}.html')
    print('Backups criados.')

    with sqlite3.connect(DB) as db:
        adicionar_coluna(db, 'jogos', 'ultima_conquista')
        adicionar_coluna(db, 'trofeus', 'data_conquista')
        db.execute('''CREATE TABLE IF NOT EXISTS verificacao_datas_psn (
            jogo_id INTEGER PRIMARY KEY, verificado_em TEXT NOT NULL
        )''')
        db.commit()

    try:
        atualizar_interface()
        print('Interface preparada: jogos e troféus ordenados por data.')
    except Exception as exc:
        print('Não foi possível atualizar a interface:', exc)
        print('Os backups estão guardados; as datas podem ser sincronizadas.')
        return

    resposta = input('Recuperar agora as datas da PSN? (s/n): ').strip().lower()
    if resposta != 's':
        print('Podes executar este ficheiro mais tarde para sincronizar as datas.')
        return

    segredo = getpass.getpass('NPSSO (não fica guardado): ').strip()
    if not segredo:
        return
    try:
        psn = PSNAWP(segredo)
        del segredo
        utilizador = psn.me()
        titulos = list(utilizador.trophy_titles(limit=None))
    except Exception as exc:
        print('Falha ao consultar a PSN:', exc)
        return

    indice = {}
    for titulo in titulos:
        for plataforma in (titulo.title_platform or []):
            chave = (norm(titulo.title_name), plat(plataforma))
            indice.setdefault(chave, []).append((titulo, plataforma))

    with sqlite3.connect(DB) as db:
        db.row_factory = sqlite3.Row
        jogos = db.execute('''SELECT j.id, j.titulo, p.nome AS plataforma
                              FROM jogos j JOIN plataformas p ON p.id=j.plataforma_id
                              WHERE j.id NOT IN (SELECT jogo_id FROM verificacao_datas_psn)
                              ORDER BY j.id''').fetchall()

    print(f'Jogos ainda por verificar: {len(jogos)}')
    feitos = erros = 0
    try:
        for numero, jogo in enumerate(jogos, 1):
            nome = jogo['titulo']
            candidatos = indice.get((norm(nome), plat(jogo['plataforma'])), [])
            if len(candidatos) != 1:
                print(f'[{numero}/{len(jogos)}] Ignorado (correspondência ambígua/ausente): {nome}')
                erros += 1
                continue
            titulo, plataforma = candidatos[0]
            try:
                print(f'[{numero}/{len(jogos)}] {nome}...', flush=True)
                lista = list(utilizador.trophies(
                    np_communication_id=titulo.np_communication_id,
                    platform=plataforma,
                    trophy_group_id='all',
                    include_progress=True
                ))
                with sqlite3.connect(DB) as db:
                    with db:
                        datas = []
                        for trofeu in lista:
                            if trofeu.trophy_id is None:
                                continue
                            data = iso(getattr(trofeu, 'earned_date_time', None))
                            if data:
                                datas.append(data)
                            grupo = getattr(trofeu, 'trophy_group_id', None) or 'default'
                            db.execute('''UPDATE trofeus SET data_conquista = ?, conquistado = ?
                                          WHERE jogo_id = ? AND psn_trophy_id = ?
                                            AND COALESCE(psn_grupo, 'default') = ?''',
                                       (data, int(bool(trofeu.earned)), jogo['id'],
                                        trofeu.trophy_id, grupo))
                        ultima = iso(getattr(titulo, 'last_updated_datetime', None))
                        # A data máxima de troféus individuais tem prioridade quando disponível.
                        if datas:
                            ultima = max(datas)
                        db.execute('UPDATE jogos SET ultima_conquista = ? WHERE id = ?',
                                   (ultima, jogo['id']))
                        db.execute('''INSERT OR REPLACE INTO verificacao_datas_psn
                                      (jogo_id, verificado_em) VALUES (?, ?)''',
                                   (jogo['id'], datetime.now().isoformat()))
                feitos += 1
            except Exception as exc:
                erros += 1
                print(f'  Falha: {exc}. Continua na próxima execução.')
    except KeyboardInterrupt:
        print('\nInterrompido. O progresso já ficou guardado.')
    print(f'Concluídos nesta execução: {feitos}; falhas/ambíguos: {erros}')
    print('Executa novamente para retomar. Reinicia o Flask e atualiza a página.')


if __name__ == '__main__':
    executar()
