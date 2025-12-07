import logging
import random
import time
import uuid
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Log konfiguratsiyasi
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8355780408:AAHEpjwoZMQRH0_mkd7U8S-ACY9FniWf-00"

# Ma'lumotlar bazasi
tests_db = {}          # {test_id: test_data}
active_sessions = {}   # {user_id: session_data}
user_states = {}       # {user_id: state_data}

# ==================== MENU YARATISH ====================

def get_main_menu():
    """Asosiy menu"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("📝 Savol qo'shish"), KeyboardButton("📋 Mening savollarim")],
        [KeyboardButton("🎯 Test yaratish"), KeyboardButton("📊 Mening testlarim")],
        [KeyboardButton("🆘 Yordam")]
    ], resize_keyboard=True)

def get_back_menu():
    """Orqaga menu"""
    return ReplyKeyboardMarkup([[KeyboardButton("⬅️ Orqaga")]], resize_keyboard=True)

# ==================== ASOSIY FUNKSIYALAR ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Boshlash komandasi"""
    user = update.effective_user
    
    # Foydalanuvchi holatini tozalash
    user_id = user.id
    if user_id in user_states:
        del user_states[user_id]
    
    await update.message.reply_text(
        f"👋 Assalomu alaykum {user.first_name}!\n\n"
        "🎯 **Test Maker Bot**\n\n"
        "📌 **QO'LLANMA:**\n"
        "1. '🎯 Test yaratish' ni tanlang\n"
        "2. Test nomini kiriting\n"
        "3. Savollarni qo'shing\n"
        "4. Test havolasini oling va tarqating\n\n"
        "⚡ **TEZKOR:** Bir nechta savolni bir vaqtda qo'shishingiz mumkin!",
        reply_markup=get_main_menu()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi xabarlarini qayta ishlash"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Menu tugmalarini tekshirish
    if text == "📝 Savol qo'shish":
        await add_questions_start(update, context)
    elif text == "📋 Mening savollarim":
        await my_questions_command(update, context)
    elif text == "🎯 Test yaratish":
        await create_test_start(update, context)
    elif text == "📊 Mening testlarim":
        await my_tests_command(update, context)
    elif text == "🆘 Yordam":
        await help_command(update, context)
    else:
        # Foydalanuvchi holatini tekshirish
        if user_id in user_states:
            state = user_states[user_id]
            
            if state['step'] == 'awaiting_test_name':
                await handle_test_name(update, context)
            elif state['step'] == 'awaiting_questions':
                await handle_test_questions(update, context)
            else:
                await update.message.reply_text(
                    "Iltimos, pastdagi menyudan biror tugmani tanlang.",
                    reply_markup=get_main_menu()
                )
        else:
            await update.message.reply_text(
                "Iltimos, pastdagi menyudan biror tugmani tanlang yoki /start buyrug'ini yuboring.",
                reply_markup=get_main_menu()
            )

# ==================== TEST YARATISH ====================

async def create_test_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test yaratishni boshlash"""
    user_id = update.effective_user.id
    
    # Yangi test holatini yaratish
    user_states[user_id] = {
        'step': 'awaiting_test_name',
        'test_data': {
            'name': '',
            'questions': [],
            'created_at': datetime.now().strftime("%d.%m.%Y %H:%M")
        }
    }
    
    await update.message.reply_text(
        "🎯 **YANGI TEST YARATISH**\n\n"
        "Iltimos, test nomini kiriting:\n\n"
        "📌 **MISOLLAR:**\n"
        "• Inglizcha So'zlar\n"
        "• Matematika Testi\n"
        "• Tarix Savollari\n"
        "• Geografiya Bilimlari",
        reply_markup=get_back_menu()
    )

async def handle_test_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test nomini qabul qilish"""
    user_id = update.effective_user.id
    test_name = update.message.text.strip()
    
    if test_name == "⬅️ Orqaga":
        # Holatni tozalash va asosiy menyuga qaytish
        if user_id in user_states:
            del user_states[user_id]
        await update.message.reply_text(
            "Test yaratish bekor qilindi.",
            reply_markup=get_main_menu()
        )
        return
    
    if not test_name:
        await update.message.reply_text("❌ Test nomi bo'sh bo'lishi mumkin emas!")
        return
    
    # Test nomini saqlash
    user_states[user_id]['test_data']['name'] = test_name
    user_states[user_id]['step'] = 'awaiting_questions'
    
    await update.message.reply_text(
        f"✅ **Test nomi qabul qilindi:** {test_name}\n\n"
        f"📝 **Endi savollarni kiriting:**\n\n"
        f"**FORMAT:** `Savol?|A|B|C|D`\n\n"
        f"**BIR NECHA SAVOL:**\n"
        f"```\n"
        f"2+2 necha?|4|5|6|7\n"
        f"3*3 necha?|9|8|7|6\n"
        f"O'zbekiston poytaxti?|Toshkent|Samarqand|Buxoro|Andijon\n"
        f"```\n\n"
        f"**ESLATMA:** Birinchi variant (A) to'g'ri javob hisoblanadi!\n\n"
        f"Savollaringizni yuboring..."
    )

async def handle_test_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test savollarini qabul qilish"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if text == "⬅️ Orqaga":
        # Holatni tozalash va asosiy menyuga qaytish
        if user_id in user_states:
            del user_states[user_id]
        await update.message.reply_text(
            "Test yaratish bekor qilindi.",
            reply_markup=get_main_menu()
        )
        return
    
    # Har bir qatorni alohida qabul qilish
    lines = text.split('\n')
    added_count = 0
    errors = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Formatni tekshirish
        if '|' not in line:
            errors.append(f"'{line[:30]}...' - Format noto'g'ri (| belgisi yo'q)")
            continue
        
        parts = [part.strip() for part in line.split('|')]
        
        if len(parts) != 5:
            errors.append(f"'{line[:30]}...' - {len(parts)} ta qism (5 ta bo'lishi kerak)")
            continue
        
        # Savol ma'lumotlarini tuzish
        question_data = {
            'text': parts[0],
            'options': parts[1:5],
            'correct_index': 0,
            'correct_answer': parts[1]
        }
        
        # Testga qo'shish
        user_states[user_id]['test_data']['questions'].append(question_data)
        added_count += 1
    
    # Natijani chiqarish
    test_data = user_states[user_id]['test_data']
    total_questions = len(test_data['questions'])
    
    if added_count > 0:
        if errors:
            error_text = "\n".join(errors[:3])
            await update.message.reply_text(
                f"✅ **{added_count} ta savol qo'shildi!**\n"
                f"📚 **Test:** {test_data['name']}\n"
                f"❌ **{len(errors)} ta xatolik:**\n{error_text}\n\n"
                f"📊 **Jami savollar:** {total_questions} ta\n\n"
                f"Yana savol qo'shishingiz yoki testni yakunlashingiz mumkin."
            )
        else:
            # Inline keyboard
            keyboard = [
                [InlineKeyboardButton("✅ Testni yakunlash", callback_data="finish_test")],
                [InlineKeyboardButton("➕ Yana savol qo'shish", callback_data="add_more")],
                [InlineKeyboardButton("⬅️ Orqaga", callback_data="cancel_test")]
            ]
            
            await update.message.reply_text(
                f"✅ **{added_count} ta savol qo'shildi!**\n\n"
                f"📚 **Test:** {test_data['name']}\n"
                f"📊 **Jami savollar:** {total_questions} ta\n\n"
                f"Yana savol qo'shish uchun formatda yuboring yoki testni yakunlang:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    else:
        error_text = "\n".join(errors[:5]) if errors else "Format noto'g'ri"
        await update.message.reply_text(
            f"❌ **Hech qanday savol qo'shilmadi!**\n\n"
            f"📋 **Xatolar:**\n{error_text}\n\n"
            f"📌 **To'g'ri format:** `Savol?|A|B|C|D`\n\n"
            f"📝 **Misol:**\n"
            f"```\n"
            f"2+2 necha?|4|5|6|7\n"
            f"3*3 necha?|9|8|7|6\n"
            f"```"
        )

# ==================== CALLBACK HANDLER ====================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callbacklarni qayta ishlash"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "finish_test":
        await finish_test_creation(query, context)
    elif data == "add_more":
        await query.edit_message_text(
            "➕ **YANA SAVOL QO'SHISH**\n\n"
            "Savollarni formatda yuboring:\n"
            "`Savol?|A|B|C|D`\n\n"
            "Bir nechta savol:\n"
            "```\n"
            "Savol1?|A1|B1|C1|D1\n"
            "Savol2?|A2|B2|C2|D2\n"
            "```"
        )
    elif data == "cancel_test":
        # Holatni tozalash
        if user_id in user_states:
            del user_states[user_id]
        await query.edit_message_text(
            "Test yaratish bekor qilindi.",
            reply_markup=get_main_menu()
        )
    elif data.startswith("showres_"):
        # Natijalarni ko'rsatish
        test_id = data.replace("showres_", "")
        await show_results_callback(query, context, test_id)

async def finish_test_creation(query, context):
    """Testni yakunlash"""
    user_id = query.from_user.id
    
    if user_id not in user_states or 'test_data' not in user_states[user_id]:
        await query.edit_message_text("❌ Test ma'lumotlari topilmadi.")
        return
    
    test_data = user_states[user_id]['test_data']
    
    if len(test_data['questions']) == 0:
        await query.edit_message_text("❌ Testda hech qanday savol yo'q!")
        return
    
    # Test ID yaratish
    test_id = str(uuid.uuid4())[:8].lower()
    
    # Variantlarni aralashtirish
    for question in test_data['questions']:
        correct_answer = question['options'][question['correct_index']]
        random.shuffle(question['options'])
        question['correct_index'] = question['options'].index(correct_answer)
    
    # Testni saqlash
    tests_db[test_id] = {
        'id': test_id,
        'creator': user_id,
        'creator_name': query.from_user.full_name,
        'name': test_data['name'],
        'questions': test_data['questions'].copy(),
        'created_at': test_data['created_at'],
        'participants': {}
    }
    
    # Bot username ni olish
    try:
        bot_username = (await context.bot.get_me()).username
    except:
        bot_username = "your_bot_username"
    
    # Test havolasi
    test_link = f"https://t.me/{bot_username}?start={test_id}"
    
    # Holatni tozalash
    if user_id in user_states:
        del user_states[user_id]
    
    # Inline tugmalar
    keyboard = [
        [InlineKeyboardButton("🔗 Test havolasi", url=test_link)],
        [InlineKeyboardButton("📊 Natijalar", callback_data=f"showres_{test_id}")]
    ]
    
    await query.edit_message_text(
        f"🎉 **TEST MUVAFFAQIYATLI YARATILDI!**\n\n"
        f"📚 **Test nomi:** {test_data['name']}\n"
        f"📊 **Savollar soni:** {len(test_data['questions'])} ta\n"
        f"👨‍🏫 **Yaratuvchi:** {query.from_user.full_name}\n"
        f"🕐 **Yaratilgan:** {test_data['created_at']}\n\n"
        f"🔗 **TEST HAVOLASI:**\n"
        f"{test_link}\n\n"
        f"📌 **BU HAVOLANI DO'STLARINGIZGA YUBORING**\n\n"
        f"📈 **Natijalarni ko'rish:** `/results_{test_id}`",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_results_callback(query, context, test_id):
    """Callback orqali natijalarni ko'rsatish"""
    user_id = query.from_user.id
    
    if test_id not in tests_db:
        await query.answer("❌ Test topilmadi.")
        return
    
    test = tests_db[test_id]
    
    if test['creator'] != user_id:
        await query.answer("❌ Faqat test yaratuvchi natijalarni ko'rishi mumkin.")
        return
    
    participants = test['participants']
    
    if not participants:
        await query.edit_message_text("📊 Hali hech kim testni yechmagan.")
        return
    
    total_participants = len(participants)
    total_questions = len(test['questions'])
    
    total_correct = sum(p['score'] for p in participants.values())
    total_possible = total_participants * total_questions
    overall_percentage = (total_correct / total_possible * 100) if total_possible > 0 else 0
    
    result_text = f"📊 **TEST NATIJALARI**\n\n"
    result_text += f"📚 **Test:** {test['name']}\n"
    result_text += f"📅 **Yaratilgan:** {test['created_at']}\n"
    result_text += f"👥 **Ishtirokchilar:** {total_participants} ta\n"
    result_text += f"📈 **Umumiy to'g'ri javoblar:** {overall_percentage:.1f}%\n\n"
    
    result_text += "🏆 **ISHTIROKCHILAR REYTINGI:**\n\n"
    
    sorted_participants = sorted(
        participants.items(),
        key=lambda x: x[1]['percentage'],
        reverse=True
    )
    
    for rank, (user_id, data) in enumerate(sorted_participants[:10], 1):
        name = data.get('name', f'Foydalanuvchi {user_id}')
        
        if rank == 1:
            medal = "🥇"
        elif rank == 2:
            medal = "🥈"
        elif rank == 3:
            medal = "🥉"
        else:
            medal = f"{rank}."
        
        result_text += f"{medal} **{name}**\n"
        result_text += f"   ✅ {data['score']}/{total_questions} ({data['percentage']:.1f}%)\n"
        result_text += f"   ⏱️ {data['time']:.1f} soniya\n\n"
    
    await query.edit_message_text(result_text)

# ==================== MENYU FUNKSIYALARI ====================

async def add_questions_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Savol qo'shishni boshlash"""
    await update.message.reply_text(
        "📝 **SAVOL QO'SHISH**\n\n"
        "**Ushbu funksiya test yaratish uchun emas!**\n"
        "Test yaratish uchun '🎯 Test yaratish' tugmasini bosing.\n\n"
        "Agar mavjud testga savol qo'shmoqchi bo'lsangiz, iltimos '🎯 Test yaratish' orqali yangi test yarating.",
        reply_markup=get_main_menu()
    )

async def my_questions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi testlaridagi savollarni ko'rsatish"""
    user_id = update.effective_user.id
    
    # Foydalanuvchining testlarini topish
    user_tests = []
    for test_id, test in tests_db.items():
        if test['creator'] == user_id:
            user_tests.append(test)
    
    if not user_tests:
        await update.message.reply_text(
            "📭 **SAVOLLAR TOPILMADI!**\n\n"
            "Hali test yaratmagansiz. Test yaratish uchun '🎯 Test yaratish' tugmasini bosing.",
            reply_markup=get_main_menu()
        )
        return
    
    text = "📋 **SIZNING TESTLAR VA SAVOLLAR:**\n\n"
    
    for test in user_tests[:5]:
        text += f"📚 **{test['name']}**\n"
        text += f"📊 {len(test['questions'])} ta savol\n"
        text += f"🕐 {test['created_at']}\n"
        
        for i, q in enumerate(test['questions'][:3], 1):
            text += f"  {i}. {q['text'][:40]}...\n"
        
        text += f"🔗 Test ID: `{test['id']}`\n\n"
    
    if len(user_tests) > 5:
        text += f"📌 ... va yana {len(user_tests)-5} ta test\n\n"
    
    await update.message.reply_text(text, reply_markup=get_main_menu())

async def my_tests_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi testlarini ko'rsatish"""
    user_id = update.effective_user.id
    
    # Foydalanuvchining testlarini topish
    user_tests = []
    for test_id, test in tests_db.items():
        if test['creator'] == user_id:
            user_tests.append(test)
    
    if not user_tests:
        await update.message.reply_text(
            "📭 **TESTLAR TOPILMADI!**\n\n"
            "Hali test yaratmagansiz. Test yaratish uchun '🎯 Test yaratish' tugmasini bosing.",
            reply_markup=get_main_menu()
        )
        return
    
    user_tests.sort(key=lambda x: x['created_at'], reverse=True)
    
    text = f"📊 **SIZNING TESTLARINGIZ ({len(user_tests)} ta):**\n\n"
    
    for i, test in enumerate(user_tests[:10], 1):
        participants_count = len(test['participants'])
        
        try:
            bot_username = (await context.bot.get_me()).username
        except:
            bot_username = "your_bot_username"
        
        test_link = f"https://t.me/{bot_username}?start={test['id']}"
        
        text += f"**{i}. {test['name']}**\n"
        text += f"   🆔 ID: `{test['id']}`\n"
        text += f"   📅 {test['created_at']}\n"
        text += f"   ❓ {len(test['questions'])} ta savol\n"
        text += f"   👥 {participants_count} ta ishtirokchi\n"
        text += f"   🔗 {test_link}\n"
        text += f"   📊 `/results_{test['id']}`\n\n"
    
    if len(user_tests) > 10:
        text += f"📌 ... va yana {len(user_tests)-10} ta test\n\n"
    
    await update.message.reply_text(text, reply_markup=get_main_menu())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam"""
    await update.message.reply_text(
        "🆘 **YORDAM VA QO'LLANMA**\n\n"
        "🎯 **TEST YARATISH:**\n"
        "1. '🎯 Test yaratish' tugmasini bosing\n"
        "2. Test nomini kiriting\n"
        "3. Savollarni qo'shing\n"
        "4. Test havolasini oling va tarqating\n\n"
        "📝 **SAVOL FORMATI:**\n"
        "`Savol matni?|Variant A|Variant B|Variant C|Variant D`\n"
        "• Birinchi variant (A) to'g'ri javob\n"
        "• Bir nechta savol: har bir savol yangi qatorda\n\n"
        "📋 **MENYU TUGMALARI:**\n"
        "📝 Savol qo'shish - Yangi test yaratish uchun\n"
        "📋 Mening savollarim - Testlardagi savollarni ko'rish\n"
        "🎯 Test yaratish - Yangi test yaratish\n"
        "📊 Mening testlarim - Mening barcha testlarim\n"
        "🆘 Yordam - Bu yordam xabari\n\n"
        "❓ **MUAMMO BO'LSA:**\n"
        "1. Botni qayta ishga tushiring\n"
        "2. /start buyrug'ini yuboring\n"
        "3. Menyudan kerakli tugmani tanlang",
        reply_markup=get_main_menu()
    )

# ==================== TEST ISHTIROKCHISI FUNKSIYALARI ====================

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Testni boshlash (havola orqali)"""
    args = context.args
    
    if not args:
        return await start(update, context)
    
    test_id = args[0]
    user_id = update.effective_user.id
    
    if test_id not in tests_db:
        await update.message.reply_text(
            "❌ **TEST TOPILMADI!**",
            reply_markup=get_main_menu()
        )
        return
    
    test = tests_db[test_id]
    
    if user_id in test['participants']:
        user_result = test['participants'][user_id]
        await update.message.reply_text(
            f"ℹ️ **SIZ ALLAQACHON TESTNI YECHGANSIZ!**\n\n"
            f"📚 **Test:** {test['name']}\n"
            f"📊 **Sizning natijangiz:**\n"
            f"✅ To'g'ri javoblar: {user_result['score']}/{len(test['questions'])}\n"
            f"📈 Foiz: {user_result['percentage']:.1f}%\n"
            f"👨‍🏫 **Yaratuvchi:** {test['creator_name']}",
            reply_markup=get_main_menu()
        )
        return
    
    active_sessions[user_id] = {
        'test_id': test_id,
        'current_question': 0,
        'answers': [],
        'start_time': time.time(),
        'score': 0,
        'user_name': update.effective_user.full_name
    }
    
    await update.message.reply_text(
        f"🎯 **TEST BOSHLANMOQDA!**\n\n"
        f"📚 **Test:** {test['name']}\n"
        f"📊 **Savollar soni:** {len(test['questions'])} ta\n"
        f"👨‍🏫 **Yaratuvchi:** {test['creator_name']}\n"
        f"🕐 **Yaratilgan:** {test['created_at']}"
    )
    
    import asyncio
    await asyncio.sleep(1)
    await send_question(update, context, user_id)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Savolni yuborish"""
    session = active_sessions.get(user_id)
    if not session:
        return
    
    test_id = session['test_id']
    test = tests_db[test_id]
    
    question_num = session['current_question']
    
    if question_num >= len(test['questions']):
        await finish_test(update, context, user_id)
        return
    
    question = test['questions'][question_num]
    
    keyboard = []
    for i, option in enumerate(question['options']):
        display_text = option[:25] + "..." if len(option) > 25 else option
        keyboard.append([
            InlineKeyboardButton(
                f"{chr(65+i)}) {display_text}",
                callback_data=f"answer_{test_id}_{question_num}_{i}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    progress = f"{question_num + 1}/{len(test['questions'])}"
    
    await update.message.reply_text(
        f"❓ **SAVOL {progress}**\n\n"
        f"{question['text']}",
        reply_markup=reply_markup
    )

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Javobni qayta ishlash"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split('_')
    
    if len(parts) != 4:
        return
    
    test_id = parts[1]
    question_num = int(parts[2])
    answer_index = int(parts[3])
    
    user_id = query.from_user.id
    
    if user_id not in active_sessions:
        await query.edit_message_text("❌ Sessiya muddati tugagan.")
        return
    
    session = active_sessions[user_id]
    
    if session['test_id'] != test_id:
        await query.edit_message_text("❌ Sessiya xatosi.")
        return
    
    test = tests_db[test_id]
    question = test['questions'][question_num]
    
    is_correct = (answer_index == question['correct_index'])
    
    session['answers'].append({
        'question_num': question_num,
        'answer_index': answer_index,
        'is_correct': is_correct,
        'time': time.time() - session['start_time']
    })
    
    if is_correct:
        session['score'] += 1
    
    if is_correct:
        await query.edit_message_text("✅ **TO'G'RI JAVOB!**")
    else:
        correct_letter = chr(65 + question['correct_index'])
        correct_answer = question['options'][question['correct_index']]
        await query.edit_message_text(
            f"❌ **NOTO'G'RI JAVOB!**\n\n"
            f"✅ **To'g'ri javob:** {correct_letter}) {correct_answer}"
        )
    
    session['current_question'] += 1
    
    import asyncio
    await asyncio.sleep(1)
    
    if session['current_question'] < len(test['questions']):
        await send_next_question(query.message, context, user_id)
    else:
        await finish_test_from_callback(query.message, context, user_id)

async def send_next_question(message, context, user_id):
    """Keyingi savolni yuborish"""
    session = active_sessions[user_id]
    test_id = session['test_id']
    test = tests_db[test_id]
    
    question_num = session['current_question']
    question = test['questions'][question_num]
    
    keyboard = []
    for i, option in enumerate(question['options']):
        display_text = option[:25] + "..." if len(option) > 25 else option
        keyboard.append([
            InlineKeyboardButton(
                f"{chr(65+i)}) {display_text}",
                callback_data=f"answer_{test_id}_{question_num}_{i}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    progress = f"{question_num + 1}/{len(test['questions'])}"
    
    await message.reply_text(
        f"❓ **SAVOL {progress}**\n\n"
        f"{question['text']}",
        reply_markup=reply_markup
    )

async def finish_test(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Testni yakunlash"""
    session = active_sessions.get(user_id)
    if not session:
        return
    
    test_id = session['test_id']
    test = tests_db[test_id]
    
    score = session['score']
    total = len(test['questions'])
    percentage = (score / total) * 100 if total > 0 else 0
    time_taken = time.time() - session['start_time']
    
    test['participants'][user_id] = {
        'name': session['user_name'],
        'score': score,
        'total': total,
        'percentage': percentage,
        'answers': session['answers'],
        'time': time_taken,
        'timestamp': datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    }
    
    result_text = (
        f"🏆 **TEST YAKUNLANDI!**\n\n"
        f"📚 **Test:** {test['name']}\n"
        f"📊 **Sizning natijangiz:**\n"
        f"✅ To'g'ri javoblar: {score}/{total}\n"
        f"📈 Foiz: {percentage:.1f}%\n"
        f"⏱️ Vaqt: {time_taken:.1f} soniya\n\n"
        f"👨‍🏫 **Yaratuvchi:** {test['creator_name']}"
    )
    
    if percentage >= 90:
        result_text += "\n\n🎯 **TAHRIRIYA:** A'lo! 👏"
    elif percentage >= 70:
        result_text += "\n\n🎯 **TAHRIRIYA:** Yaxshi! 👍"
    elif percentage >= 50:
        result_text += "\n\n🎯 **TAHRIRIYA:** Qoniqarli! 🤔"
    else:
        result_text += "\n\n🎯 **TAHRIRIYA:** Yana urinib ko'ring! 💪"
    
    await update.message.reply_text(result_text, reply_markup=get_main_menu())
    
    if user_id in active_sessions:
        del active_sessions[user_id]

async def finish_test_from_callback(message, context, user_id):
    """Callback orqali testni yakunlash"""
    session = active_sessions.get(user_id)
    if not session:
        return
    
    test_id = session['test_id']
    test = tests_db[test_id]
    
    score = session['score']
    total = len(test['questions'])
    percentage = (score / total) * 100 if total > 0 else 0
    time_taken = time.time() - session['start_time']
    
    test['participants'][user_id] = {
        'name': session['user_name'],
        'score': score,
        'total': total,
        'percentage': percentage,
        'answers': session['answers'],
        'time': time_taken,
        'timestamp': datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    }
    
    result_text = (
        f"🏆 **TEST YAKUNLANDI!**\n\n"
        f"📊 **SIZNING NATIJANGIZ:**\n"
        f"✅ To'g'ri javoblar: {score}/{total}\n"
        f"📈 Foiz: {percentage:.1f}%\n"
        f"⏱️ Vaqt: {time_taken:.1f} soniya"
    )
    
    await message.reply_text(result_text)
    
    if user_id in active_sessions:
        del active_sessions[user_id]

async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Natijalarni ko'rsatish"""
    text = update.message.text
    
    if not text.startswith('/results_'):
        return
    
    test_id = text.replace('/results_', '')
    user_id = update.effective_user.id
    
    if test_id not in tests_db:
        await update.message.reply_text("❌ Test topilmadi.")
        return
    
    test = tests_db[test_id]
    
    if test['creator'] != user_id:
        await update.message.reply_text("❌ Faqat test yaratuvchi natijalarni ko'rishi mumkin.")
        return
    
    participants = test['participants']
    
    if not participants:
        await update.message.reply_text("📊 Hali hech kim testni yechmagan.")
        return
    
    total_participants = len(participants)
    total_questions = len(test['questions'])
    
    total_correct = sum(p['score'] for p in participants.values())
    total_possible = total_participants * total_questions
    overall_percentage = (total_correct / total_possible * 100) if total_possible > 0 else 0
    
    result_text = f"📊 **TEST NATIJALARI**\n\n"
    result_text += f"📚 **Test:** {test['name']}\n"
    result_text += f"📅 **Yaratilgan:** {test['created_at']}\n"
    result_text += f"👥 **Ishtirokchilar:** {total_participants} ta\n"
    result_text += f"📈 **Umumiy to'g'ri javoblar:** {overall_percentage:.1f}%\n\n"
    
    result_text += "🏆 **ISHTIROKCHILAR REYTINGI:**\n\n"
    
    sorted_participants = sorted(
        participants.items(),
        key=lambda x: x[1]['percentage'],
        reverse=True
    )
    
    for rank, (user_id, data) in enumerate(sorted_participants, 1):
        name = data.get('name', f'Foydalanuvchi {user_id}')
        
        if rank == 1:
            medal = "🥇"
        elif rank == 2:
            medal = "🥈"
        elif rank == 3:
            medal = "🥉"
        else:
            medal = f"{rank}."
        
        result_text += f"{medal} **{name}**\n"
        result_text += f"   ✅ {data['score']}/{total_questions} ({data['percentage']:.1f}%)\n"
        result_text += f"   ⏱️ {data['time']:.1f} soniya\n\n"
    
    await update.message.reply_text(result_text, reply_markup=get_main_menu())

# ==================== ASOSIY DASTUR ====================

def main():
    """Asosiy funksiya"""
    print("🤖 Menu Test Bot ishga tushmoqda...")
    
    try:
        application = Application.builder().token(TOKEN).build()
        print("✅ Bot yaratildi!")
        
    except Exception as e:
        print(f"❌ Xatolik: {e}")
        return
    
    # Handlerlar
    application.add_handler(CommandHandler("start", start_test))
    application.add_handler(CommandHandler("help", help_command))
    
    # Results handler
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^/results_.*'),
        show_results
    ))
    
    # Text message handler (menyu uchun)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    # Callback handler
    application.add_handler(CallbackQueryHandler(
        handle_callback,
        pattern=r"^(finish_test|add_more|cancel_test|showres_.*)"
    ))
    
    # Answer callback handler
    application.add_handler(CallbackQueryHandler(
        handle_answer,
        pattern=r"^answer_.*"
    ))
    
    print("✅ Bot muvaffaqiyatli ishga tushdi!")
    print("📱 Endi Telegramda botni oching va /start ni yuboring")
    
    application.run_polling()

if __name__ == '__main__':
    main()
