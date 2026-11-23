"""Amigos PSN com paginação, cache local e pedidos limitados por página.

O cache guarda IDs/avatares públicos, nunca tokens ou passwords.
"""
import json
import os
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import RLock, local

from psnawp_api.utils import BASE_PATH, API_PATH

CACHE = Path(__file__).resolve().parent / 'Database' / 'amigos_cache.json'
LOCK = RLock()
PAGE_SIZE = 12
CACHE_TTL = 30 * 60
PROFILE_RETRY_TTL = 5 * 60
_WORKERS = local()


def _read():
    try:
        with LOCK:
            cache = json.loads(CACHE.read_text(encoding='utf-8'))
        if isinstance(cache, dict) and isinstance(cache.get('accounts'), list) and isinstance(cache.get('users'), dict):
            cache.setdefault('updated', 0)
            cache.setdefault('failed', {})
            return cache
    except (OSError, ValueError, TypeError):
        pass
    return {'accounts': [], 'users': {}, 'updated': 0, 'failed': {}}


def _write(cache):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK:
        temp = CACHE.with_suffix('.tmp')
        temp.write_text(json.dumps(cache, ensure_ascii=False), encoding='utf-8')
        os.replace(temp, CACHE)


def _avatar(profile):
    if not isinstance(profile, dict):
        return None
    p = profile.get('profile') or profile
    if not isinstance(p, dict):
        return None
    for key in ('avatars', 'avatarUrls', 'profilePictureUrls'):
        imgs = p.get(key) or []
        if isinstance(imgs, dict):
            imgs = list(imgs.values())
        if not isinstance(imgs, list):
            continue
        order = {'xl': 0, 'l': 1, 'm': 2, 's': 3}
        imgs = sorted(imgs, key=lambda e: order.get(str(e.get('size', '')).lower(), 4) if isinstance(e, dict) else 5)
        for item in imgs:
            url = item.get('url') or item.get('avatarUrl') or item.get('profilePictureUrl') if isinstance(item, dict) else item
            if isinstance(url, str) and url.startswith(('https://', 'http://')):
                return url
    for key in ('avatarUrl', 'avatar_url', 'profilePictureUrl', 'avatar'):
        url = p.get(key)
        if isinstance(url, str) and url.startswith(('https://', 'http://')):
            return url
    return None


def _account_ids(psn):
    url = BASE_PATH['profile_uri'] + API_PATH['friends_list'].format(account_id='me')
    response = psn.authenticator.get(url=url, params={'limit': 1000}).json()
    accounts = response.get('friends', [])
    if not isinstance(accounts, list):
        raise ValueError('Resposta PSN inesperada para a lista de amigos')
    return list(dict.fromkeys(str(a) for a in accounts if a))


def _load_profile(account_id, token):
    # Uma instância PSNAWP por trabalhador (não uma por amigo).
    from psnawp_api import PSNAWP
    if not getattr(_WORKERS, 'psn', None):
        _WORKERS.psn = PSNAWP(token)
    psn = _WORKERS.psn
    url = BASE_PATH['profile_uri'] + API_PATH['profiles'].format(account_id=account_id)
    p = psn.authenticator.get(url=url).json()
    if not isinstance(p, dict):
        raise ValueError('Perfil PSN inválido')
    agora = time.time()
    # Os nomes reais só são usados quando a PSN os devolve para este amigo.
    detalhes = p.get('personalDetail') or p.get('personal_details') or {}
    if not isinstance(detalhes, dict):
        detalhes = {}
    nome = ' '.join(str(detalhes.get(campo, '')).strip() for campo in ('firstName', 'lastName')).strip()
    if not nome:
        for campo in ('displayName', 'realName', 'name'):
            valor = p.get(campo)
            if isinstance(valor, str) and valor.strip():
                nome = valor.strip()
                break
    return {'id': p.get('onlineId') or p.get('currentOnlineId') or p.get('online_id'),
            'nome_real': nome[:120], 'avatar': _avatar(p), 'plus': bool(p.get('isPlus') or p.get('plus')),
            'obtido': agora, 'avatar_verificado': agora}


def obter_pagina(psn=None, pagina=1, atualizar=False):
    cache = _read()
    aviso = None
    agora = time.time()
    accounts = cache['accounts']

    if psn is not None and (atualizar or not accounts or agora - cache.get('updated', 0) > CACHE_TTL):
        try:
            novos = _account_ids(psn)
            # Atualizar apenas após a resposta ter sido recebida e validada.
            cache['accounts'] = novos
            cache['updated'] = agora
            accounts = novos
            _write(cache)
        except Exception:
            aviso = 'Não foi possível atualizar a lista PSN; a mostrar os dados guardados.'
    elif psn is None:
        aviso = ('Sem ligação à PSN: a mostrar amigos guardados em cache. '
                 'Inicia com python iniciar_com_psn.py para atualizar.')

    accounts = cache['accounts']
    total = len(accounts)
    try:
        pagina = int(pagina)
    except (ValueError, TypeError):
        pagina = 1
    paginas = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    pagina = max(1, min(pagina, paginas))
    selected = accounts[(pagina - 1) * PAGE_SIZE:pagina * PAGE_SIZE]
    users = cache.setdefault('users', {})
    failed = cache.setdefault('failed', {})

    if psn is not None and os.environ.get('PSN_NPSSO', '').strip():
        faltam = [a for a in selected if
                  (a not in users or not users[a].get('id') or
                   (not users[a].get('avatar') and agora - users[a].get('avatar_verificado', 0) > 3600) or
                   (atualizar and agora - users[a].get('obtido', 0) > 24 * 3600))
                  and agora - failed.get(a, 0) > PROFILE_RETRY_TTL]
        if faltam:
            token = os.environ['PSN_NPSSO'].strip()
            with ThreadPoolExecutor(max_workers=min(3, len(faltam))) as pool:
                tasks = {pool.submit(_load_profile, a, token): a for a in faltam}
                for future in as_completed(tasks):
                    account_id = tasks[future]
                    try:
                        result = future.result()
                        if result.get('id'):
                            users[account_id] = result
                            failed.pop(account_id, None)
                        else:
                            failed[account_id] = agora
                            aviso = 'Alguns perfis não devolveram um ID PSN. Podes tentar mais tarde.'
                    except Exception:
                        failed[account_id] = agora
                        aviso = 'Alguns perfis não responderam à PSN; os restantes continuam visíveis.'
            _write(cache)

    amigos = []
    for account_id in selected:
        dados = users.get(account_id)
        if isinstance(dados, dict) and dados.get('id'):
            amigos.append(dict(dados))
        else:
            amigos.append({'id': None, 'account_id': account_id, 'avatar': None, 'plus': False})
    return amigos, pagina, total, aviso


# A pesquisa e a ordenação alfabética exigem perfis conhecidos de TODAS as páginas,
# não apenas da página 1. Por isso o primeiro acesso autenticado constrói o índice
# local (guardado em Database/amigos_cache.json) sem procurar utilizadores públicos.
def obter_lista_completa(psn=None, atualizar=False):
    cache = _read()
    agora = time.time()
    aviso = None

    if psn is not None and (atualizar or not cache['accounts'] or agora - cache.get('updated', 0) > CACHE_TTL):
        try:
            novos = _account_ids(psn)
            cache['accounts'] = novos
            cache['updated'] = agora
            _write(cache)
        except Exception:
            aviso = 'Não foi possível atualizar a lista da PSN. A usar a lista de amigos em cache.'
    elif psn is None:
        aviso = 'Sem sessão PSN: a usar apenas os amigos previamente carregados em cache.'

    accounts = cache['accounts']
    users = cache.setdefault('users', {})
    failed = cache.setdefault('failed', {})
    if psn is not None and os.environ.get('PSN_NPSSO', '').strip():
        pendentes = [a for a in accounts if (
            not isinstance(users.get(a), dict) or not users[a].get('id') or
            (atualizar and agora - users[a].get('obtido', 0) > 24 * 3600)
        ) and agora - failed.get(a, 0) > PROFILE_RETRY_TTL]
        if pendentes:
            token = os.environ['PSN_NPSSO'].strip()
            # Máximo de 3 pedidos em paralelo para reduzir bloqueios e rate limits.
            with ThreadPoolExecutor(max_workers=min(3, len(pendentes))) as pool:
                tasks = {pool.submit(_load_profile, a, token): a for a in pendentes}
                for future in as_completed(tasks):
                    account_id = tasks[future]
                    try:
                        result = future.result()
                        if result.get('id'):
                            users[account_id] = result
                            failed.pop(account_id, None)
                        else:
                            failed[account_id] = agora
                    except Exception:
                        failed[account_id] = agora
            _write(cache)

    conhecidos, desconhecidos = [], []
    for account_id in accounts:
        perfil = users.get(account_id)
        if isinstance(perfil, dict) and perfil.get('id'):
            conhecidos.append({**perfil, 'account_id': account_id})
        else:
            desconhecidos.append({'id': None, 'account_id': account_id, 'avatar': None, 'plus': False})
    # Ordem alfabética natural, ignorando maiúsculas e acentos, sobre o ID PSN.
    conhecidos.sort(key=lambda u: _chave_alfabetica(u['id']))
    return conhecidos + desconhecidos, len(accounts), aviso, len(desconhecidos)


def _chave_alfabetica(valor):
    normalized = unicodedata.normalize('NFKD', str(valor or '').casefold())
    return ''.join(c for c in normalized if not unicodedata.combining(c))


def filtrar_amigos(amigos, termo):
    """Filtra exclusivamente perfis confirmados da lista de amigos PSN."""
    partes = _chave_alfabetica(termo).split()
    if not partes:
        return amigos
    return [amigo for amigo in amigos if amigo.get('id') and all(
        parte in _chave_alfabetica(' '.join((amigo.get('id') or '', amigo.get('nome_real') or '')))
        for parte in partes
    )]
