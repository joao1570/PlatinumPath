# PlatinumPath

Aplicação web local para organizar a biblioteca PlayStation (PS3, PS4 e PS5), acompanhar os troféus e planear a próxima platina. Projeto desenvolvido em Python, Flask, SQLite, HTML, CSS e JavaScript, com integração não oficial da PSN através de PSNAWP.

## Funcionalidades

- Dashboard com perfil, estatísticas, capas, pesquisa, filtros e ordenação pelas conquistas mais recentes.
- Detalhes de cada jogo: progresso, descrição e imagem dos troféus, pesquisa, filtros e favoritos locais no navegador.
- Objetivos por jogo: adicionar, concluir, reabrir e eliminar tarefas, guardadas no SQLite.
- Amigos PSN ordenados alfabeticamente pelo ID, com paginação, cache, pesquisa **apenas entre amigos** (por ID e, quando disponível, nome), perfis e troféus. No primeiro acesso autenticado, o programa pode demorar a construir o índice de amigos. Os jogadores guardados manualmente aparecem numa secção separada e não são incluídos na pesquisa de amigos PSN. Guardar um jogador é uma ação local, não um pedido de amizade na PSN.
- Sincronização dos 30 títulos mais recentes ou de toda a biblioteca, pelo dashboard ou terminal. Cria um backup antes de gravar e conserva conquistas existentes.

## Instalação simplificada (Windows com Python 3.14)

O PlatinumPath inclui um instalador automático para Windows. **Não precisas de escrever comandos no terminal** para a instalação e o arranque:

1. Instala Python 3.14 para Windows com o Python Launcher (`py`), caso ainda não esteja instalado.
2. Extrai os ficheiros para a pasta `PlatinumPath` e executa **`INSTALAR.cmd`** (ou `INSTALAR.bat`) com duplo clique.
3. O instalador cria a pasta `.venv`, instala `requirements.txt`, faz um **backup da base de dados existente** em `Database/backups/` e executa a inicialização/migração do SQLite.
4. Depois executa **`INICIAR_COM_PSN.cmd`** para introduzir o NPSSO no terminal e abrir a aplicação no navegador automaticamente. Em alternativa, **`INICIAR_OFFLINE.cmd`** inicia o servidor sem autenticação PSN.
5. **`ATUALIZAR_TROFEUS.cmd`** permite atualizar os troféus sem abrir o dashboard. Não o uses ao mesmo tempo que uma sincronização na versão web.

> **Atenção às extensões:** abre o `.cmd`/`.bat`, não o ficheiro `.py` com nome semelhante, porque este pode abrir apenas o código no editor. No Explorador do Windows ativa **Ver > Mostrar > Extensões de nomes de ficheiro**.

Mantém a janela de comandos aberta enquanto estiveres a utilizar o programa. O endereço é <http://127.0.0.1:5000/>. Para parar, fecha a janela ou carrega em `Ctrl+C`. O NPSSO é pedido com entrada oculta e não é gravado em ficheiro.

### Instalação alternativa pelo terminal

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe preparar_instalacao.py
.\.venv\Scripts\python.exe abrir_platinumpath.py --psn
```

Para abrir offline, substitui `--psn` por `--offline`. A sincronização pela interface permite atualizar os 30 jogos mais recentes ou toda a biblioteca. Pode demorar, e a API não oficial PSNAWP pode impor limitações ou deixar de funcionar.

### Dados e segurança

- O ficheiro real é `Database/platinumpath.db`. Nunca o substituas por uma versão mais antiga sem fazer backup.
- Os backups de sincronização ficam em `Database/backups/`. Para recuperar um backup, fecha a aplicação, guarda uma cópia da base corrente e copia o backup escolhido para `Database/platinumpath.db`.
- O token NPSSO nunca deve ser publicado no GitHub ou partilhado. A sessão é passada por ambiente ao processo local, não gravada num ficheiro pelo PlatinumPath.
- A aplicação está configurada para execução local, com debug desativado, proteção CSRF nas operações POST e cabeçalhos de segurança. Não foi concebida para exposição pública à Internet.
- O acesso à PSN não é necessário para consultar a biblioteca já guardada. Os favoritos de troféus permanecem no armazenamento local do navegador; os objetivos ficam na base de dados.
- A sincronização rápida verifica a identidade da conta existente e não apaga troféus conquistados. Os scripts anteriores são ferramentas auxiliares; usa preferencialmente `atualizar_recentes.py`.

## Testes

```powershell
py -3.14 -m pip install -r requirements-dev.txt
py -3.14 -m pytest -q tests
```

Os testes usam cópias temporárias da base de dados e respostas PSN simuladas. Não necessitam de NPSSO nem alteram a biblioteca real. Um teste ao vivo da integração PSN deve ser feito localmente com a conta do utilizador.

## Estrutura

| Ficheiro/pasta | Função |
| --- | --- |
| `app.py` | Dashboard, detalhe, objetivos, segurança e rotas de sincronização |
| `sync_web.py` | Execução controlada da sincronização com registo de estado |
| `atualizar_recentes.py` | Importação/atualização de títulos, troféus e perfil, com backup |
| `amigos.py`, `amigos_paginados.py` | Perfis, amigos e cache paginada |
| `jogos.py` | Acesso SQLite e gestão de jogos por terminal |
| `init_db.py`, `Database/schema.sql` | Criação e migração da base de dados |
| `templates/`, `static/` | Interface e recursos gráficos |
| `tests/` | Testes automatizados |
| `docs/` | Documentação do projeto |

## Repositório

https://github.com/joao1570/PlatinumPath

Versão local de entrega: 20-11-2026. Ver `docs/VALIDACAO_FINAL.md` para o âmbito da validação e limitações.
