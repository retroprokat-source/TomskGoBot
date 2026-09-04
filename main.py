import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN, BOT_URL
from database import (
    init_db,
    add_user,
    add_purchase,
    has_purchase,
    get_progress,
    save_progress,
    reset_progress,
    get_purchased_routes,
    add_payment,
    get_payment_by_link_id,
    update_payment_status,
)
from routes_data import get_routes, get_route
from services.payments import create_payment_link

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()


class RouteState(StatesGroup):
    waiting_for_payment = State()


def main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🏛 Маршруты", callback_data="show_routes")],
        [InlineKeyboardButton(text="🎓 Мои маршруты", callback_data="my_routes")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def routes_keyboard():
    routes = get_routes()
    buttons = []
    for route in routes:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{route['name']} — {route['price']} ₽",
                    callback_data=f"route_info:{route['id']}"
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def route_info_keyboard(route_id: str, purchased: bool):
    buttons = []

    if purchased:
        buttons.append(
            [InlineKeyboardButton(text="▶️ Начать маршрут", callback_data=f"start_route:{route_id}")]
        )
    else:
        buttons.append(
            [InlineKeyboardButton(text="🚶 Первые 2 точки — бесплатно", callback_data=f"free_start:{route_id}")]
        )
        buttons.append(
            [InlineKeyboardButton(text="💳 Купить маршрут", callback_data=f"buy_route:{route_id}")]
        )

    buttons.append([InlineKeyboardButton(text="⬅️ К маршрутам", callback_data="show_routes")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def navigation_keyboard(route_id: str, current_point: int, total_points: int, purchased: bool):
    buttons = []

    prev_button = InlineKeyboardButton(
        text="⬅️ Предыдущая",
        callback_data=f"nav:{route_id}:{current_point - 1}"
    )
    next_button = InlineKeyboardButton(
        text="➡️ Следующая",
        callback_data=f"nav:{route_id}:{current_point + 1}"
    )

    if current_point == 1:
        buttons.append([next_button])
    elif current_point >= total_points:
        buttons.append([prev_button])
    else:
        buttons.append([prev_button, next_button])

    buttons.append([InlineKeyboardButton(text="🗺️ К маршрутам", callback_data="show_routes")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_keyboard(payment_url: str):
    buttons = [
        [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)],
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data="check_payment")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("start"))
async def cmd_start(message: Message):
    add_user(str(message.from_user.id), message.from_user.username)
    await message.answer(
        "🏛 Добро пожаловать в бот-экскурсию по Томску!\n\n"
        "Здесь можно купить маршрут и пройти его по точкам.\n"
        "Первые 2 точки каждого маршрута — бесплатно.",
        reply_markup=main_menu_keyboard()
    )


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏛 Главное меню\n\nВыберите действие:",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "show_routes")
async def show_routes(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите маршрут:",
        reply_markup=routes_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("route_info:"))
async def route_info(callback: CallbackQuery):
    route_id = callback.data.split(":")[1]
    route = get_route(route_id)

    if not route:
        await callback.answer("Маршрут не найден")
        return

    purchased = has_purchase(str(callback.from_user.id), route_id)

    points_count = len(route["points"])

    text = (
        f"{route['name']}\n\n"
        f"{route['description']}\n\n"
        f"🕒 Время: {route['duration']}\n"
        f"📍 Дистанция: {route['distance']}\n"
        f"🔢 Точек: {points_count}\n"
        f"💰 Цена: {route['price']} ₽\n\n"
    )

    if purchased:
        text += "✅ Маршрут уже куплен. Можно пройти ещё раз."

    await callback.message.edit_text(text, reply_markup=route_info_keyboard(route_id, purchased))
    await callback.answer()


@router.callback_query(F.data.startswith("free_start:"))
async def free_start(callback: CallbackQuery):
    route_id = callback.data.split(":")[1]
    route = get_route(route_id)

    if not route:
        await callback.answer("Маршрут не найден")
        return

    points = route["points"]
    current = 1
    save_progress(str(callback.from_user.id), route_id, current)

    await show_point(callback, route, points, current, purchased=False)


@router.callback_query(F.data.startswith("start_route:"))
async def start_route(callback: CallbackQuery):
    route_id = callback.data.split(":")[1]
    route = get_route(route_id)

    if not route:
        await callback.answer("Маршрут не найден")
        return

    purchased = has_purchase(str(callback.from_user.id), route_id)

    if not purchased:
        await callback.answer("Сначала купите маршрут")
        return

    points = route["points"]
    current = 1
    save_progress(str(callback.from_user.id), route_id, current)

    await show_point(callback, route, points, current, purchased=True)


@router.callback_query(F.data.startswith("nav:"))
async def navigate(callback: CallbackQuery):
    parts = callback.data.split(":")
    route_id = parts[1]
    point_num = int(parts[2])

    route = get_route(route_id)

    if not route:
        await callback.answer("Маршрут не найден")
        return

    points = route["points"]
    purchased = has_purchase(str(callback.from_user.id), route_id)

    if point_num > 2 and not purchased:
        await callback.message.edit_text(
            "🔒 Бесплатно доступны только первые 2 точки.\n\n"
            "Дальше маршрут откроется после оплаты.",
            reply_markup=route_info_keyboard(route_id, purchased)
        )
        await callback.answer()
        return

    if point_num < 1 or point_num > len(points):
        await callback.answer("Недопустимая точка")
        return

    save_progress(str(callback.from_user.id), route_id, point_num)

    await show_point(callback, route, points, point_num, purchased)


async def show_point(callback: CallbackQuery, route, points, point_num: int, purchased: bool):
    point = points[point_num - 1]
    total = len(points)

    progress_bar = "🟩" * point_num + "⬜" * (total - point_num)

    text = (
        f"📍 Точка {point_num} из {total}\n\n"
        f"{point['name']}\n\n"
        f"🏛 {point['description']}\n\n"
        f"📍 Адрес: {point['address']}\n\n"
        f"{progress_bar}"
    )

    if not purchased and point_num >= 2:
        text += "\n\n🔒 Дальше — платный доступ. Откройте весь маршрут."

    if point_num == total:
        text += "\n\n🎉 Это последняя точка маршрута!"

    await callback.message.edit_text(
        text,
        reply_markup=navigation_keyboard(route["id"], point_num, total, purchased)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_route:"))
async def buy_route(callback: CallbackQuery, state: FSMContext):
    route_id = callback.data.split(":")[1]
    route = get_route(route_id)

    if not route:
        await callback.answer("Маршрут не найден")
        return

    if has_purchase(str(callback.from_user.id), route_id):
        await callback.answer("Маршрут уже куплен")
        return

    amount = route["price"]
    purpose = f"Покупка маршрута {route['name']}"

    payment_url, payment_link_id = create_payment_link(
        user_id=str(callback.from_user.id),
        route_id=route_id,
        amount=amount,
        purpose=purpose,
    )

    if not payment_url:
        await callback.message.answer("Ошибка при создании платежа. Попробуйте позже.")
        await callback.answer()
        return

    add_payment(
        user_id=str(callback.from_user.id),
        route_id=route_id,
        amount=float(amount),
        purpose=purpose,
        payment_link_id=payment_link_id,
    )

    await state.update_data(route_id=route_id, payment_link_id=payment_link_id)

    await callback.message.edit_text(
        f"💳 Для покупки маршрута «{route['name']}» оплатите {amount} ₽.\n\n"
        "После оплаты нажмите «Я оплатил».",
        reply_markup=payment_keyboard(payment_url)
    )
    await callback.answer()


@router.callback_query(F.data == "check_payment")
async def check_payment(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    route_id = data.get("route_id")
    payment_link_id = data.get("payment_link_id")

    if not route_id:
        await callback.answer("Нет активной покупки")
        return

    payment = get_payment_by_link_id(payment_link_id) if payment_link_id else None

    if has_purchase(str(callback.from_user.id), route_id):
        await callback.message.edit_text(
            "✅ Маршрут уже куплен!",
            reply_markup=route_info_keyboard(route_id, True)
        )
    elif payment and payment["status"] == "paid":
        add_purchase(str(callback.from_user.id), route_id)
        await callback.message.edit_text(
            "✅ Оплата подтверждена! Маршрут открыт.",
            reply_markup=route_info_keyboard(route_id, True)
        )
    else:
        await callback.answer("Платёж ещё не найден. Попробуйте позже.")
    await callback.answer()


@router.callback_query(F.data == "my_routes")
async def my_routes(callback: CallbackQuery):
    purchased = get_purchased_routes(str(callback.from_user.id))

    if not purchased:
        await callback.message.edit_text(
            "У вас пока нет купленных маршрутов.",
            reply_markup=main_menu_keyboard()
        )
        await callback.answer()
        return

    buttons = []
    for route in purchased:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{route['name']}",
                    callback_data=f"start_route:{route['id']}"
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])

    await callback.message.edit_text(
        "Ваши купленные маршруты:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@router.message(Command("routes"))
async def cmd_routes(message: Message):
    routes = get_routes()
    text = "Маршруты:\n\n"
    for route in routes:
        text += f"{route['name']} — {route['price']} ₽, {route['distance']}\n"
        text += f"{route['description']}\n\n"
    await message.answer(text, reply_markup=routes_keyboard())


@router.message(Command("my_routes"))
async def cmd_my_routes(message: Message):
    purchased = get_purchased_routes(str(message.from_user.id))
    if not purchased:
        await message.answer("У вас пока нет купленных маршрутов.")
        return
    text = "Ваши маршруты:\n\n"
    for route in purchased:
        text += f"• {route['name']}\n"
    await message.answer(text)


async def main():
    init_db()
    dp.include_router(router)
    await dp.start_polling(bot)

from flask import Flask, request

app = Flask(__name__)

@app.route("/")
def health():
    return "OK", 200


@app.route("/webhook/tochka", methods=["GET", "POST"])
def tochka_webhook():
    import json

    if request.method == "GET":
        return "OK", 200

    try:
        data = json.loads(request.get_data(as_text=True))
    except Exception:
        return "OK", 200

    payment_data = data.get("Data", data)

    payment_link_id = payment_data.get("paymentLinkId", "")
    status = payment_data.get("status", "")
    payment_status = payment_data.get("paymentStatus", "")

    if (
        status in ("success", "confirmed", "paid", "APPROVED")
        or payment_status in ("success", "confirmed", "paid", "APPROVED")
    ):
        update_payment_status(payment_link_id, "paid")

        payment = get_payment_by_link_id(payment_link_id)
        if payment:
            user_id = payment["user_id"]
            route_id = payment["route_id"]
            add_purchase(user_id, route_id)

    return "OK", 200


if __name__ == "__main__":
    import time
    from threading import Thread
    from services.payments import setup_webhook

    Thread(target=lambda: app.run(host="0.0.0.0", port=10000)).start()

    def delayed_setup():
        time.sleep(5)
        setup_webhook()

    Thread(target=delayed_setup).start()
    asyncio.run(main())
