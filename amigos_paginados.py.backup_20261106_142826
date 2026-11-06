"""Consulta paginada/cacheada da lista PSN. Não armazena tokens nem credenciais."""
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import RLock
from psnawp_api.utils import BASE_PATH, API_PATH

CACHE = Path(__file__).resolve().parent / 'database' / 'amigos_cache.json'
LOCK = RLock()
PAGE_SIZE = 12


def _read():
    try:
        with LOCK:
            x = json.loads(CACHE.read_text(encoding='utf-8'))
        if isinstance(x, dict):
            return x
    except (OSError, ValueError):
        pass
    return {'accounts': [], 'users': {}, 'updated': 0}


def _write(cache):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK:
        temp = CACHE.with_suffix('.tmp')
        temp.write_text(json.dumps(cache, ensure_ascii=False), encoding='utf-8')
        os.replace(temp, CACHE)


def _avatar(profile):
    """Formatos suportados pela PSN: avatarUrls/avatarUrl e avatars/url."""
    if not isinstance(profile, dict):
        return None
    p = profile.get('profile', profile)
    for key in ('avatars', 'avatarUrls'):
        imgs = p.get(key) or []
        if isinstance(imgs, dict):
            imgs = list(imgs.values())
        if not isinstance(imgs, list):
            continue
        imgs = sorted(imgs, key=lambda x: {'xl': 0, 'l': 1, 'm': 2, 's': 3}.get(str(x.get('size', '')) if isinstance(x, dict) else '', 4))
        for entry in imgs:
            url = (entry.get('url') or entry.get('avatarUrl') or entry.get('avatar_url')) if isinstance(entry, dict) else (entry if isinstance(entry, str) else None)
            if isinstance(url, str) and url.startswith('https://'):
                return url
    for key in ('avatarUrl', 'avatar_url'):
        url = p.get(key)
        if isinstance(url, str) and url.startswith('https://'):
            return url
    return None


def _account_ids(psn):
    url = BASE_PATH['profile_uri'] + API_PATH['friends_list'].format(account_id='me')
    result = psn.authenticator.get(url=url, params={'limit': 200}).json()
    return [str(x) for x in result.get('friends', []) if x]


def _load_profile(account_id, token):
    # Cada worker usa a sua própria instância de autenticação.
    from psnawp_api import PSNAWP
    psn = PSNAWP(token)
    url = BASE_PATH['profile_uri'] + API_PATH['profiles'].format(account_id=account_id)
    p = psn.authenticator.get(url=url).json()
    return {'id': p.get('onlineId') or p.get('currentOnlineId'),
            'avatar': _avatar(p), 'plus': bool(p.get('isPlus') or p.get('plus')),
            'obtido': time.time()}


def obter_pagina(psn, pagina=1, atualizar=False):
    cache = _read()
    aviso = None
    agora = time.time()
    # Evita atualizar toda a lista em cada abertura: só 1 chamada a cada 30 min.
    if atualizar or not cache.get('accounts') or agora - cache.get('updated', 0) > 1800:
        try:
            cache['accounts'] = _account_ids(psn)
            cache['updated'] = agora
            _write(cache)
        except Exception as exc:
            if not cache.get('accounts'):
                raise
            aviso = 'Não foi possível atualizar a PSN; a mostrar amigos em cache.'
    accounts = cache.get('accounts', [])
    total = len(accounts)
    pagina = max(1, min(pagina, max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)))
    selected = accounts[(pagina - 1) * PAGE_SIZE:pagina * PAGE_SIZE]
    users = cache.setdefault('users', {})
    faltam = [a for a in selected if a not in users or not users[a].get('id') or (atualizar and agora - users[a].get('obtido', 0) > 30)]
    if faltam:
        token = os.environ.get('PSN_NPSSO', '').strip()
        # Poucos pedidos em simultâneo para evitar bloquear ou saturar a PSN.
        with ThreadPoolExecutor(max_workers=3) as pool:
            tasks = {pool.submit(_load_profile, a, token): a for a in faltam}
            for future in as_completed(tasks):
                account_id = tasks[future]
                try:
                    result = future.result()
                    if result['id']:
                        users[account_id] = result
                        _write(cache)
                except Exception:
                    aviso = 'Alguns perfis não responderam; podes tentar novamente mais tarde.'
    amigos = [dict(users[a]) for a in selected if a in users and users[a].get('id')]
    return amigos, pagina, total, aviso
