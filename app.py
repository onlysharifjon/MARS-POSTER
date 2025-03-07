from aiogram import Bot, types, executor, Dispatcher
import logging
from database import *  # SQLite bazasi uchun
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from datetime import datetime  # Sana va vaqtni olish uchun
import asyncio  # Vaqt bilan ishlash uchun
import time  # Vaqtni tekshirish uchun
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import re

# Admin ID-lari
ADMINS = [5773429637,1210278389,5172746353]

# Bot sozlamalari
bot = Bot(token="8159354014:AAG7vch3LI8849WTEDhLFEq_NTlKRdl7S0k", parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(level=logging.INFO)

# Holatlarni aniqlash
class PostState(StatesGroup):
    photo = State()
    caption = State()

class ElonState(StatesGroup):
    photo = State()
    caption = State()
    time = State()  # Vaqt uchun holat

# Tugmachalar
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

# Botga start bosilganda tugma chiqadi
@dp.message_handler(commands="start")
async def admin_start(message: types.Message):
    await message.answer(f"Assalomu alaykum, {message.from_user.full_name}!", reply_markup=btn_start)


# Yangi holat klassi - vaqtni yangilash uchun
class UpdateTimeState(StatesGroup):
    waiting_for_time = State()
    waiting_for_new_time = State()

# /posts buyrug'i - barcha aktiv postlarni ko'rsatish
@dp.message_handler(commands=["posts"])
async def show_posts(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ Sizga ruxsat yo'q!")
        return
        
    # Barcha aktiv postlarni olish
    posts = cursor.execute("SELECT id, photo, caption, post_time FROM active_posts WHERE status != 'deleted'").fetchall()
    
    if not posts:
        await message.answer("📭 Hozirda aktiv postlar yo'q.")
        return
        
    await message.answer(f"📋 Jami {len(posts)} ta aktiv post mavjud:")
    
    # Har bir postni ko'rsatish
    for post in posts:
        post_id, photo, caption, post_time = post
        
        # Inline tugmalar
        inline_kb = InlineKeyboardMarkup(row_width=2)
        delete_btn = InlineKeyboardButton("🗑 O'chirish", callback_data=f"delete:{post_id}")
        update_time_btn = InlineKeyboardButton("🕒 Vaqtni yangilash", callback_data=f"update_time:{post_id}")
        new_time = InlineKeyboardButton("Yangi vaqt qoshish", callback_data=f"new_time:{post_id}")
        inline_kb.add(delete_btn, update_time_btn, new_time)
        
        # Postni yuborish
        try:
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=photo,
                caption=f"📝 Post #{post_id}\n"
                        f"⏰ Vaqt: {post_time}\n\n"
                        f"{caption}",
                reply_markup=inline_kb
            )
        except Exception as e:
            # Agar rasm bilan xatolik bo'lsa, matn sifatida yuborish
            await message.answer(
                f"📝 Post #{post_id}\n"
                f"⏰ Vaqt: {post_time}\n\n"
                f"{caption}",
                reply_markup=inline_kb
            )

@dp.callback_query_handler(lambda c: c.data.startswith('new_time:'))
async def process_new_time(callback_query: types.CallbackQuery, state: FSMContext):
    post_id = int(callback_query.data.split(':')[1])
    
    # Post ID'ni state'ga saqlash
    await state.update_data(post_id=post_id)
    
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        f"⏰ Post #{post_id} uchun yangi vaqtni kiriting (HH:MM formatida, masalan: 00:01):"
    )
    
    # Vaqt kutish holatiga o'tish
    await UpdateTimeState.waiting_for_new_time.set()

@dp.message_handler(state=UpdateTimeState.waiting_for_new_time)
async def add_new_post_time(message: types.Message, state: FSMContext):
    time_text = message.text
    if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', time_text):
        await message.answer("⚠️ Noto'g'ri vaqt formati. Iltimos, vaqtni HH:MM formatida kiriting (masalan: 00:01):")
        return
    
    data = await state.get_data()
    post_id = data.get("post_id")
    post_times = get_post_times(post_id)
    post_times.append(time_text)

    updated_times = ",".join(post_times)
    updateting_post_time(post_id, updated_times)
    
    await message.answer(f"✅ Post #{post_id} vaqtlari {', '.join(post_times)} ga yangilandi!")

    
    # Holatni tozalash
    await state.finish()
    


# Callback query handler - postni o'chirish
@dp.callback_query_handler(lambda c: c.data.startswith('delete:'))
async def process_delete_post(callback_query: types.CallbackQuery):
    post_id = int(callback_query.data.split(':')[1])
    
    # Postni o'chirish (statusini o'zgartirish)
    cursor.execute("UPDATE active_posts SET status = 'deleted' WHERE id = ?", (post_id,))
    connect.commit()
    
    await bot.answer_callback_query(callback_query.id, text=f"Post #{post_id} o'chirildi!")
    
    # Xabarni yangilash
    await bot.edit_message_caption(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        caption=f"🗑 POST #{post_id} O'CHIRILDI!",
        reply_markup=None
    )

# Callback query handler - vaqtni yangilash
@dp.callback_query_handler(lambda c: c.data.startswith('update_time:'))
async def process_update_time(callback_query: types.CallbackQuery, state: FSMContext):
    post_id = int(callback_query.data.split(':')[1])
    
    # Post ID'ni state'ga saqlash
    await state.update_data(post_id=post_id)
    
    data = await state.get_data()
    post_id = data.get("post_id")
    post_times = get_post_times(post_id)
    update_times_btn = InlineKeyboardMarkup(row_width=3)  # 3 ta tugma bir qatorda
    
    # Har bir vaqt uchun tugma qo'shamiz
    for time in post_times:
        button = InlineKeyboardButton(text=time, callback_data=f"time_{post_id}_{time}")
        update_times_btn.add(button)
    update_times_btn.add(InlineKeyboardButton("Bosh menyu", callback_data="main_menu"))
    
    await callback_query.message.answer(f"⏰ Post #{post_id} uchun qaysi vaqtni o'zgartirmoqchisz ?", reply_markup=update_times_btn)
    
    # Vaqt kutish holatiga o'tish
    




@dp.callback_query_handler(lambda c: c.data.startswith('time_'))
async def process_update_time(callback_query: types.CallbackQuery, state: FSMContext):
    time = callback_query.data.split('_')[-1]
    post_id = callback_query.data.split('_')[1]
   
    post_times = get_post_times(post_id)
    
    
    post_times.remove(time)
    
    updated_times = ",".join(post_times)
    updateting_post_time(post_id, updated_times)
    new_times_btn = InlineKeyboardMarkup(row_width=1)  # 3 ta tugma bir qatorda
    # Har bir vaqt uchun tugma qo'shamiz
    await bot.answer_callback_query(callback_query.id, text=f"Post #{post_id} uchun vaqt {time} o'chirildi!")
    
    for a in post_times:
        button = InlineKeyboardButton(text=a, callback_data=f"time_{post_id}_{a}")
        new_times_btn.add(button)
    new_times_btn.add(InlineKeyboardButton("Bosh menyu", callback_data="main_menu"))
    
    await callback_query.message.edit_reply_markup(reply_markup=new_times_btn)
    # Holatni tozalash

@dp.callback_query_handler(lambda c: c.data == "main_menu")
async def main_menu(callback_query: types.CallbackQuery):
    await callback_query.message.delete()
    await bot.send_message(callback_query.from_user.id, "Bosh menyu", reply_markup=btn_start)

# 📮 Post jo'natish tugmasi bosilganda
@dp.message_handler(lambda message: message.text == "📮Post jo`natish")
async def ask_for_post_photo(message: types.Message):
    if message.from_user.id in ADMINS:
        await message.answer("📤 Iltimos, post uchun rasm yuboring:", reply_markup=btn_cancel)
        await PostState.photo.set()
    else:
        await message.answer("❌ Sizga ruxsat yo'q!")

# 🧾 Elon qo'shish tugmasi bosilganda
@dp.message_handler(lambda message: message.text == "🧾Elon qo`shish")
async def ask_for_elon_photo(message: types.Message):
    if message.from_user.id in ADMINS:
        await message.answer("📤 Iltimos, e'lon uchun rasm yuboring:", reply_markup=btn_cancel)
        await ElonState.photo.set()
    else:
        await message.answer("❌ Sizga ruxsat yo'q!")

# ❌ Bekor qilish tugmasi bosilganda
@dp.message_handler(lambda message: message.text == "❌ Bekor qilish", state="*")
async def cancel_post(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("🚫 Amal bekor qilindi.", reply_markup=btn_start)

# Post uchun rasmni qabul qilish
@dp.message_handler(content_types=types.ContentType.PHOTO, state=PostState.photo)
async def get_post_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo=photo_id)
    await message.answer("✍️ Endi rasm uchun izoh (caption) yuboring:", reply_markup=btn_cancel)
    await PostState.caption.set()

# Post uchun captionni qabul qilish va jo'natish
@dp.message_handler(state=PostState.caption)
async def get_post_caption(message: types.Message, state: FSMContext):
    caption = message.text
    data = await state.get_data()
    photo_id = data.get("photo")

    # Bazadan barcha guruhlarni olish
    groups = cursor.execute("SELECT group_id, group_name, joined_date FROM active_groups").fetchall()

    if groups:
        sent_count = 0
        for group in groups:
            group_id, group_name, joined_date = group
            try:
                await bot.send_photo(chat_id=group_id, photo=photo_id, caption=caption)
                sent_count += 1
            except Exception as e:
                print(f"⚠️ {group_name} ({group_id}) ga jo'natib bo'lmadi: {e}")

        await message.answer(f"📢 {sent_count} ta guruhga rasm bilan post jo'natildi!", reply_markup=btn_start)
    else:
        await message.answer("❌ Hech qanday aktiv guruh topilmadi.", reply_markup=btn_start)

    await state.finish()

# E'lon uchun rasmni qabul qilish
@dp.message_handler(content_types=types.ContentType.PHOTO, state=ElonState.photo)
async def get_elon_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo=photo_id)
    await message.answer("✍️ Endi e'lon uchun izoh (caption) yuboring:", reply_markup=btn_cancel)
    await ElonState.caption.set()

# E'lon uchun captionni qabul qilish
@dp.message_handler(state=ElonState.caption)
async def get_elon_caption(message: types.Message, state: FSMContext):
    caption = message.text
    await state.update_data(caption=caption)
    
    await message.answer("⏰ E'lonni har kuni yuborish vaqtini kiriting (HH:MM formatida, masalan: 00:01):", reply_markup=btn_cancel)
    await ElonState.time.set()

# E'lon uchun vaqtni qabul qilish va jo'natish
@dp.message_handler(state=ElonState.time)
async def get_elon_time(message: types.Message, state: FSMContext):
    time_text = message.text
    
    # Vaqt formatini tekshirish
    import re
    if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', time_text) and time_text != "❌ Bekor qilish":
        await message.answer("⚠️ Noto'g'ri vaqt formati. Iltimos, vaqtni HH:MM formatida kiriting (masalan: 00:01):", reply_markup=btn_cancel)
        return
    
    # State'dan ma'lumotlarni olish
    data = await state.get_data()
    photo_id = data.get("photo")
    caption = data.get("caption")
    
    # Database.py dagi funksiyani chaqirish
    add_post(photo_id, caption, time_text)
    
    # Bazadan ohirgi qo'shilgan ID olish
    post_id = cursor.lastrowid
    
    await message.answer(
        f"✅ E'lon saqlandi!\n"
        f"🕒 Har kuni soat {time_text} da yuboriladi.\n"
        f"📝 E'lon ID: {post_id}", 
        reply_markup=btn_start
    )
    
    await state.finish()

# Matn xabarlarni ham qabul qilish (Post uchun)
@dp.message_handler(state=PostState.photo, content_types=types.ContentType.TEXT)
async def text_instead_of_photo_post(message: types.Message, state: FSMContext):
    text = message.text
    if text != "❌ Bekor qilish":  # Agar "Bekor qilish" bo'lmasa
        # Bazadan barcha guruhlarni olish
        groups = cursor.execute("SELECT group_id, group_name, joined_date FROM active_groups").fetchall()

        if groups:
            sent_count = 0
            for group in groups:
                group_id, group_name, joined_date = group
                try:
                    await bot.send_message(chat_id=group_id, text=text)
                    sent_count += 1
                except Exception as e:
                    print(f"⚠️ {group_name} ({group_id}) ga jo'natib bo'lmadi: {e}")

            await message.answer(f"📢 {sent_count} ta guruhga matnli post jo'natildi!", reply_markup=btn_start)
        else:
            await message.answer("❌ Hech qanday aktiv guruh topilmadi.", reply_markup=btn_start)

        await state.finish()

# Matn xabarlarni ham qabul qilish (E'lon uchun)
@dp.message_handler(state=ElonState.photo, content_types=types.ContentType.TEXT)
async def text_instead_of_photo_elon(message: types.Message, state: FSMContext):
    text = message.text
    if text != "❌ Bekor qilish":  # Agar "Bekor qilish" bo'lmasa
        # Text saqlanadi va caption so'raladi
        await state.update_data(is_text_only=True, text=text)
        await message.answer("✍️ Endi qo'shimcha izoh kiriting yoki '⏭ O'tkazish' deb yozing:", reply_markup=btn_cancel)
        await ElonState.caption.set()



# Vaqt bo'yicha e'lonlarni yuborish
async def send_scheduled_posts():
    current_time = datetime.now().strftime("%H:%M")
    
    # Hozirgi vaqtga to'g'ri keladigan e'lonlarni olish (database.py dan)
    scheduled_posts = cursor.execute(
        "SELECT id, photo, caption, post_time, status FROM active_posts WHERE post_time LIKE ? AND status = 'active'",
        (current_time,)
    ).fetchall()
    
    if scheduled_posts:
        # Barcha guruhlarni olish
        groups = cursor.execute("SELECT group_id, group_name FROM active_groups").fetchall()
        
        if groups:
            for post in scheduled_posts:
                # To'g'ri indekslar bilan elementlarni olish
                post_id = post[0]
                photo = post[1]
                caption = post[2]
                
                sent_count = 0
                for group in groups:
                    group_id, group_name = group
                    try:
                        await bot.send_photo(chat_id=group_id, photo=photo, caption=caption)
                        sent_count += 1
                    except Exception as e:
                        print(f"⚠️ {group_name} ({group_id}) ga {post_id} e'lonni jo'natib bo'lmadi: {e}")
                
                print(f"📊 E'lon #{post_id} {sent_count} ta guruhga yuborildi")
                
                # Postni yuborilgan deb belgilash
                mark_post_as_sent(post_id)
    
# Vaqt bo'yicha ishlaydigan scheduler
async def scheduler():
    while True:
        await send_scheduled_posts()
        # Har daqiqada bir marta tekshirish
        await asyncio.sleep(60)

# Bot guruhga qo'shilganda bazaga yozish
@dp.message_handler(content_types=types.ContentType.NEW_CHAT_MEMBERS)
async def join_group(message: types.Message):
    bot_info = await bot.get_me()
    for new_member in message.new_chat_members:
        if new_member.id == bot_info.id:
            group_id = str(message.chat.id)
            group_name = message.chat.title
            joined_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Hozirgi vaqtni olish

            # Guruh bor yoki yo'qligini tekshirish
            select = cursor.execute("SELECT group_id FROM active_groups WHERE group_id=?", (group_id,)).fetchone()
            
            if select:
                cursor.execute("UPDATE active_groups SET group_name=?, joined_date=? WHERE group_id=?", 
                               (group_name, joined_date, group_id))
                await message.answer(f"♻️ Guruh yangilandi: {group_name}")
            else:
                cursor.execute("INSERT INTO active_groups (group_id, group_name, joined_date) VALUES (?, ?, ?)",
                               (group_id, group_name, joined_date))
                await message.answer(f"✅ Guruh bazaga qo'shildi: {group_name}")

            connect.commit()

# Botni ishga tushirish
async def on_startup(_):
    asyncio.create_task(scheduler())
    print("Bot va scheduler ishga tushdi!")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)