"""Pesquisa/ordenação de amigos PSN — sem ligações à PlayStation Network."""
import json
import sqlite3
import time
from pathlib import Path
from types import SimpleNamespace
import pytest

import amigos
import amigos_paginados as pag
from app import app


@pytest.fixture
def setup_isolado(monkeypatch, tmp_path):
    monkeypatch.setattr(pag, 'CACHE', tmp_path / 'amigos_cache.json')
    monkeypatch.setattr(amigos, 'DB', tmp_path / 'amigos.db')
    app.config['TESTING'] = True
    return app.test_client()


def test_ordem_alfabetica_entre_todas_as_paginas(setup_isolado, monkeypatch):
    # API devolve os account IDs numa ordem não-alfabética.
    ids = [str(i) for i in range(27)]
    nomes = [f'Utilizador_{n:02d}' for n in reversed(range(27))]
    monkeypatch.setenv('PSN_NPSSO', 'token_fake')
    monkeypatch.setattr(amigos, 'cliente', lambda: object())
    monkeypatch.setattr(pag, '_account_ids', lambda psn: ids)
    chamadas = []
    def perfil(account_id, token):
        chamadas.append(account_id)
        return {'id': nomes[int(account_id)], 'avatar': None, 'nome_real': '', 'plus': False,
                'obtido': time.time(), 'avatar_verificado': time.time()}
    monkeypatch.setattr(pag, '_load_profile', perfil)
    client = setup_isolado
    html = client.get('/amigos').get_data(as_text=True)
    assert html.index('Utilizador_00') < html.index('Utilizador_01')
    assert 'Utilizador_12' not in html
    html2 = client.get('/amigos?pagina=2').get_data(as_text=True)
    assert 'Utilizador_12' in html2
    assert 'Utilizador_00' not in html2
    assert sorted(chamadas) == sorted(ids)
    assert len(chamadas) == 27  # o índice é reutilizado no acesso seguinte
    assert 'token_fake' not in pag.CACHE.read_text(encoding='utf-8')


def test_pesquisa_so_amigos_psn_e_nao_global(setup_isolado, monkeypatch):
    monkeypatch.setenv('PSN_NPSSO', 'falso')
    # A chamada de cliente não permite user(online_id=...) de propósito.
    monkeypatch.setattr(amigos, 'cliente', lambda: SimpleNamespace(me=lambda:None))
    monkeypatch.setattr(pag, '_account_ids', lambda psn: ['1','2','3'])
    perfis = {
        '1': ('JoelBrito_92','Joel Brito'), '2': ('JoanaPSN', 'Joana'),
        '3': ('Alpha', 'Alfa Teste')
    }
    def perfil(account_id, token):
        online_id, nome = perfis[account_id]
        return {'id': online_id, 'nome_real': nome, 'avatar': None, 'plus':False,
                'obtido':time.time(), 'avatar_verificado':time.time()}
    monkeypatch.setattr(pag, '_load_profile', perfil)
    # Guardado localmente não é necessariamente amigo PSN, não deve ser pesquisável.
    with amigos.conexao() as c:
        c.execute("INSERT INTO amigos_guardados VALUES ('JoelQualquer','', '2026-11-01')")
    client=setup_isolado
    html = client.get('/amigos?q=joel').get_data(as_text=True)
    assert 'JoelBrito_92' in html
    assert 'JoelQualquer' not in html
    assert 'JoanaPSN' not in html
    assert '1 encontrados de 3 amigos' in html
    html = client.get('/amigos?q=bríto').get_data(as_text=True)
    assert 'JoelBrito_92' in html  # ignora acentos
    html = client.get('/amigos?q=desconhecido').get_data(as_text=True)
    assert 'Nenhum dos teus amigos encontrados' in html
    assert client.get('/amigos/pesquisar?id=joel').headers['Location'].endswith('/amigos?q=joel')


def test_sem_sessao_usa_apenas_amigos_guardados_em_cache(setup_isolado, monkeypatch):
    dados = {'accounts': ['1', '2'], 'users': {'1':{'id':'JoelBrito','avatar':None,'nome_real':'Joel Brito'}},
             'updated': time.time(), 'failed': {}}
    pag.CACHE.write_text(json.dumps(dados), encoding='utf-8')
    monkeypatch.delenv('PSN_NPSSO', raising=False)
    response = setup_isolado.get('/amigos?q=joel')
    html=response.get_data(as_text=True)
    assert response.status_code==200
    assert 'JoelBrito' in html
    assert '1 perfis ainda' in html
    assert 'Sem sessão PSN' in html


def test_pesquisa_longas_rejeitadas(setup_isolado):
    assert setup_isolado.get('/amigos?q='+'x'*81).status_code == 400
    assert setup_isolado.get('/amigos/pesquisar?q='+'x'*81).status_code == 400
