# Recon Core

Automação modular de recon com bot Telegram + worker em fila SQLite.

## Instalação rápida

1. Crie e ative um ambiente virtual Python:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
2. Instale as dependências do projeto:
   - `pip install -r requirements.txt`
3. Configure o token do Telegram (uma das opções):
   - variável de ambiente: `export TELEGRAM_BOT_TOKEN="<seu_token>"`
   - ou arquivo `config/app.yml` em `telegram.bot_token`
4. Inicie bot: `python3 -m bot.controller`
5. Em outro terminal inicie worker: `python3 -m runner.worker`
6. No Telegram: `/site example.com balanced`

> Se aparecer `ModuleNotFoundError: No module named 'telegram'`, normalmente o problema é dependência não instalada ou venv não ativado no terminal atual.
>
> Se aparecer erro de permissão em `/opt/recon-core`, ajuste `config/app.yml` para usar caminhos relativos (padrão deste repositório) ou exporte `RECON_ROOT` para uma pasta com permissão de escrita.
>
> Evite `sudo python3 -m bot.controller` dentro do venv: o `sudo` costuma usar outro Python sem os pacotes do `.venv`.

## Estrutura

- `bot/`: comandos Telegram e notificações
- `runner/`: loop worker/fila
- `modules/`: scripts de coleta e relatório
- `storage/recon/`: saídas por job/timestamp
- `storage/history.sqlite`: histórico de jobs

## Banco SQLite

Tabela `jobs` com status: `pending`, `running`, `completed`, `failed`.
