from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

btn_start = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton('📮Post jo`natish'),
            KeyboardButton('🧾Elon qo`shish')  # voqtli button
        ]
    ],resize_keyboard=True
)
btn_cancel = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton("❌ Bekor qilish")]], resize_keyboard=True
)