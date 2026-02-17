# Recon Core

Automação modular de recon com bot Telegram + worker em fila SQLite.

## Instalação rápida



1. Inicie bot: `python3 -m bot.controller`
2. Em outro terminal inicie worker: `python3 -m runner.worker`
3. No Telegram: `/site example.com balanced`

## Estrutura

- `bot/`: comandos Telegram e notificações
- `runner/`: loop worker/fila
- `modules/`: scripts de coleta e relatório
- `storage/recon/`: saídas por job/timestamp
- `storage/history.sqlite`: histórico de jobs

## Banco SQLite

Tabela `jobs` com status: `pending`, `running`, `completed`, `failed`.
