"""The only coupling to native Telegram and Hermes callback authorization."""

import asyncio
import logging

from .router import ActionContext, ActionResult

log = logging.getLogger(__name__)


def wire(application, adapter, router, profile_home):
    from telegram.ext import CallbackQueryHandler
    from hermes_constants import reset_hermes_home_override, set_hermes_home_override

    # Fail at wiring on incompatible Hermes, before accepting any clicks.
    if not all(callable(getattr(adapter, name, None))
               for name in ("_callback_ctx", "_callback_authorized")):
        raise RuntimeError("Hermes callback authorization API is required")

    async def on_button(update, context):
        query = update.callback_query
        resolved = router.resolve(query.data)
        if resolved is None:
            return
        namespace, handler, action, payload = resolved
        token = set_hermes_home_override(profile_home)
        try:
            cb = adapter._callback_ctx(query)
            if not await adapter._callback_authorized(query, cb, "You are not authorized to use this button."):
                return  # Hermes already answered the denied callback.
            message = query.message
            if message is None or not namespace.allows(cb["chat_id"], cb["thread_id"]):
                await query.answer("This button is outside its configured chat/topic.")
                return
            click = ActionContext(namespace.name, action, payload, str(query.from_user.id),
                                  str(cb["chat_id"]), str(cb["thread_id"]) if cb["thread_id"] is not None else None,
                                  message.message_id)
            await query.answer()  # One early ack; feedback below uses a chat message.
            try:
                result = await asyncio.wait_for(handler(click), timeout=router.timeout)
            except TimeoutError:
                result = ActionResult(False, "Action timed out; its outcome may be unknown. Check state before trying again.")
            except Exception:
                log.warning("Button action raised; outcome may be unknown")
                result = ActionResult(False, "Action could not be completed; its outcome may be unknown. Check state before trying again.")

            ui_failed = False
            if result.edit_text is not None or result.remove_buttons:
                try:
                    if result.edit_text is not None:
                        await query.edit_message_text(
                            text=result.edit_text, parse_mode=None,
                            reply_markup=None if result.remove_buttons else message.reply_markup)
                    else:
                        await query.edit_message_reply_markup(reply_markup=None)
                except Exception:
                    ui_failed = True
                    log.warning("Button message edit failed")
            feedback = result.text
            if ui_failed:
                feedback += " (Button message could not be updated.)"
            try:
                await context.bot.send_message(chat_id=click.chat_id, message_thread_id=click.thread_id,
                                               text=feedback, parse_mode=None)
            except Exception:
                log.warning("Button result feedback could not be delivered")
        finally:
            reset_hermes_home_override(token)

    application.add_handler(CallbackQueryHandler(on_button, pattern=router.pattern))
