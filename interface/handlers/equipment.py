from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from interface.init_bot import dp, bot
from api import user, equipment, qr_code, transfer
import interface.buttons as buttons
from interface.parse_data import parse_qr_code_data, parse_my_equipment_data


class Take_Equipment(StatesGroup):
    """
    Use states as events for taking equipment
    """
    scan_qr_code = State()  # step 1
    waiting_for_confirmation = State()  # step 3


@dp.callback_query_handler(lambda call: call.data == 'take_equipment')
@buttons.delete_message
async def take_equipment_step_1(call: types.CallbackQuery):
    """
    Request a photo with QR code
    """
    await bot.send_message(chat_id=call.message.chat.id, text='Отправьте фото с\
 QR кодом техники. На одном фото должен быть <b>только один QR код</b>.\nПосле\
 отправки всех QR кодов напишите /ok', parse_mode=types.message.ParseMode.HTML)
    await Take_Equipment.scan_qr_code.set()
    state = dp.current_state()
    await state.update_data(user_items=[], equipment_names=[])


@dp.message_handler(state=Take_Equipment.scan_qr_code,
                    content_types=types.ContentTypes.PHOTO)
async def take_equipment_step_2(message: types.Message, state: FSMContext):
    """
    Get QR code, read data from it and create transfer
    """
    # read data from user's photo with QR code
    # TODO: validation control sum
    eq = await read_qr_code(message)
    eq_buffer = await state.get_data()
    if eq:
        transformed_result = parse_qr_code_data(eq)  # get equipment name
        if transformed_result not in eq_buffer['equipment_names']:
            await bot.send_message(chat_id=message.chat.id,
                                   text=transformed_result)
            if transformed_result != 'Данной техники нет в базе данных':
                # write data to storage
                await state.update_data(
                    user_items=eq_buffer['user_items']+[eq],
                    equipment_names=eq_buffer['equipment_names']
                    + [transformed_result],
                    user_id=message.chat.id)
                # create transfer
                eq_data = equipment.get_equipment(int(eq.split()[0]))
                transfer.create_transfer(eq_data['id'], eq_data['holder']['id'],
                                         message.chat.id)
        else:
            await bot.send_message(chat_id=message.chat.id,
                                   text='Вы уже взяли данную технику')


@dp.message_handler(state=Take_Equipment.scan_qr_code, commands='ok')
async def take_equipment_step_3(message: types.Message, state: FSMContext):
    """
    Ask admins for permission
    """
    eq_buffer = await state.get_data()  # list with equipment ids and names
    await bot.send_message(chat_id=message.chat.id,
                           text='Ожидайте подтверждения от администраторов')
    for admin in user.get_admin_list():
        await equipment_confirmation(admin['id'], message.chat.id, eq_buffer)
    await Take_Equipment.next()


@dp.callback_query_handler(lambda call: call.data == 'conf_success',
                           state=Take_Equipment.waiting_for_confirmation)
async def take_equipment_step_4_ok(call: types.CallbackQuery,
                                   state: FSMContext):
    """
    Close transfer and add it to the history
    """
    # TODO: rewrite state with func argument
    # get current state
    user_id = await state.get_data()
    await state.finish()
    user_id = user_id['user_id']  # get user id
    await bot.send_message(chat_id=user_id, text='Ваша заявка на взятие техники\
 была подтверждена')
    user_transfers = [trans['id']
                      for trans in transfer.get_active_transfers(user_id)]
    list(map(transfer.verify_transfer, user_transfers))


@dp.callback_query_handler(lambda call: call.data == 'conf_failed',
                           state=Take_Equipment.waiting_for_confirmation)
async def take_equipment_step_4_fail(call: types.CallbackQuery,
                                     state: FSMContext):
    """
    Close transfer and delete it
    """
    # TODO: rewrite state with func argument
    # get current state
    user_id = await state.get_data()
    await state.finish()
    user_id = user_id['user_id']  # get user id
    await bot.send_message(chat_id=user_id,
                           text='Ваша заявка на взятие техники была отклонена')
    user_transfers = [trans['id']
                      for trans in transfer.get_active_transfers(user_id)]
    list(map(transfer.delete_transfer, user_transfers))


async def read_qr_code(message: types.Message) -> str:
    """
    Create file from user's photo with QR code and read it
    """
    # create file
    photo = await bot.download_file_by_id(message.photo[0].file_id)
    photo_id = str(message.photo[0].file_id)
    qr_code.save_photo(photo, photo_id)
    try:
        # read file
        result = qr_code.get_qr_code_data(qr_code.get_file_path(photo_id))
        # delete file
        qr_code.delete_file(qr_code.get_file_path(photo_id))
    except Exception:
        result = ''
        await bot.send_message(
            chat_id=message.chat.id,
            text='Произошла ошибка в распознавании фото. Попробуйте ещё раз')
    return result


# TODO: delete other messages for other admins
async def equipment_confirmation(admin_id: int, user_id: int, eq_names: list):
    """
    Confirm taking the equipment
    """
    keyboard_interface = buttons.create_inline_markup(
        [{'text': '\U00002705', 'callback': "conf_success"},
         {'text': '\U0000274C', 'callback': "conf_failed"}])

    transformed_eq_names = '\n'.join(eq_names['equipment_names'])
    username = user.get_user(user_id)['username']
    user_name = f'@{username}' if username is not None else f'[{user_id}]\
(tg://user?id={user_id})'
    await bot.send_message(
        chat_id=admin_id,
        text=f"Подтвердите передачу техники к {user_name}.\
 Список техники:\n{transformed_eq_names}",
        reply_markup=keyboard_interface, parse_mode="Markdown")


class Scan_QR_Code(StatesGroup):
    """
    Use states as events for scanning QR code
    """
    scan_qr_code = State()


@dp.callback_query_handler(lambda call: call.data == 'scan_qr_code')
@buttons.delete_message
async def scan_qr_code_step_1(call: types.CallbackQuery):
    """
    Request a photo with QR code
    """
    await bot.send_message(chat_id=call.message.chat.id, text='Отправьте фото с\
 QR кодом техники. На одном фото должен быть <b>только один QR код</b>',
                           parse_mode=types.message.ParseMode.HTML)
    await Scan_QR_Code.scan_qr_code.set()


@dp.message_handler(state=Scan_QR_Code.scan_qr_code,
                    content_types=types.ContentTypes.PHOTO)
async def scan_qr_code_step_2(message: types.Message, state: FSMContext):
    """
    Scan QR code
    """
    # TODO: validation control sum
    data = await read_qr_code(message)
    if data:
        result = parse_qr_code_data(data)
        await bot.send_message(chat_id=message.chat.id, text=result)
        await state.finish()


@dp.callback_query_handler(lambda call: call.data == "return_eq")
@buttons.delete_message
async def return_equipment(call: types.CallbackQuery):
    """
    Return all equipment
    """
    user_eq_data = equipment.get_equipment_by_holder(call.message.chat.id)
    # create transfer from user to storehouse
    for eq in user_eq_data:
        transfer.create_transfer(eq['id'], eq['holder']['id'], 1)
    # move transfer into history
    user_transfers = [transfer.get_transfer_by_equipment_id(eq['id'])['id']
                      for eq in user_eq_data]
    list(map(transfer.verify_transfer, user_transfers))
    list(map(transfer.delete_transfer, user_transfers))

    transformed_result = parse_my_equipment_data(user_eq_data)
    username = call.message.chat.username or user.get_user(
        call.message.chat.id)['username']
    user_id = call.message.chat.id
    for admin in user.get_admin_list():
        await bot.send_message(
            chat_id=admin['id'],
            text='{} вернул(а) данную технику:\n{}'.format(
                f'@{username}' if username is not None
                else f'[{user_id}](tg://user?id={user_id})',
                transformed_result))
    await bot.send_message(
        chat_id=user_id,
        text=f'Данная техника была успешно возвращена:\n{transformed_result}\
\n\nЧтобы вернуться в главное меню напишите /start')
