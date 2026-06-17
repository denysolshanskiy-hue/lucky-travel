from __future__ import annotations

import asyncio
import html
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import Config, load_config
from database import Database, Tour
from keyboards import (
    BTN_BOOKINGS,
    BTN_CAMPING,
    BTN_CREATE_TOUR,
    BTN_MY_TOURS,
    BTN_PACKING_DAY,
    BTN_PACKING_OVERNIGHT,
    BTN_TOURS,
    BTN_RENT,
    admin_booking_keyboard,
    admin_rental_booking_keyboard,
    admin_camping_booking_keyboard,
    camping_keyboard,
    camping_numbers_keyboard,
    camping_payment_keyboard,
    main_menu,
    payment_keyboard,
    tour_detail_keyboard,
    tours_keyboard,
    rental_keyboard,
)
from texts import DAY_PACKING_TEXT, OVERNIGHT_PACKING_TEXT

router = Router()
db: Database
config: Config


class NewTour(StatesGroup):
    title = State()
    starts_at = State()
    price = State()
    prepay = State()
    seats_total = State()
    kind = State()
    photo = State()
    included = State()
    route = State()
    booking_date = State()
    instructor_contact = State()
    car_number = State()


class BookingFlow(StatesGroup):
    full_name = State()
    phone = State()
    people_count = State()
    ages = State()


class CampingFlow(StatesGroup):
    booking_date = State()
    full_name = State()
    phone = State()

class RentalFlow(StatesGroup):
    booking_date = State()
    full_name = State()
    phone = State()

TENT_TOTAL = 6
HAMMOCK_TOTAL = 4
COMMUNITY_URL = "https://t.me/luckytraval"
CAMPING_LOCATION_URL = "https://maps.app.goo.gl/ujbWhYRXWn5T3dAX7?g_st=it"
CAMPING_OPTIONS = {
    "tent_one": {
        "title": "Намет на 1 особу",
        "item_type": "tent",
        "units": 1,
    },
    "tent_two": {
        "title": "Намет на 2 особи",
        "item_type": "tent",
        "units": 1,
    },
    "tent_two_child": {
        "title": "Намет на 2 особи + дитина",
        "item_type": "tent",
        "units": 1,
    },
    "hammock": {
        "title": "Намет-гамак на 1 особу",
        "item_type": "hammock",
        "units": 1,
    },
}
RENTAL_OPTIONS = {
    "kayak_1d": ("Байдарка\місце на 1 день", 700),
    "kayak_2d": ("Байдарка\місце на 2 дні", 1300),
    "kayak_3d": ("Байдарка\місце на 3 дні", 1800),
    "kayak_4d": ("Байдарка\місце на 4 дні", 2000),
    "kayak_5d": ("Байдарка\місце на 5 днів", 2500),
    "kayak_6d": ("Байдарка\місце на 6 днів", 3000),
    "kayak_7d": ("Байдарка\місце на 7 днів", 3500),

    "kayak_hour": ("Байдарка\місце на 1 годину", 200),

    "sup_1d": ("SUP на 1 день", 1200),
    "sup_2d": ("SUP на 2 дні", 2000),
    "sup_3d": ("SUP на 3 дні", 3000),
    "sup_4d": ("SUP на 4 дні", 4000),
    "sup_5d": ("SUP на 5 днів", 5000),
    "sup_6d": ("SUP на 6 днів", 6000),
    "sup_7d": ("SUP на 7 днів", 7000),

    "sup_hour": ("SUP на 1 годину", 400),
}

def is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


def parse_datetime(value: str) -> str:
    normalized = value.strip()
    for pattern in (
        "%d.%m.%Y %H:%M",
        "%d-%m-%Y %H:%M",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M",
    ):
        try:
            return datetime.strptime(normalized, pattern).isoformat(timespec="minutes")
        except ValueError:
            continue
    raise ValueError


def format_dt(value: str) -> str:
    return datetime.fromisoformat(value).strftime("%d.%m.%Y о %H:%M")


def tour_text(tour: Tour) -> str:
    prepay = f"\nПередплата: {tour.prepay} грн" if tour.prepay else ""
    seats = f"\nКількість місць: {tour.seats_total}" if tour.seats_total else ""
    kind = "тур з ночівлею" if tour.kind == "overnight" else "одноденний тур"
    return (
        f"<b>{tour.title}</b>\n\n"
        f"Дата і час: {format_dt(tour.starts_at)}\n"
        f"Формат: {kind}\n"
        f"Ціна: {tour.price} грн{prepay}{seats}\n\n"
        f"<b>У ціну входить:</b>\n{tour.included}\n\n"
        f"<b>Маршрут:</b>\n{tour.route}"
    )


def booking_admin_text(booking_id: int, tour: Tour, data: dict) -> str:
    username = f"@{data['username']}" if data.get("username") else "без username"
    return (
        f"Нова заявка #{booking_id}\n\n"
        f"Тур: {tour.title}\n"
        f"Дата: {format_dt(tour.starts_at)}\n"
        f"Клієнт: {data['full_name']} ({username})\n"
        f"Телефон: {data['phone']}\n"
        f"Кількість людей: {data['people_count']}\n"
        f"Учасники:\n{data['ages']}\n\n"
        f"Після перевірки оплати натисніть кнопку нижче."
    )


def reminder_text(tour: Tour, days_before: int) -> str:
    packing = OVERNIGHT_PACKING_TEXT if tour.kind == "overnight" else DAY_PACKING_TEXT
    contact = f"\nКонтакти інструктора: {tour.instructor_contact}" if tour.instructor_contact else ""
    car = f"\nНомер авто: {tour.car_number}" if tour.car_number else ""
    return (
        f"Нагадування: до туру «{tour.title}» залишилось {days_before} дн.\n"
        f"Старт: {format_dt(tour.starts_at)}\n"
        f"{contact}{car}\n\n"
        f"{packing}"
    )


async def notify_booking_status(bot: Bot, booking_id: int, status: str) -> bool:
    ok = await db.update_booking_status(booking_id, status)
    if not ok:
        return False

    booking = await db.get_booking(booking_id)
    if not booking:
        return True

    if status == "paid":
        await bot.send_message(
            booking.user_id,
            f"Оплату за тур «{booking.tour_title}» підтверджено.\n"
            f"Дата туру: {format_dt(booking.starts_at or '')}\n\n"
            f"Дякуємо, ваша заявка #{booking.id} активна.",
        )
    elif status == "cancelled":
        await bot.send_message(
            booking.user_id,
            f"Заявку #{booking.id} на тур «{booking.tour_title}» скасовано.",
        )
    return True


async def camping_availability() -> tuple[int, int]:
    used = await db.camping_used_units()
    free_tents = max(TENT_TOTAL - used.get("tent", 0), 0)
    free_hammocks = max(HAMMOCK_TOTAL - used.get("hammock", 0), 0)
    return free_tents, free_hammocks


def camping_total_for(item_type: str) -> int:
    return TENT_TOTAL if item_type == "tent" else HAMMOCK_TOTAL


async def camping_free_numbers(item_type: str) -> list[int]:
    booked = await db.camping_booked_numbers(item_type)
    free_numbers = [
        number
        for number in range(1, camping_total_for(item_type) + 1)
        if number not in booked
    ]
    used = await db.camping_used_units()
    legacy_bookings = max(used.get(item_type, 0) - len(booked), 0)
    if legacy_bookings:
        return free_numbers[legacy_bookings:]
    return free_numbers


async def send_camping(message: Message) -> None:
    free_tents, free_hammocks = await camping_availability()
    text = (
        "<b>Кемпінг</b>\n\n"
        "Можна окремо забронювати місце для ночівлі.\n\n"
        f"Вільно звичайних наметів: {free_tents} з {TENT_TOTAL}\n"
        f"Вільно наметів-гамаків: {free_hammocks} з {HAMMOCK_TOTAL}\n\n"
        "Оберіть варіант:"
    )
    await message.answer(text, reply_markup=camping_keyboard(free_tents, free_hammocks))


def camping_admin_text(booking_id: int, data: dict) -> str:
    username = f"@{data['username']}" if data.get("username") else "без username"
    return (
        f"Нова бронь кемпінгу #{booking_id}\n\n"
        f"Дата: {data['booking_date']}\n\n"
        f"Варіант: {data['option_title']} №{data['item_number']}\n"
        f"Клієнт: {data['full_name']} ({username})\n"
        f"Телефон: {data['phone']}"
    )


def participant_names(text: str) -> list[str]:
    names = []
    for line in text.splitlines():
        clean = line.strip(" -•\t")
        if not clean:
            continue
        if " - " in clean:
            clean = clean.split(" - ", 1)[0].strip()
        else:
            clean = "".join(char for char in clean if not char.isdigit()).strip(" -,:")
        if clean:
            names.append(clean)
    return names


def telegram_link(user_id: int, username: str | None) -> str:
    if username:
        return f"@{username}"
    return f'<a href="tg://user?id={user_id}">профіль Telegram</a>'


def participants_text(tour: Tour, bookings: list, admin_view: bool) -> str:
    if not bookings:
        return f"На тур «{html.escape(tour.title)}» ще немає зареєстрованих учасників."

    if admin_view:
        lines = [f"<b>Учасники туру «{html.escape(tour.title)}»</b>"]
        for booking in bookings:
            status = "оплачено" if booking.status == "paid" else "очікує оплати"
            lines.append(
                "\n"
                f"Заявка #{booking.id} ({status})\n"
                f"Контактна особа: {html.escape(booking.full_name)}\n"
                f"Телефон: {html.escape(booking.phone)}\n"
                f"Telegram: {telegram_link(booking.user_id, booking.username)}\n"
                f"Кількість людей: {booking.people_count}\n"
                f"Учасники:\n{html.escape(booking.ages)}"
            )
        return "\n".join(lines)

    names = []
    for booking in bookings:
        names.extend(participant_names(booking.ages))

    if not names:
        names = [booking.full_name for booking in bookings]

    lines = [f"<b>Учасники туру «{html.escape(tour.title)}»</b>"]
    lines.extend(f"{index}. {html.escape(name)}" for index, name in enumerate(names, start=1))
    return "\n".join(lines)


@router.message(Command("start"))
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Вітаю! Тут можна переглянути тури на байдарках, зареєструватися та отримати список речей.",
        reply_markup=main_menu(is_admin(message.from_user.id)),
    )


@router.callback_query(F.data == "menu")
async def menu_callback(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "Головне меню:",
        reply_markup=main_menu(is_admin(callback.from_user.id)),
    )
    await callback.answer()


@router.message(Command("tours"))
async def tours_command(message: Message) -> None:
    await send_tours(message)


@router.message(lambda message: message.text and "Доступні тури" in message.text)
async def tours_button(message: Message, state: FSMContext) -> None:
    await state.clear()
    await send_tours(message)


@router.callback_query(F.data == "tours")
async def tours_callback(callback: CallbackQuery) -> None:
    await send_tours(callback.message)
    await callback.answer()


async def send_tours(message: Message) -> None:
    tours = await db.list_active_tours()
    if not tours:
        await message.answer("Поки немає активних турів.")
        return
    await message.answer("Оберіть тур:", reply_markup=tours_keyboard(tours))


@router.callback_query(F.data.startswith("tour:"))
async def tour_detail(callback: CallbackQuery) -> None:
    tour_id = int(callback.data.split(":")[1])
    tour = await db.get_tour(tour_id)
    if not tour:
        await callback.answer("Тур не знайдено", show_alert=True)
        return
    if tour.photo_file_id:
        await callback.message.answer_photo(
            photo=tour.photo_file_id,
            caption=tour_text(tour),
            reply_markup=tour_detail_keyboard(tour.id),
        )
    else:
        await callback.message.answer(tour_text(tour), reply_markup=tour_detail_keyboard(tour.id))
    await callback.answer()


@router.callback_query(F.data.startswith("tour_participants:"))
async def tour_participants(callback: CallbackQuery) -> None:
    tour_id = int(callback.data.split(":")[1])
    tour = await db.get_tour(tour_id)
    if not tour:
        await callback.answer("Тур не знайдено", show_alert=True)
        return
    bookings = await db.list_tour_bookings(tour_id)
    await callback.message.answer(
        participants_text(
            tour,
            bookings,
            admin_view=is_admin(callback.from_user.id),
        )
    )
    await callback.answer()


@router.message(Command("packing_day"))
async def packing_day(message: Message) -> None:
    await message.answer(DAY_PACKING_TEXT)


@router.message(lambda message: message.text and "На 1 день" in message.text)
async def packing_day_button(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(DAY_PACKING_TEXT)


@router.message(Command("packing_overnight"))
async def packing_overnight(message: Message) -> None:
    await message.answer(OVERNIGHT_PACKING_TEXT)


@router.message(lambda message: message.text and "З ночівлею" in message.text)
async def packing_overnight_button(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(OVERNIGHT_PACKING_TEXT)


@router.message(lambda message: message.text and "Кемпінг" in message.text)
async def camping_button(message: Message, state: FSMContext) -> None:
    await state.clear()
    await send_camping(message)


@router.callback_query(F.data == "packing:day")
async def packing_day_callback(callback: CallbackQuery) -> None:
    await callback.message.answer(DAY_PACKING_TEXT)
    await callback.answer()


@router.callback_query(F.data == "packing:overnight")
async def packing_overnight_callback(callback: CallbackQuery) -> None:
    await callback.message.answer(OVERNIGHT_PACKING_TEXT)
    await callback.answer()


@router.callback_query(F.data == "camping:refresh")
async def camping_refresh(callback: CallbackQuery) -> None:
    await send_camping(callback.message)
    await callback.answer()


@router.callback_query(F.data.startswith("camping:"))
async def camping_select(callback: CallbackQuery, state: FSMContext) -> None:
    option_code = callback.data.split(":")[1]
    option = CAMPING_OPTIONS.get(option_code)
    if not option:
        await callback.answer("Варіант не знайдено.", show_alert=True)
        return

    free_numbers = await camping_free_numbers(option["item_type"])
    if not free_numbers:
        await callback.answer("На жаль, цей варіант уже зайнятий.", show_alert=True)
        await send_camping(callback.message)
        return

    await state.clear()
    item_name = "намету" if option["item_type"] == "tent" else "намету-гамака"
    await callback.message.answer(
        f"Обрано: {option['title']}\n"
        f"Оберіть номер {item_name}:",
        reply_markup=camping_numbers_keyboard(
            option_code,
            option["item_type"],
            free_numbers,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("camping_number:"))
async def camping_number_select(callback: CallbackQuery, state: FSMContext) -> None:
    _, option_code, item_type, raw_number = callback.data.split(":")
    option = CAMPING_OPTIONS.get(option_code)
    if not option or option["item_type"] != item_type:
        await callback.answer("Варіант не знайдено.", show_alert=True)
        return

    item_number = int(raw_number)
    free_numbers = await camping_free_numbers(item_type)
    if item_number not in free_numbers:
        await callback.answer("Цей номер уже заброньовано.", show_alert=True)
        await callback.message.answer(
            "Оберіть інший вільний номер:",
            reply_markup=camping_numbers_keyboard(option_code, item_type, free_numbers),
        )
        return

    await state.clear()
    await state.update_data(
        option_code=option_code,
        option_title=option["title"],
        item_type=item_type,
        item_number=item_number,
        units=option["units"],
    )
    await state.set_state(CampingFlow.booking_date)

    await callback.message.answer(
        f"Обрано: {option['title']} №{item_number}\n\n"
        "Введіть дату бронювання у форматі:\n"
        "15.07.2026"
    )

@router.message(CampingFlow.full_name)
async def camping_full_name(message: Message, state: FSMContext) -> None:
    await state.update_data(full_name=message.text.strip())
    await state.set_state(CampingFlow.phone)
    await message.answer("Введіть номер телефону.")

@router.message(CampingFlow.booking_date)
async def camping_booking_date(
    message: Message,
    state: FSMContext
):
    await state.update_data(
        booking_date=message.text.strip()
    )

    await state.set_state(CampingFlow.full_name)

    await message.answer(
        "Введіть ваше ім'я та прізвище."
    )

@router.message(CampingFlow.phone)
async def camping_phone(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.update_data(
        phone=message.text.strip(),
        user_id=message.from_user.id,
        username=message.from_user.username,
    )

    free_numbers = await camping_free_numbers(data["item_type"])
    if data["item_number"] not in free_numbers:
        await state.clear()
        await message.answer(
            "На жаль, поки ви заповнювали дані, цей номер уже забронювали."
        )
        await send_camping(message)
        return

    booking_id = await db.create_camping_booking(data)
    await state.clear()
    camping_text = (
        f"Бронь кемпінгу #{booking_id} створено.\n\n"
        f"Варіант: {data['option_title']} №{data['item_number']}\n"
        f"Телефон: {data['phone']}\n\n"
        "Для підтвердження броні оплатіть кемпінг окремою кнопкою нижче.\n\n"
        "Локацію кемпінгу також додали нижче: там зручно відкрити маршрут на карті."
    )
    if config.camping_payment_url:
        await message.answer(
            camping_text,
            reply_markup=camping_payment_keyboard(
                config.camping_payment_url,
                CAMPING_LOCATION_URL,
            ),
        )
    else:
        await message.answer(camping_text)

    for admin_id in config.admin_ids:
        await bot.send_message(
            admin_id,
            camping_admin_text(booking_id, data),
            reply_markup=admin_camping_booking_keyboard(booking_id),
        )

@router.message(lambda message: message.text and "Прокат байдарок" in message.text)
async def rental_button(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "Оберіть варіант прокату:",
        reply_markup=rental_keyboard()
    )

@router.callback_query(F.data.startswith("rent:"))
async def rent_select(callback: CallbackQuery, state: FSMContext):
    code = callback.data.split(":")[1]

    title, price = RENTAL_OPTIONS[code]

    await state.clear()
    await state.update_data(
        rental_title=title,
        rental_price=price,
    )

    await state.set_state(RentalFlow.booking_date)

    await callback.message.answer(
        f"Обрано:\n{title}\n\n"
        "Введіть дату бронювання у форматі:\n"
        "15.07.2026"
    )

    await callback.answer()

@router.message(RentalFlow.booking_date)
async def rental_booking_date(
    message: Message,
    state: FSMContext
):
    await state.update_data(
        booking_date=message.text.strip()
    )

    await state.set_state(RentalFlow.full_name)

    await message.answer(
        "Введіть ваше ім'я та прізвище."
    )
    
@router.message(RentalFlow.full_name)
async def rental_name(message: Message, state: FSMContext):
    await state.update_data(
        full_name=message.text.strip()
    )

    await state.set_state(RentalFlow.phone)

    await message.answer("Введіть номер телефону.")

@router.message(RentalFlow.phone)
async def rental_phone(
    message: Message,
    state: FSMContext,
    bot: Bot
):
    data = await state.update_data(
        phone=message.text.strip(),
        username=message.from_user.username,
        user_id=message.from_user.id,
    )

    booking_id = await db.create_rental_booking(data)
    await state.clear()

    text = (
    f"✅ Заявку #{booking_id} прийнято\n\n"
    f"Послуга: {data['rental_title']}\n"
    f"Сума до оплати: {data['rental_price']} грн"
)

    await message.answer(
        text,
        reply_markup=payment_keyboard(
            "https://send.monobank.ua/jar/2zFqHRhbGi"
        )
    )

    admin_text = (
        "Нова заявка на прокат\n\n"
        f"Дата: {data['booking_date']}\n\n"
        f"Клієнт: {data['full_name']}\n"
        f"Телефон: {data['phone']}\n"
        f"Telegram: @{data['username'] if data['username'] else 'немає'}\n\n"
        f"Послуга: {data['rental_title']}\n"
        f"Сума: {data['rental_price']} грн"
    )

    for admin_id in config.admin_ids:
        await bot.send_message(admin_id, admin_text)

@router.callback_query(
    F.data.startswith("admin:rental_paid:")
)
async def rental_paid(callback: CallbackQuery):
    ...

@router.callback_query(
    F.data.startswith("admin:rental_cancel:")
)
async def rental_cancel(callback: CallbackQuery):
    ...

@router.message(Command("newtour"))
async def new_tour(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Ця команда доступна тільки адміну.")
        return
    await start_new_tour(message, state)


@router.callback_query(F.data == "admin:newtour")
async def new_tour_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Це меню тільки для адміна.", show_alert=True)
        return
    await start_new_tour(callback.message, state)
    await callback.answer()


@router.message(lambda message: message.text and "Створити тур" in message.text)
async def new_tour_button(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Ця кнопка доступна тільки адміну.")
        return
    await start_new_tour(message, state)


async def start_new_tour(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(NewTour.title)
    await message.answer("Введіть назву туру.")


@router.message(NewTour.title)
async def new_tour_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await state.set_state(NewTour.starts_at)
    await message.answer("Введіть дату і час старту. Наприклад: 15.07.2026 09:00")


@router.message(NewTour.starts_at)
async def new_tour_starts_at(message: Message, state: FSMContext) -> None:
    try:
        starts_at = parse_datetime(message.text)
    except ValueError:
        await message.answer("Не вийшло розпізнати дату. Приклад: 15.07.2026 09:00")
        return
    await state.update_data(starts_at=starts_at)
    await state.set_state(NewTour.price)
    await message.answer("Введіть повну ціну туру в грн, тільки число.")


@router.message(NewTour.price)
async def new_tour_price(message: Message, state: FSMContext) -> None:
    if not message.text.strip().isdigit():
        await message.answer("Введіть тільки число, наприклад 1800.")
        return
    await state.update_data(price=int(message.text.strip()))
    await state.set_state(NewTour.prepay)
    await message.answer("Введіть суму передплати в грн або напишіть 0, якщо передплати немає.")


@router.message(NewTour.prepay)
async def new_tour_prepay(message: Message, state: FSMContext) -> None:
    if not message.text.strip().isdigit():
        await message.answer("Введіть тільки число.")
        return
    prepay = int(message.text.strip())
    await state.update_data(prepay=prepay or None)
    await state.set_state(NewTour.seats_total)
    await message.answer("Введіть кількість місць у турі, тільки число.")


@router.message(NewTour.seats_total)
async def new_tour_seats_total(message: Message, state: FSMContext) -> None:
    if not message.text.strip().isdigit() or int(message.text.strip()) < 1:
        await message.answer("Введіть число більше 0.")
        return
    await state.update_data(seats_total=int(message.text.strip()))
    await state.set_state(NewTour.kind)
    await message.answer("Який формат туру? Напишіть: 1 день або ночівля.")


@router.message(NewTour.kind)
async def new_tour_kind(message: Message, state: FSMContext) -> None:
    text = message.text.strip().lower()
    if text not in {"1 день", "одноденний", "день", "ночівля", "з ночівлею"}:
        await message.answer("Напишіть «1 день» або «ночівля».")
        return
    await state.update_data(kind="overnight" if "ноч" in text else "day")
    await state.set_state(NewTour.photo)
    await message.answer("Надішліть фото туру або напишіть пропустити.")


@router.message(NewTour.photo)
async def new_tour_photo(message: Message, state: FSMContext) -> None:
    if message.photo:
        await state.update_data(photo_file_id=message.photo[-1].file_id)
    elif message.text and message.text.strip().lower() == "пропустити":
        await state.update_data(photo_file_id=None)
    else:
        await message.answer("Надішліть фото або напишіть пропустити.")
        return
    await state.set_state(NewTour.included)
    await message.answer("Напишіть, що входить у ціну. Можна списком.")


@router.message(NewTour.included)
async def new_tour_included(message: Message, state: FSMContext) -> None:
    await state.update_data(included=message.text.strip())
    await state.set_state(NewTour.route)
    await message.answer("Опишіть маршрут туру.")


@router.message(NewTour.route)
async def new_tour_route(message: Message, state: FSMContext) -> None:
    await state.update_data(route=message.text.strip())
    await state.set_state(NewTour.instructor_contact)
    await message.answer("Введіть контакти інструктора для нагадувань або напишіть пропустити.")


@router.message(NewTour.instructor_contact)
async def new_tour_instructor(message: Message, state: FSMContext) -> None:
    value = None if message.text.strip().lower() == "пропустити" else message.text.strip()
    await state.update_data(instructor_contact=value)
    await state.set_state(NewTour.car_number)
    await message.answer("Введіть номер авто для нагадувань або напишіть пропустити.")


@router.message(NewTour.car_number)
async def new_tour_car(message: Message, state: FSMContext) -> None:
    value = None if message.text.strip().lower() == "пропустити" else message.text.strip()
    data = await state.update_data(car_number=value)
    tour_id = await db.create_tour(data)
    await state.clear()
    await message.answer(f"Тур створено. ID: {tour_id}")


@router.callback_query(F.data.startswith("book:"))
async def start_booking(callback: CallbackQuery, state: FSMContext) -> None:
    tour_id = int(callback.data.split(":")[1])
    tour = await db.get_tour(tour_id)
    if not tour:
        await callback.answer("Тур не знайдено", show_alert=True)
        return
    await state.clear()
    await state.update_data(tour_id=tour_id)
    await state.set_state(BookingFlow.full_name)
    await callback.message.answer("Введіть ваше ім'я та прізвище.")
    await callback.answer()


@router.message(BookingFlow.full_name)
async def booking_name(message: Message, state: FSMContext) -> None:
    await state.update_data(full_name=message.text.strip())
    await state.set_state(BookingFlow.phone)
    await message.answer("Введіть номер телефону.")


@router.message(BookingFlow.phone)
async def booking_phone(message: Message, state: FSMContext) -> None:
    await state.update_data(phone=message.text.strip())
    await state.set_state(BookingFlow.people_count)
    await message.answer("Скільки людей ви реєструєте? Введіть число.")


@router.message(BookingFlow.people_count)
async def booking_people_count(message: Message, state: FSMContext) -> None:
    if not message.text.strip().isdigit() or int(message.text.strip()) < 1:
        await message.answer("Введіть число більше 0.")
        return
    await state.update_data(people_count=int(message.text.strip()))
    await state.set_state(BookingFlow.ages)
    count = int(message.text.strip())
    await message.answer(
        "Вкажіть ім'я та вік кожного учасника.\n"
        "Краще писати кожного з нового рядка.\n\n"
        f"Потрібно учасників: {count}\n"
        "Наприклад:\n"
        "Артем - 35\n"
        "Олексій - 40\n"
        "Михайло - 14"
    )


@router.message(BookingFlow.ages)
async def booking_ages(message: Message, state: FSMContext, bot: Bot) -> None:
    participants = message.text.strip()
    if not any(char.isdigit() for char in participants):
        await message.answer(
            "Додайте, будь ласка, вік учасників. Наприклад:\n"
            "Артем - 35\n"
            "Олексій - 40"
        )
        return

    data = await state.update_data(
        ages=participants,
        user_id=message.from_user.id,
        username=message.from_user.username,
    )
    tour = await db.get_tour(data["tour_id"])
    if not tour:
        await state.clear()
        await message.answer("Тур не знайдено. Спробуйте обрати тур ще раз.")
        return

    booking_id = await db.create_booking(data)
    await state.clear()

    pay_url = tour.payment_url or config.mono_payment_url
    amount_to_pay = tour.prepay or tour.price
    instructor = (
        f"\nІнструктор: {tour.instructor_contact}\n"
        if tour.instructor_contact
        else ""
    )
    text = (
        f"Заявку #{booking_id} прийнято.\n\n"
        f"Тур: {tour.title}\n"
        f"Дата: {format_dt(tour.starts_at)}\n"
        f"Кількість людей: {data['people_count']}\n"
        f"Учасники:\n{data['ages']}\n"
        f"{instructor}\n"
        f"Сума до оплати: {amount_to_pay} грн\n\n"
        f"Після оплати ми підтвердимо вашу заявку тут у боті."
    )
    if pay_url:
        await message.answer(
            text,
            reply_markup=payment_keyboard(pay_url, community_url=COMMUNITY_URL),
        )
    else:
        await message.answer(text)

    admin_text = booking_admin_text(booking_id, tour, data)
    for admin_id in config.admin_ids:
        await bot.send_message(
            admin_id,
            admin_text,
            reply_markup=admin_booking_keyboard(booking_id),
        )


@router.message(Command("mytours"))
async def my_tours(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Ця команда доступна тільки адміну.")
        return
    await send_admin_tours(message)


@router.callback_query(F.data == "admin:mytours")
async def my_tours_callback(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Це меню тільки для адміна.", show_alert=True)
        return
    await send_admin_tours(callback.message)
    await callback.answer()


@router.message(lambda message: message.text and "Мої тури" in message.text)
async def my_tours_button(message: Message, state: FSMContext) -> None:
    await state.clear()
    if not is_admin(message.from_user.id):
        await message.answer("Ця кнопка доступна тільки адміну.")
        return
    await send_admin_tours(message)


async def send_admin_tours(message: Message) -> None:
    tours = await db.list_active_tours()
    if not tours:
        await message.answer("Активних турів немає.")
        return
    lines = [
        f"#{tour.id} - {tour.title} - {format_dt(tour.starts_at)} - "
        f"{tour.price} грн - місць: {tour.seats_total or 'не вказано'}"
        for tour in tours
    ]
    await message.answer("\n".join(lines))


@router.message(Command("bookings"))
async def bookings(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Ця команда доступна тільки адміну.")
        return
    await send_admin_bookings(message)


@router.callback_query(F.data == "admin:bookings")
async def bookings_callback(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Це меню тільки для адміна.", show_alert=True)
        return
    await send_admin_bookings(callback.message)
    await callback.answer()


@router.message(lambda message: message.text and "Заявки" in message.text)
async def bookings_button(message: Message, state: FSMContext) -> None:
    await state.clear()
    if not is_admin(message.from_user.id):
        await message.answer("Ця кнопка доступна тільки адміну.")
        return
    await send_admin_bookings(message)


async def send_admin_bookings(message: Message) -> None:
    rows = await db.list_recent_bookings()
    camping_rows = await db.list_recent_camping_bookings()
    rental_rows = await db.list_recent_rental_bookings()
    if not rows and not camping_rows and not rental_rows:
        await message.answer("Заявок поки немає.")
        return

    for row in rows:
        text = (
            f"#{row.id} [{row.status}] {row.tour_title} - {format_dt(row.starts_at or '')}\n"
            f"{row.full_name}, {row.phone}, людей: {row.people_count}\n"
            f"Учасники:\n{row.ages}"
        )
        await message.answer(text, reply_markup=admin_booking_keyboard(row.id))

    for row in camping_rows:
        text = (
            f"Кемпінг #{row.id} [{row.status}]\n"
            f"Дата: {row.booking_date}\n"
            f"{row.option_title} №{row.item_number if row.item_number else 'не вказано'}\n"
            f"{row.full_name}, {row.phone}"
        )
        await message.answer(text, reply_markup=admin_camping_booking_keyboard(row.id))

    for row in rental_rows:
        text = (
            f"Прокат #{row.id} [{row.status}]\n"
            f"Дата: {row.booking_date}\n"
            f"{row.rental_title}\n"
            f"{row.full_name}, {row.phone}\n"
            f"Сума: {row.rental_price} грн"
        )

    await message.answer(
        text,
        reply_markup=admin_rental_booking_keyboard(row.id)
    )

@router.message(Command("paid"))
async def paid(message: Message, command: CommandObject) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Ця команда доступна тільки адміну.")
        return
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Вкажіть номер заявки. Наприклад: /paid 1")
        return
    booking_id = int(command.args.strip())
    ok = await notify_booking_status(message.bot, booking_id, "paid")
    await message.answer(
        f"Оплату за заявку #{booking_id} підтверджено, клієнту надіслано повідомлення."
        if ok
        else "Заявку не знайдено."
    )


@router.callback_query(F.data.startswith("admin:paid:"))
async def paid_callback(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Це меню тільки для адміна.", show_alert=True)
        return
    booking_id = int(callback.data.split(":")[2])
    ok = await notify_booking_status(callback.bot, booking_id, "paid")
    if ok:
        await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"Оплату за заявку #{booking_id} підтверджено, клієнту надіслано повідомлення."
        if ok
        else "Заявку не знайдено."
    )
    await callback.answer()


@router.message(Command("cancel"))
async def cancel(message: Message, command: CommandObject) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Ця команда доступна тільки адміну.")
        return
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Вкажіть номер заявки. Наприклад: /cancel 1")
        return
    booking_id = int(command.args.strip())
    ok = await notify_booking_status(message.bot, booking_id, "cancelled")
    await message.answer(
        f"Заявку #{booking_id} скасовано, клієнту надіслано повідомлення."
        if ok
        else "Заявку не знайдено."
    )


@router.callback_query(F.data.startswith("admin:cancel:"))
async def cancel_callback(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Це меню тільки для адміна.", show_alert=True)
        return
    booking_id = int(callback.data.split(":")[2])
    ok = await notify_booking_status(callback.bot, booking_id, "cancelled")
    if ok:
        await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"Заявку #{booking_id} скасовано, клієнту надіслано повідомлення."
        if ok
        else "Заявку не знайдено."
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:camping_cancel:"))
async def camping_cancel_callback(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Це меню тільки для адміна.", show_alert=True)
        return
    booking_id = int(callback.data.split(":")[2])
    ok = await db.update_camping_booking_status(booking_id, "cancelled")
    if ok:
        await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"Бронь кемпінгу #{booking_id} скасовано." if ok else "Бронь не знайдено."
    )
    await callback.answer()


async def send_reminders(bot: Bot) -> None:
    today = datetime.now().date()
    for booking, tour in await db.reminder_candidates():
        starts_at = datetime.fromisoformat(tour.starts_at).date()
        days = (starts_at - today).days

        if days == 3 and not booking.reminder_3d_sent:
            await bot.send_message(booking.user_id, reminder_text(tour, 3))
            await db.mark_reminder_sent(booking.id, 3)
        elif days == 1 and not booking.reminder_1d_sent:
            await bot.send_message(booking.user_id, reminder_text(tour, 1))
            await db.mark_reminder_sent(booking.id, 1)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    global db, config
    config = load_config()
    db = Database(config.database_path)
    await db.init()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    scheduler.add_job(send_reminders, "interval", hours=1, args=[bot])
    scheduler.start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
