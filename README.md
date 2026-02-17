# Recon Core

Automação modular de recon com bot Telegram + worker em fila SQLite.

## Instalação rápida

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="<token>"
export RECON_ROOT="$(pwd)"
```

## Uso

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
