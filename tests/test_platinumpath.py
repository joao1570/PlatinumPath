"""Testes locais sem fazer pedidos reais à PlayStation Network."""
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
# Permite usar o ambiente instalado na pasta venv ao testar num Python externo.
if not __import__('importlib').util.find_spec('flask') and (ROOT / 'venv/Lib/site-packages').exists():
    sys.path.insert(0, str(ROOT / 'venv/Lib/site-packages'))
sys.path.insert(0, str(ROOT))

import amigos
import amigos_paginados
import sincronizar_trofeus as sync
from app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    import shutil, jogos
    db = tmp_path / "platinumpath.db"
    if (ROOT / "Database/platinumpath.db").exists():
        shutil.copy2(ROOT / "Database/platinumpath.db", db)
    else:
        from init_db import criar_base_dados
        criar_base_dados(db)
        with sqlite3.connect(db) as c:
            c.execute("INSERT INTO jogos (titulo, plataforma_id) VALUES ('Teste',1)")
    monkeypatch.setattr(jogos, "DATABASE_PATH", db)
    monkeypatch.setattr(amigos, "DB", db)
    monkeypatch.setattr(amigos_paginados, "CACHE", tmp_path / "cache.json")
    monkeypatch.delenv('PSN_NPSSO', raising=False)
    app.config.update(TESTING=True)
    return app.test_client()


def test_paginas_locais_carregam_sem_psn(client):
    assert client.get('/').status_code == 200
    assert client.get('/amigos').status_code == 200
    assert client.get('/amigos?pagina=2').status_code == 200
    assert client.get('/jogo/1').status_code == 200
    assert client.get('/jogo/99999999').status_code == 404
    assert client.get('/static/icons/bronze_trophy.png').status_code == 200
    assert client.get('/amigos/pesquisar?id=a').status_code == 302
    assert client.get('/amigos/pesquisar?id=').status_code == 400


def test_icons_sao_png_reais():
    from PIL import Image
    for tipo in ('bronze', 'silver', 'gold', 'platinum'):
        with Image.open(ROOT / 'static' / 'icons' / f'{tipo}_trophy.png') as image:
            assert image.format == 'PNG'


def test_cache_amigos_paginacao_e_falhas(tmp_path, monkeypatch):
    monkeypatch.setattr(amigos_paginados, 'CACHE', tmp_path / 'amigos_cache.json')
    monkeypatch.setenv('PSN_NPSSO', 'token_de_teste_nao_real')
    monkeypatch.setattr(amigos_paginados, '_account_ids', lambda psn: [str(i) for i in range(26)])
    monkeypatch.setattr(amigos_paginados, '_load_profile', lambda i, token: {
        'id': f'Amigo_{i}', 'avatar': None, 'plus': False,
        'obtido': __import__('time').time(), 'avatar_verificado': __import__('time').time()
    })
    primeiro, pagina, total, aviso = amigos_paginados.obter_pagina(object(), 1)
    assert total == 26 and pagina == 1 and len(primeiro) == 12
    segundo, pagina, total, _ = amigos_paginados.obter_pagina(object(), 2)
    assert pagina == 2 and len(segundo) == 12 and segundo[0]['id'] == 'Amigo_12'
    offline, pagina, total, aviso = amigos_paginados.obter_pagina(None, 1)
    assert offline == primeiro and 'cache' in aviso
    assert 'token_de_teste_nao_real' not in amigos_paginados.CACHE.read_text(encoding='utf-8')
    assert amigos_paginados.obter_pagina(None, 55)[1] == 3


def test_amigos_sem_token_e_perfil_com_api_falsa(client, monkeypatch, tmp_path):
    monkeypatch.setattr(amigos, 'DB', tmp_path / 'platinumpath.db')
    class User:
        def profile(self):
            return {'onlineId': 'Teste_123', 'avatars': [{'size': 'xl', 'url': 'https://example.org/avatar.png'}]}
        def trophy_summary(self):
            ganhos = SimpleNamespace(platinum=1, gold=2, silver=3, bronze=4)
            return SimpleNamespace(trophy_level=100, earned_trophies=ganhos)
        def trophy_titles(self, limit=None, offset=0, page_size=50):
            def title(i):
                return SimpleNamespace(title_name=f'Jogo {i}', title_icon_url=None,
                                       np_communication_id=f'NPWR{i:05}_00', title_platform=['PS4'],
                                       progress=15, earned_trophies=None, defined_trophies=None)
            return iter([title(i) for i in range(offset, min(offset+(limit if limit is not None else 90), 90))])
        def trophies(self, *args, **kwargs):
            assert kwargs['trophy_group_id'] == 'all'
            assert kwargs['include_progress'] and kwargs['limit'] is None
            return [SimpleNamespace(trophy_name='Teste troféu', trophy_detail='Descrição',
                                    trophy_type=SimpleNamespace(value='gold'), trophy_icon_url=None, earned=True)]
    monkeypatch.setattr(amigos, 'cliente', lambda: SimpleNamespace(user=lambda **kwargs: User()))
    response = client.get('/amigos/Teste_123')
    assert response.status_code == 200 and b'Jogo 0' in response.data
    assert b'Jogo 40' not in response.data
    assert b'Mais jogos' in response.data
    response2 = client.get('/amigos/Teste_123?pagina=2')
    assert response2.status_code == 200 and b'Jogo 40' in response2.data
    assert b'Jogo 0<' not in response2.data
    trofeus = client.get('/amigos/Teste_123/trofeus/NPWR00001_00')
    assert trofeus.status_code == 200 and b'Teste trof' in trofeus.data
    assert client.get('/amigos/Teste_123/trofeus/%5Bnao%5D').status_code == 400
    with client.session_transaction() as sess:
        csrf = sess['csrf_token']
    assert client.post('/amigos/guardar/Teste_123', data={'csrf_token':csrf}).status_code == 302
    with sqlite3.connect(amigos.DB) as db:
        assert db.execute('SELECT COUNT(*) FROM amigos_guardados').fetchone()[0] == 1
    assert client.post('/amigos/remover/Teste_123', data={'csrf_token':csrf}).status_code == 302
    with sqlite3.connect(amigos.DB) as db:
        assert db.execute('SELECT COUNT(*) FROM amigos_guardados').fetchone()[0] == 0


def test_sync_guarda_datas_e_atualiza_sem_duplicar():
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.executescript('''CREATE TABLE trofeus (
        id INTEGER PRIMARY KEY, jogo_id INTEGER NOT NULL, nome TEXT NOT NULL,
        tipo TEXT NOT NULL, conquistado INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE jogos (id INTEGER PRIMARY KEY, titulo TEXT, plataforma_id INTEGER);
        INSERT INTO jogos (id, titulo, plataforma_id) VALUES (1,'Jogo teste',1);''')
    sync.preparar_base_dados(db)
    bronze = SimpleNamespace(trophy_id=5, trophy_type='bronze', trophy_group_id='default',
                             trophy_name='Teste Bronze', trophy_icon_url='https://example.org/a.png',
                             trophy_detail='Descrição', earned=True,
                             earned_date_time=datetime(2026, 11, 13, tzinfo=timezone.utc))
    dados = sync.preparar_trofeus([bronze]);assert len(dados) == 1
    assert sync.guardar_trofeus(db, 1, dados) == (1, 0)
    assert db.execute('SELECT data_conquista FROM trofeus').fetchone()[0].startswith('2026-11-13')
    assert sync.guardar_trofeus(db, 1, dados) == (0, 1)
    assert db.execute('SELECT count(*) FROM trofeus').fetchone()[0] == 1
    bronze.earned = False; bronze.earned_date_time = None
    dados = sync.preparar_trofeus([bronze]);sync.guardar_trofeus(db, 1, dados)
    assert db.execute('SELECT data_conquista FROM trofeus').fetchone()[0] is None
    db.close()


def test_retry_so_para_erros_temporarios(monkeypatch):
    class RateLimit(Exception):
        status_code = 429
    contador = {'n': 0}
    def trophies(**kw):
        contador['n'] += 1
        if contador['n'] == 1:
            raise RateLimit('429')
        return [1]
    monkeypatch.setattr(sync.time, 'sleep', lambda x: None)
    assert sync.consultar_trofeus(SimpleNamespace(trophies=trophies), 'NPWR00001_00', object()) == [1]
    assert contador['n'] == 2


def test_retry_psnawp_429_excecao_real():
    from psnawp_api.core.psnawp_exceptions import PSNAWPTooManyRequests, PSNAWPServerError
    assert sync._limite_api(PSNAWPTooManyRequests('Too Many Requests'))
    assert sync._limite_api(PSNAWPServerError('Service temporarily unavailable'))
    assert not sync._limite_api(ValueError('bad account'))


def test_objetivos_criar_concluir_reabrir_eliminar(client):
    import jogos
    assert client.get('/jogo/1').status_code == 200
    with client.session_transaction() as sess:
        token = sess['csrf_token']
    url = '/jogo/1/objetivos'
    assert client.post(url, data={'acao':'adicionar','descricao':'Teste'}).status_code == 403
    def post(**kw):
        return client.post(url, data={'csrf_token':token, **kw})
    assert post(acao='adicionar', descricao='').status_code == 400
    assert post(acao='adicionar', descricao='<script>teste</script>').status_code == 302
    with sqlite3.connect(jogos.DATABASE_PATH) as db:
        ident = db.execute('SELECT MAX(id) FROM objetivos').fetchone()[0]
    resposta = client.get('/jogo/1')
    assert b'&lt;script&gt;teste&lt;/script&gt;' in resposta.data
    for expected in (1,0):
        assert post(acao='alternar', objetivo_id=ident).status_code == 302
        with sqlite3.connect(jogos.DATABASE_PATH) as db:
            assert db.execute('SELECT concluido FROM objetivos WHERE id=?',(ident,)).fetchone()[0] == expected
    assert post(acao='eliminar', objetivo_id=ident).status_code == 302
    assert post(acao='eliminar', objetivo_id=ident).status_code == 404


def test_sync_web_autenticacao_e_estado(client, monkeypatch):
    import sync_web
    client.get('/')
    with client.session_transaction() as sess:
        token = sess['csrf_token']
    assert client.post('/sincronizar', data={'csrf_token':token}).status_code == 400
    monkeypatch.setenv('PSN_NPSSO', 'token-falso')
    mock = Mock(return_value=True)
    monkeypatch.setattr(sync_web,'iniciar',mock)
    assert client.post('/sincronizar', data={'csrf_token':token,'limite':5}).status_code == 400
    assert client.post('/sincronizar', data={'csrf_token':token,'limite':30}).status_code == 202
    mock.assert_called_once_with('token-falso',30)
    mock.return_value=False
    assert client.post('/sincronizar', data={'csrf_token':token}).status_code == 409
    assert client.get('/sincronizar/estado').status_code == 200
    assert 'token-falso' not in client.get('/sincronizar/estado').get_data(as_text=True)


def test_base_nova_e_rotas(tmp_path, monkeypatch):
    import jogos
    from init_db import criar_base_dados
    path=tmp_path/'nova.db'
    criar_base_dados(path)
    criar_base_dados(path)
    monkeypatch.setattr(jogos, 'DATABASE_PATH', path)
    monkeypatch.setattr(amigos, 'DB', path)
    monkeypatch.setattr(amigos_paginados, 'CACHE', tmp_path/'cache.json')
    monkeypatch.delenv('PSN_NPSSO', raising=False)
    c=app.test_client()
    assert c.get('/').status_code == 200
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO jogos(titulo,plataforma_id) VALUES ('Novo',1)")
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert c.get('/jogo/1').status_code==200
    assert c.get('/amigos').status_code==200


def test_sync_recente_idempotente_e_conta(tmp_path, monkeypatch):
    import atualizar_recentes as recentes
    from init_db import criar_base_dados
    path=tmp_path/'nova.db'; criar_base_dados(path)
    monkeypatch.setattr(recentes,'DB',path)
    monkeypatch.setattr(recentes,'BACKUP',tmp_path/'backups')
    t=SimpleNamespace(title_name='Novo',title_icon_url='https://example.org/capa.png')
    trophy=SimpleNamespace(trophy_id=0,trophy_type='gold',trophy_group_id='default',trophy_name='Teste',earned=True, earned_date_time=datetime(2026,11,20,tzinfo=timezone.utc))
    with recentes.conexao() as db:
        assert recentes.atualizar_jogo(db,t,'PS5',[trophy])==1
        assert recentes.atualizar_jogo(db,t,'PS5',[trophy])==0
        trophy.earned=False; trophy.earned_date_time=None
        assert recentes.atualizar_jogo(db,t,'PS5',[trophy])==0
        assert db.execute('SELECT COUNT(*),SUM(conquistado) FROM trofeus').fetchone()[:] == (1,1)
        db.execute("INSERT INTO perfil_psn VALUES(1,'Teste',1,0,0,0,0,0,'agora',NULL)")
        recentes.confirmar_conta(db,'teste')
        with pytest.raises(RuntimeError): recentes.confirmar_conta(db,'outro')
    recentes.criar_backup()
    assert len(list(recentes.BACKUP.glob('*.db')))==1


def test_sync_completo_simulado(tmp_path, monkeypatch):
    import atualizar_recentes as recentes
    from init_db import criar_base_dados
    db_path=tmp_path/'sync.db'; criar_base_dados(db_path)
    monkeypatch.setattr(recentes,'DB',db_path)
    monkeypatch.setattr(recentes,'BACKUP',tmp_path/'backups')
    monkeypatch.setenv('PSN_NPSSO','token-falso')
    class User:
        online_id='ContaTeste'
        def trophy_titles(self, **kw):
            return [SimpleNamespace(title_name='Jogo teste',np_communication_id='NPWR00001_00',title_platform=['PS5'],defined_trophies={'gold':1}, last_updated_date_time=datetime.now(timezone.utc),title_icon_url='https://example.org/capa.png')]
        def trophies(self, **kw):
            return [SimpleNamespace(trophy_id=1,trophy_type='gold', trophy_group_id='default',trophy_name='Teste',earned=True,earned_date_time=datetime.now(timezone.utc))]
        def trophy_summary(self):
            return SimpleNamespace(trophy_level=10,progress=20,earned_trophies=SimpleNamespace(bronze=0,silver=0,gold=1,platinum=0))
    u=User()
    monkeypatch.setattr(recentes,'PSNAWP',lambda token: SimpleNamespace(me=lambda:u))
    assert recentes.sincronizar(30)==0
    assert recentes.sincronizar(30)==0
    with sqlite3.connect(db_path) as db:
        assert db.execute('SELECT COUNT(*) FROM jogos').fetchone()[0]==1
        assert db.execute('SELECT COUNT(*),SUM(conquistado) FROM trofeus').fetchone()==(1,1)
        assert db.execute('SELECT online_id FROM perfil_psn').fetchone()[0]=='ContaTeste'
    u.online_id='OutraConta'
    assert recentes.sincronizar(30)==1
    assert len(list(recentes.BACKUP.glob('*.db')))==2
