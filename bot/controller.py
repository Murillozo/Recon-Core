"""Telegram bot entrypoint for dispatching recon jobs."""
from __future__ import annotations

import fcntl
import html
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from urllib.parse import quote

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.commands import (
    allowed_profiles,
    cancel_job,
    delete_job,
    enqueue_job,
    environment_paths,
    get_job_for_chat,
    init_db,
    is_in_scope,
    list_completed_jobs_for_chat,
    list_recent_jobs_for_chat,
    load_scope,
    validate_domain,
)
from recon_settings import load_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("recon-bot")


HELP_TEXT = (
    "*Comandos disponíveis*\n"
    "- `/site <dominio> <perfil>` cria um job\n"
    "- `/cancel <job_id>` cancela job pendente\n"
    "- `/excluir <job_id>` exclui job (em andamento ou concluído) e apaga a pasta\n"
    "- `/status <job_id>` mostra status detalhado de um job\n"
    "- `/jobs` lista seus últimos jobs\n"
    "- `/feitos` lista jobs concluídos com caminho da pasta\n"
    "- `/help` mostra esta ajuda\n\n"
    "Perfis: passive, balanced, deep"
)


def required_bot_token() -> str:
    """Return configured Telegram token or raise a clear startup error."""
    token = load_settings().telegram_bot_token
    if not token:
        raise RuntimeError(
            "Set TELEGRAM_BOT_TOKEN or telegram.bot_token in config/app.yml before running bot"
        )
    return token


@contextmanager
def single_instance_lock(lock_file: Path) -> Iterator[None]:
    """Prevent multiple local polling instances with the same bot token."""
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    fh = lock_file.open("w", encoding="utf-8")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        fh.close()
        raise RuntimeError(
            f"Another bot instance is already running (lock: {lock_file}). "
            "Stop the old process before starting a new one."
        ) from exc

    fh.write(str(os.getpid()))
    fh.flush()
    try:
        yield
    finally:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        fh.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


async def site(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Formato inválido. Exemplo: /site example.com balanced")
        return

    domain = args[0].strip().lower()
    profile = args[1].strip().lower()
    paths = environment_paths()

    if not validate_domain(domain):
        await update.message.reply_text("Domínio inválido.")
        return

    scope = load_scope(paths["scope"])
    if not is_in_scope(domain, scope):
        await update.message.reply_text("Domínio fora do escopo permitido.")
        return

    profiles = allowed_profiles(paths["config"])
    if profile not in profiles:
        await update.message.reply_text(
            f"Perfil inválido. Escolha um: {', '.join(sorted(profiles))}"
        )
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    requested_by = user.username or user.full_name
    job_id = enqueue_job(paths["db"], domain, profile, chat_id, requested_by)

    await update.message.reply_text(
        f"Job criado com sucesso!\nID: {job_id}\nDomínio: {domain}\nPerfil: {profile}"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text("Formato inválido. Exemplo: /cancel 12")
        return

    job_id = int(args[0])
    chat_id = update.effective_chat.id
    paths = environment_paths()

    canceled, reason = cancel_job(paths["db"], job_id, chat_id)
    if canceled:
        await update.message.reply_text(f"Job {job_id} cancelado com sucesso.")
        return

    if reason == "not_found":
        await update.message.reply_text(f"Job {job_id} não encontrado.")
    elif reason == "forbidden":
        await update.message.reply_text("Você não pode cancelar um job criado por outro chat.")
    else:
        await update.message.reply_text(
            f"Não foi possível cancelar o job {job_id}. Status atual: {reason}"
        )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text("Formato inválido. Exemplo: /status 12")
        return

    job_id = int(args[0])
    chat_id = update.effective_chat.id
    paths = environment_paths()

    ok, data = get_job_for_chat(paths["db"], job_id, chat_id)
    if not ok:
        if data == "not_found":
            await update.message.reply_text(f"Job {job_id} não encontrado.")
        else:
            await update.message.reply_text("Você não pode consultar job de outro chat.")
        return

    await update.message.reply_text(
        "\n".join(
            [
                f"Job: {data['id']}",
                f"Domínio: {data['domain']}",
                f"Perfil: {data['profile']}",
                f"Status: {data['status']}",
                f"Criado em: {data['created_at']}",
                f"Iniciado em: {data['started_at']}",
                f"Finalizado em: {data['finished_at']}",
            ]
        )
    )


async def excluir(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text("Formato inválido. Exemplo: /excluir 12")
        return

    job_id = int(args[0])
    chat_id = update.effective_chat.id
    paths = environment_paths()

    deleted, reason, removed_paths = delete_job(paths["db"], paths["root"], job_id, chat_id)
    if deleted:
        lines = [f"Job {job_id} excluído com sucesso."]
        if removed_paths:
            lines.append("Pastas removidas:")
            lines.extend(f"- {path}" for path in removed_paths)
        else:
            lines.append("Nenhuma pasta de artefatos encontrada para remover.")
        await update.message.reply_text("\n".join(lines))
        return

    if reason == "not_found":
        await update.message.reply_text(f"Job {job_id} não encontrado.")
    else:
        await update.message.reply_text("Você não pode excluir um job criado por outro chat.")


async def jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    paths = environment_paths()
    rows = list_recent_jobs_for_chat(paths["db"], chat_id, limit=5)

    if not rows:
        await update.message.reply_text("Você ainda não possui jobs.")
        return

    lines = ["Últimos jobs:"]
    for row in rows:
        lines.append(
            f"- ID {row['id']} | {row['domain']} | {row['profile']} | {row['status']} | {row['created_at']}"
        )
    await update.message.reply_text("\n".join(lines))


async def feitos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    paths = environment_paths()
    rows = list_completed_jobs_for_chat(paths["db"], chat_id, limit=10)

    if not rows:
        await update.message.reply_text("Você ainda não possui jobs concluídos.")
        return

    lines = ["Jobs concluídos:"]
    for row in rows:
        run_dir = row["run_dir"]
        escaped_run_dir = html.escape(run_dir)

        lines.append(
            f"- ID {row['id']} | {row['domain']} | {row['profile']} | finalizado: {row['finished_at']}"
        )
        if run_dir == "-":
            lines.append("  pasta: -")
        else:
            lines.append(f"  caminho: <code>{escaped_run_dir}</code>")
            lines.append("  dica: segure/tap no caminho para copiar")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


def main() -> None:
    token = required_bot_token()

    paths = environment_paths()
    init_db(paths["db"])
    logs_dir = Path(paths["root"] / "logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("site", site))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("excluir", excluir))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("jobs", jobs))
    app.add_handler(CommandHandler("feitos", feitos))

    lock_file = logs_dir / "bot.controller.lock"
    with single_instance_lock(lock_file):
        logger.info("Starting Recon bot")
        app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
