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
7. Para cancelar job pendente: `/cancel <job_id>`
8. Para ver status de um job: `/status <job_id>`
9. Para listar jobs recentes: `/jobs`
10. Para ajuda: `/help`

> Se aparecer `ModuleNotFoundError: No module named 'telegram'`, normalmente o problema é dependência não instalada ou venv não ativado no terminal atual.
>
> Se aparecer erro de permissão em `/opt/recon-core`, ajuste `config/app.yml` para usar caminhos relativos (padrão deste repositório) ou exporte `RECON_ROOT` para uma pasta com permissão de escrita.
>
> Evite `sudo python3 -m bot.controller` dentro do venv: o `sudo` costuma usar outro Python sem os pacotes do `.venv`.
>
> Se aparecer `409 Conflict: terminated by other getUpdates request`, significa que **já existe outra instância** usando esse mesmo token (outro terminal, tmux/screen, systemd ou outro servidor).
>
> Diagnóstico rápido (Kali/Linux):
> - `ps -ef | rg 'python3 -m bot.controller'`
> - `pkill -f 'python3 -m bot.controller'` (se quiser encerrar instâncias antigas)
>
> Depois suba **apenas 1 instância** do bot por token.

## Estrutura

- `bot/`: comandos Telegram e notificações
- `runner/`: loop worker/fila
- `modules/`: scripts de coleta e relatório
- `storage/recon/`: saídas por job/timestamp
- `storage/history.sqlite`: histórico de jobs

## Banco SQLite

Tabela `jobs` com status: `pending`, `running`, `completed`, `failed`, `canceled`.


## Rodando como serviço (systemd)

Para produção, rode **2 serviços**: bot e worker.

1. Crie arquivo de ambiente (exemplo `/etc/recon-core/recon-core.env`):

```bash
TELEGRAM_BOT_TOKEN=SEU_TOKEN_AQUI
RECON_ROOT=/opt/recon-core
```

2. Crie o serviço do bot em `/etc/systemd/system/recon-bot.service`:

```ini
[Unit]
Description=Recon Core Telegram Bot
After=network.target

[Service]
Type=simple
User=recon
Group=recon
WorkingDirectory=/opt/recon-core
EnvironmentFile=/etc/recon-core/recon-core.env
ExecStart=/opt/recon-core/.venv/bin/python -m bot.controller
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

3. Crie o serviço do worker em `/etc/systemd/system/recon-worker.service`:

```ini
[Unit]
Description=Recon Core Worker
After=network.target

[Service]
Type=simple
User=recon
Group=recon
WorkingDirectory=/opt/recon-core
EnvironmentFile=/etc/recon-core/recon-core.env
ExecStart=/opt/recon-core/.venv/bin/python -m runner.worker
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

4. Habilite e inicie:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now recon-bot recon-worker
```

5. Logs e status:

```bash
sudo systemctl status recon-bot recon-worker
sudo journalctl -u recon-bot -u recon-worker -f
```

> Importante: mantenha **apenas uma instância do bot** por token para evitar conflito `409`.
