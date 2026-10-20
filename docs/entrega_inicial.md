# PlatinumPath

## 1. Identificação do sistema

Nome: PlatinumPath

Opção escolhida: B — Projeto Livre

Descrição: Aplicação para gerir jogos PlayStation e acompanhar o progresso dos troféus e platinas.

## 2. Objetivo do sistema

O PlatinumPath tem como objetivo ajudar jogadores PlayStation a organizar os seus videojogos e acompanhar a conquista de troféus.

A aplicação vai permitir registar jogos, marcar os troféus conquistados e criar objetivos para chegar à platina.

Também vai apresentar estatísticas para o utilizador acompanhar o seu progresso.

## 3. Contexto do projeto

A ideia surgiu do meu interesse pelos videojogos e pela conquista de troféus PlayStation.

Por vezes é difícil acompanhar os troféus que faltam e organizar as tarefas necessárias para conseguir uma platina.

O PlatinumPath pretende facilitar essa organização, permitindo acompanhar o progresso de cada jogo num só lugar.

## 4. Funcionalidades previstas

A primeira versão do PlatinumPath vai permitir:

- Adicionar, consultar, editar e eliminar jogos.
- Associar cada jogo à respetiva plataforma (PS3, PS4 ou PS5).
- Registar os troféus de cada jogo.
- Marcar os troféus já conquistados.
- Criar objetivos para conseguir a platina.
- Consultar o progresso de cada jogo.

## 5. Limites do projeto

Nesta primeira fase, a aplicação vai funcionar localmente no computador.

Os jogos e os troféus serão registados manualmente pelo utilizador.

Ainda não será possível ligar uma conta PlayStation Network, sincronizar troféus automaticamente ou criar contas de utilizador.

Estas funcionalidades poderão ser acrescentadas no futuro, caso a aplicação seja lançada ao público.

## 6. Sistema de gestão de base de dados

O SGBD escolhido para o PlatinumPath é o SQLite.

Escolhi o SQLite porque é simples de utilizar, funciona bem com Python e não precisa de um servidor próprio.

Como a primeira versão da aplicação vai funcionar localmente, considero que é uma boa opção para guardar os jogos, troféus e objetivos dos utilizadores.

## 7. Modelo entidade-relacionamento preliminar

A base de dados terá quatro tabelas principais:

- Plataformas: guarda as plataformas PS3, PS4 e PS5.
- Jogos: guarda o nome, a plataforma e o estado de cada jogo.
- Troféus: guarda os troféus associados a cada jogo e indica se foram conquistados.
- Objetivos: guarda as tarefas que faltam completar para conseguir a platina.

## 8. Diagrama entidade-relacionamento

O diagrama E-R representa as quatro tabelas principais do PlatinumPath e as relações entre elas.

O diagrama foi criado no draw.io e está guardado na pasta docs com o nome modelo_er.drawio.

## 9. Repositório GitHub

O código do PlatinumPath vai ser desenvolvido e guardado no GitHub, permitindo acompanhar as alterações feitas ao longo do projeto.

Link do repositório:
https://github.com/joao1570/PlatinumPath