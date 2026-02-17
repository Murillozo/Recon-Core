"""Telegram bot entrypoint for dispatching recon jobs."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.commands import (
    allowed_profiles,
    enqueue_job,
    environment_paths,
    init_db,
    is_in_scope,
    load_scope,
    validate_domain,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("recon-bot")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Use: /site <dominio> <perfil>\nPerfis disponíveis: passive, balanced, deep"
    )


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


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN before running bot")

    paths = environment_paths()
    init_db(paths["db"])
    Path(paths["root"] / "logs").mkdir(parents=True, exist_ok=True)

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("site", site))

    logger.info("Starting Recon bot")
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
