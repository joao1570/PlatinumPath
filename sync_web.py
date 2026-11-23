"""Controlled local synchronization; one job at a time, no credentials in logs."""
import os
import subprocess
import sys
from pathlib import Path
from threading import Lock, Thread

BASE = Path(__file__).resolve().parent
_lock = Lock()
_state = {'estado': 'inativo', 'codigo': None, 'linhas': []}


def estado():
    with _lock:
        return {**_state, 'linhas': list(_state['linhas'])}


def _executar(token, limite):
    codigo = 1
    try:
        env = dict(os.environ, PSN_NPSSO=token, PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1')
        with subprocess.Popen([sys.executable, str(BASE / 'atualizar_recentes.py'), '--jogos', str(limite)],
                              cwd=BASE, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding='utf-8', errors='replace') as processo:
            for linha in processo.stdout:
                with _lock:
                    _state['linhas'].append(linha.rstrip().replace(token, '[oculto]'))
                    _state['linhas'] = _state['linhas'][-150:]
            codigo = processo.wait()
    except Exception as exc:
        with _lock:
            _state['linhas'].append(f'Não foi possível executar a sincronização: {type(exc).__name__}.')
    finally:
        with _lock:
            _state.update(estado='concluido' if codigo == 0 else 'erro', codigo=codigo)


def iniciar(token, limite=30):
    if not token or limite not in (0, 30):
        raise ValueError('Sessão PSN ou limite inválido.')
    with _lock:
        if _state['estado'] == 'a_sincronizar':
            return False
        _state.update(estado='a_sincronizar', codigo=None, linhas=[])
    try:
        Thread(target=_executar, args=(token, limite), daemon=True).start()
    except Exception:
        with _lock:
            _state.update(estado='erro', codigo=1)
        raise
    return True
