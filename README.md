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


## Estrutura

- `bot/`: comandos Telegram e notificações
- `runner/`: loop worker/fila
- `modules/`: scripts de coleta e relatório
- `storage/recon/`: saídas por job/timestamp
- `storage/history.sqlite`: histórico de jobs

## Banco SQLite

Tabela `jobs` com status: `pending`, `running`, `completed`, `failed`, `canceled`.

## Instalação como serviço systemd

O repositório inclui um instalador para publicar o bot e o worker como serviços Linux. Execute a partir da raiz do projeto:

```bash
sudo TELEGRAM_BOT_TOKEN="<seu_token>" ./scripts/install-systemd.sh
```

Por padrão, o script:

- copia o projeto para `/opt/recon-core`;
- cria/usa o usuário de serviço `recon`;
- cria a venv em `/opt/recon-core/.venv`;
- instala `requirements.txt`;
- cria `/opt/recon-core/.env` com `RECON_ROOT` e, se informado, `TELEGRAM_BOT_TOKEN`;
- cria os serviços `recon-bot.service` e `recon-worker.service` em `/etc/systemd/system/`;
- habilita e inicia os dois serviços.

Opções úteis:

```bash
sudo ./scripts/install-systemd.sh --install-dir /srv/recon-core --user recon
sudo ./scripts/install-systemd.sh --no-start
sudo ./scripts/install-systemd.sh --skip-copy
```

Depois da instalação, verifique:

```bash
sudo systemctl status recon-bot.service recon-worker.service
sudo journalctl -u recon-bot.service -u recon-worker.service -f
```
