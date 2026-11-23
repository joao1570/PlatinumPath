"""Testes isolados do assistente de instalacao (sem acesso a PSN)."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import abrir_platinumpath
import preparar_instalacao
from init_db import criar_base_dados


class TesteInstalacao(unittest.TestCase):
    def test_backup_antes_da_migracao_nao_apaga_jogos(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / 'Database' / 'platinumpath.db'
            criar_base_dados(db)
            with sqlite3.connect(db) as cx:
                cx.execute("INSERT INTO jogos (titulo,plataforma_id) VALUES ('Teste',1)")
            with patch.object(preparar_instalacao, 'DATABASE_PATH', db), patch.object(
                preparar_instalacao, 'criar_base_dados', lambda: criar_base_dados(db)
            ):
                preparar_instalacao.main()
            with sqlite3.connect(db) as cx:
                self.assertEqual(cx.execute('SELECT COUNT(*) FROM jogos').fetchone()[0], 1)
            backups = list((db.parent / 'backups').glob('platinumpath_pre_instalacao_*.db'))
            self.assertEqual(len(backups), 1)
            with sqlite3.connect(backups[0]) as cx:
                self.assertEqual(cx.execute('SELECT titulo FROM jogos').fetchone()[0], 'Teste')

    def test_launcher_inicia_servidor_e_abre_navegador(self):
        processo = MagicMock()
        processo.poll.return_value = None
        processo.wait.return_value = 0
        resposta = MagicMock()
        resposta.__enter__.return_value = resposta
        resposta.__exit__.return_value = False
        with patch.object(abrir_platinumpath,'servidor_ativo',return_value=False), \
             patch.object(abrir_platinumpath.subprocess,'Popen',return_value=processo) as p, \
             patch.object(abrir_platinumpath.urllib.request,'urlopen',return_value=resposta), \
             patch.object(abrir_platinumpath.webbrowser,'open',return_value=True) as navegador:
            self.assertEqual(abrir_platinumpath.executar('offline'),0)
            self.assertTrue(str(p.call_args.args[0][1]).endswith('app.py'))
            navegador.assert_called_once_with('http://127.0.0.1:5000/')

    def test_launcher_impede_duplo_arranque(self):
        with patch.object(abrir_platinumpath,'servidor_ativo',return_value=True), \
             patch.object(abrir_platinumpath.subprocess,'Popen') as p:
            self.assertEqual(abrir_platinumpath.executar('psn'),1)
            p.assert_not_called()


if __name__ == '__main__':
    unittest.main()
