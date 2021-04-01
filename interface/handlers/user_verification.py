from aiogram import types

from interface.init_bot import dp, bot
import interface.buttons as buttons
from api import user

# TODO: delete other messages for other admins
async def verification(admin_id: int, user_id: int, username: str):
    keyboard_interface = buttons.create_inline_markup([{'text': '\U00002705', 'callback': f'verification success {user_id}'},{'text': '\U0000274C', 'callback': f'verification failed {user_id}'}])

    await bot.send_message(chat_id=admin_id, text=f"Подтвердите пользователя {f'@{username}' if username != 'None' else f'[{user_id}](tg://user?id={user_id})'}", reply_markup=keyboard_interface, parse_mode="Markdown")


@dp.callback_query_handler(lambda call: call.data.startswith('verification success'))
@buttons.delete_message
async def verification_success(call: types.CallbackQuery):
    user_id = int(call.data.split()[2])
    user.verify_user(user_id)
    await bot.send_message(chat_id=user_id, text='Вы получили доступ к боту. Пропишите /start для использования')


@dp.callback_query_handler(lambda call: call.data.startswith('verification failed'))
@buttons.delete_message
async def verification_failed(call: types.CallbackQuery):
    user_id = int(call.data.split()[2])
    await bot.send_message(chat_id=user_id, text='Администраторы отклонили вашу заявку')