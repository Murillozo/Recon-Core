# Recon Core

Automação modular de recon com bot Telegram + worker em fila SQLite.

## Instalação rápida

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuração do Telegram e runtime

O projeto usa arquivo externo de configuração:

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

## Perfis adaptados para seu workflow (anotações)

Os perfis agora executam módulos diferentes:

- **passive**: DNS + subdomínios + alive + urls + JS
- **balanced**: passive + fingerprint + portas + sdlookup + candidatos XSS
- **deep**: balanced + nuclei (vulnerabilidades)

Arquivos dos perfis:

- `config/profiles/passive.yml`
- `config/profiles/balanced.yml`
- `config/profiles/deep.yml`

Ferramentas do seu caderno mapeadas em `config/tools.yml`:

- subdomínios: `subfinder`, `findomain`, `assetfinder`, `knock`, `puredns`
- URLs: `gauplus`, `gau`, `waybackurls`, `xurlfind3r`
- alive/status: `httpx`, `hakcheckurl`
- JS: `subjs`
- vuln: `nuclei`
- IP/CVE: `sdlookup`
- XSS pipeline helpers: `gf`, `uro`, `qsreplace`, `airixss`, `freq`

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
