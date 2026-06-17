from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from database import Booking, Tour


BTN_TOURS = "🛶 Доступні тури"
BTN_PACKING_DAY = "🎒 На 1 день"
BTN_PACKING_OVERNIGHT = "🏕 З ночівлею"
BTN_CAMPING = "⛺ Кемпінг"
BTN_CREATE_TOUR = "➕ Створити тур"
BTN_MY_TOURS = "📅 Мої тури"
BTN_BOOKINGS = "📝 Заявки"
BTN_RENT = "🏄 Прокат байдарок та SUP"

def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=BTN_TOURS)],
        [
            KeyboardButton(text=BTN_PACKING_DAY),
            KeyboardButton(text=BTN_PACKING_OVERNIGHT),
        ],
        [KeyboardButton(text=BTN_CAMPING), KeyboardButton(text=BTN_RENT)],
    ]
    if is_admin:
        rows.extend(
            [
                [KeyboardButton(text=BTN_CREATE_TOUR)],
                [
                    KeyboardButton(text=BTN_MY_TOURS),
                    KeyboardButton(text=BTN_BOOKINGS),
                ],
            ]
        )
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Оберіть дію",
    )


def tours_keyboard(tours: list[Tour]) -> InlineKeyboardMarkup:
    def tour_button_text(tour: Tour) -> str:
        seats = f" - {tour.seats_total} місць" if tour.seats_total else ""
        return f"{tour.title} - {tour.starts_at[:16].replace('T', ' ')}{seats}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=tour_button_text(tour),
                    callback_data=f"tour:{tour.id}",
                )
            ]
            for tour in tours
        ]
    )


def tour_detail_keyboard(tour_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Зареєструватися", callback_data=f"book:{tour_id}")],
            [InlineKeyboardButton(text="👥 Учасники туру", callback_data=f"tour_participants:{tour_id}")],
            [InlineKeyboardButton(text="Назад до турів", callback_data="tours")],
        ]
    )


def payment_keyboard(url: str, community_url: str | None = None) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="Оплатити через Monobank", url=url)]]
    if community_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text="💬 Чат і корисна інформація", url=community_url
                )
            ]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def camping_payment_keyboard(payment_url: str, location_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оплатити кемпінг через Monobank", url=payment_url)],
            [InlineKeyboardButton(text="📍 Локація кемпінгу на карті", url=location_url)],
        ]
    )


def admin_booking_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Оплату отримано", callback_data=f"admin:paid:{booking_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Скасувати заявку", callback_data=f"admin:cancel:{booking_id}"
                )
            ],
        ]
    )


def camping_keyboard(free_tents: int, free_hammocks: int) -> InlineKeyboardMarkup:
    rows = []
    if free_tents > 0:
        rows.extend(
            [
                [
                    InlineKeyboardButton(
                        text="⛺ Намет на 1 особу", callback_data="camping:tent_one"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⛺ Намет на 2 особи", callback_data="camping:tent_two"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⛺ Намет на 2 + дитина",
                        callback_data="camping:tent_two_child",
                    )
                ],
            ]
        )
    if free_hammocks > 0:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🌳 Намет-гамак на 1 особу", callback_data="camping:hammock"
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="Оновити залишки", callback_data="camping:refresh")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def camping_numbers_keyboard(option_code: str, item_type: str, free_numbers: list[int]) -> InlineKeyboardMarkup:
    rows = []
    for index in range(0, len(free_numbers), 3):
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"№{number}",
                    callback_data=f"camping_number:{option_code}:{item_type}:{number}",
                )
                for number in free_numbers[index : index + 3]
            ]
        )
    rows.append([InlineKeyboardButton(text="Назад до кемпінгу", callback_data="camping:refresh")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_camping_booking_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Скасувати бронь кемпінгу",
                    callback_data=f"admin:camping_cancel:{booking_id}",
                )
            ]
        ]
    )


def bookings_keyboard(bookings: list[Booking]) -> InlineKeyboardMarkup:
    rows = []
    for booking in bookings:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"#{booking.id} - {booking.full_name} - {booking.status}",
                    callback_data=f"admin:booking:{booking.id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="Назад у меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def rental_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text="🛶 Байдарка (місце) на 1 день — 700 грн",
            callback_data="rent:kayak_1d"
        )],
        [InlineKeyboardButton(
            text="🛶 Байдарка (місце) на 2 дні — 1300 грн",
            callback_data="rent:kayak_2d"
        )],
        [InlineKeyboardButton(
            text="🛶 Байдарка (місце) на 3 дні — 1800 грн",
            callback_data="rent:kayak_3d"
        )],
        [InlineKeyboardButton(
            text="🛶 Байдарка (місце) на 4 дні — 2000 грн",
            callback_data="rent:kayak_4d"
        )],
        [InlineKeyboardButton(
            text="🛶 Байдарка (місце) на 5 днів — 2500 грн",
            callback_data="rent:kayak_5d"
        )],
        [InlineKeyboardButton(
            text="🛶 Байдарка (місце) на 6 днів — 3000 грн",
            callback_data="rent:kayak_6d"
        )],
        [InlineKeyboardButton(
            text="🛶 Байдарка (місце) на 7 днів — 3500 грн",
            callback_data="rent:kayak_7d"
        )],
        [InlineKeyboardButton(
            text="🛶 Байдарка (місце) на 1 годину — 200 грн",
            callback_data="rent:kayak_hour"
        )],

        [InlineKeyboardButton(
            text="🏄 SUP на 1 день — 1200 грн",
            callback_data="rent:sup_1d"
        )],
        [InlineKeyboardButton(
            text="🏄 SUP на 2 дні — 2000 грн",
            callback_data="rent:sup_2d"
        )],
        [InlineKeyboardButton(
            text="🏄 SUP на 3 дні — 3000 грн",
            callback_data="rent:sup_3d"
        )],
        [InlineKeyboardButton(
            text="🏄 SUP на 4 дні — 4000 грн",
            callback_data="rent:sup_4d"
        )],
        [InlineKeyboardButton(
            text="🏄 SUP на 5 днів — 5000 грн",
            callback_data="rent:sup_5d"
        )],
        [InlineKeyboardButton(
            text="🏄 SUP на 6 днів — 6000 грн",
            callback_data="rent:sup_6d"
        )],
        [InlineKeyboardButton(
            text="🏄 SUP на 7 днів — 7000 грн",
            callback_data="rent:sup_7d"
        )],
        [InlineKeyboardButton(
            text="🏄 SUP на 1 годину — 400 грн",
            callback_data="rent:sup_hour"
        )],
    ]

    return InlineKeyboardMarkup(inline_keyboard=rows)

def admin_rental_booking_keyboard(
    booking_id: int
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Оплату отримано",
                    callback_data=f"admin:rental_paid:{booking_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Скасувати заявку",
                    callback_data=f"admin:rental_cancel:{booking_id}"
                )
            ]
        ]
    )