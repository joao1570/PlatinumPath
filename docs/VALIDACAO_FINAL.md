# Validação da versão de entrega — 20/11/2026

## Alterações

- Sincronização pelo dashboard: 30 títulos recentes ou todos os títulos, registo de execução e proteção contra iniciar duas operações pela interface. O login continua a ocorrer no terminal.
- Objetivos por jogo: adicionar, concluir, reabrir e eliminar, guardados no SQLite.
- Inicialização de bases novas e migração não destrutiva de bases antigas; índices para consultas por jogo.
- Segurança: servidor local sem debug, CSRF em POST, cabeçalhos de segurança, mensagens de erro da sincronização sem exceções brutas, dados pessoais excluídos do Git por padrão.
- Sincronização: capas atualizadas quando disponíveis, deteção de listas de troféus incompletas, tentativas para falhas temporárias, estado de erro se falhar a atualização do perfil. Mantém os troféus já conquistados e cria backup.
- Normalização do tipo de troféu de amigos; README, comandos de arranque e testes atualizados.
- As capas e os quatro ícones originais foram mantidos. Os instaladores antigos, ambientes virtuais e backups históricos não são necessários para o ZIP completo; não são apagados da pasta original do utilizador.

## Resultados obtidos

| Verificação | Resultado |
| --- | --- |
| pytest (7 testes anteriores e 5 novos) | 12 passaram |
| Rotas Flask, incluindo os 485 detalhes de jogo | 490 respostas HTTP 200 |
| SQLite integrity_check | ok |
| SQLite foreign_key_check | nenhuma violação |
| Jogos | 485 |
| Registos de troféus | 23 910 |
| Registos de troféus conquistados | 7 853 |
| Análise de sintaxe JavaScript do novo ficheiro | sem erros |

O teste integral de sincronização utilizou uma API simulada: verificou criação de jogo, perfil, troféus, backup, segunda sincronização sem duplicações e rejeição de conta diferente. Os testes de objetivos usam uma base temporária. Os testes correram em Linux/Python 3.13 com as dependências Python incluídas no ZIP original, não no Windows/Python 3.14 do utilizador.

## Verificação ainda necessária no computador do utilizador

- A navegação automatizada em Chromium foi bloqueada pelo ambiente de execução (ERR_BLOCKED_BY_ADMINISTRATOR). As rotas foram testadas pelo cliente Flask; a execução visual e as imagens remotas não foram validadas integralmente.
- A sincronização real e a consulta de amigos dependem da autenticação PSN e não foram efetuadas neste ambiente. Usar INICIAR_COM_PSN.bat, clicar Atualizar troféus e confirmar o resultado.
- Não foi efetuado commit ou push remoto. Usar o ZIP de atualização sobre o repositório existente (manter .git, a base de dados e o ambiente virtual), verificar `git status` e testar antes de publicar. Se a cache ou o avatar já estiverem versionados, `.gitignore` não os retira do índice; usar `git rm --cached --ignore-unmatch Database/amigos_cache.json static/avatar_psn.png` para os desversionar sem apagar os ficheiros locais.
- Não executar a sincronização pelo terminal em paralelo com a interface. A aplicação é local; não deve ser publicada como serviço web sem revisão adicional de segurança. A associação de jogos existentes ainda usa título normalizado e plataforma, pelo que títulos homónimos ou variantes podem exigir intervenção manual.
