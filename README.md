# Recon Core

Automação modular de recon com bot Telegram + worker em fila SQLite.

## Instalação rápida

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuração do Telegram e runtime

O projeto agora usa um arquivo externo de configuração:

- `config/app.yml`

Preencha principalmente:

- `telegram.bot_token`
- `app.recon_root`
- `worker.poll_seconds`
- `paths.*` (sqlite, scope, tools, profiles)

Exemplo mínimo:

```yaml
app:
  recon_root: /opt/recon-core
telegram:
  bot_token: "123456:ABCDEF"
worker:
  poll_seconds: 15
```

Também há fallback por variáveis de ambiente (`TELEGRAM_BOT_TOKEN`, `RECON_ROOT`, `WORKER_POLL_SECONDS`), mas o recomendado é manter em `config/app.yml`.

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
