"""
Profile management module for candidate profiles
"""
import json
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from validators import parse_salary_string, parse_list_input, calculate_target_end_date, validate_superpowers
from keyboards import *
from db import save_profile, get_profile, delete_profile

class ProfileStates(StatesGroup):
    # Required fields
    role = State()
    current_location = State()
    target_location = State()
    level = State()
    level_custom = State()
    deadline_weeks = State()
    
    # Optional fields
    role_synonyms = State()
    salary = State()
    company_types = State()
    company_custom = State()
    industries = State()
    competencies = State()
    superpowers = State()
    constraints = State()
    
    # Review and edit
    final_review = State()
    edit_field = State()

def format_profile_display(profile_data: dict) -> str:
    """Format profile for display in chat"""
    if not profile_data:
        return "Профиль не найден"
    
    # Basic info section
    result = ["📋 ВАШ ПРОФИЛЬ", ""]
    result.append("🎯 ОСНОВНАЯ ИНФОРМАЦИЯ")
    result.append("-" * 40)
    result.append(f"Роль: {profile_data['role']}")
    result.append(f"Уровень: {profile_data['level']}")
    result.append(f"Текущая локация: {profile_data['current_location']}")
    result.append(f"Локация поиска: {profile_data['target_location']}")
    result.append(f"Срок поиска: {profile_data['deadline_weeks']} недель")
    result.append(f"Дедлайн: {profile_data['target_end_date']}")
    result.append("")
    
    # Optional fields
    if profile_data.get('role_synonyms_json'):
        synonyms = json.loads(profile_data['role_synonyms_json'])
        if synonyms:
            result.append("📝 СИНОНИМЫ РОЛЕЙ")
            result.append("-" * 40)
            result.append(", ".join(synonyms))
            result.append("")
    
    if profile_data.get('salary_min') and profile_data.get('salary_max'):
        result.append("💰 ЗАРПЛАТНЫЕ ОЖИДАНИЯ")
        result.append("-" * 40)
        salary_text = f"{profile_data['salary_min']:.0f}-{profile_data['salary_max']:.0f} {profile_data['salary_currency']}/{profile_data['salary_period']}"
        result.append(salary_text)
        result.append("")
    
    if profile_data.get('company_types_json'):
        company_types = json.loads(profile_data['company_types_json'])
        if company_types:
            result.append("🏢 ТИПЫ КОМПАНИЙ")
            result.append("-" * 40)
            result.append(", ".join(company_types))
            result.append("")
    
    if profile_data.get('industries_json'):
        industries = json.loads(profile_data['industries_json'])
        if industries:
            result.append("🔧 ИНДУСТРИИ")
            result.append("-" * 40)
            result.append(", ".join(industries))
            result.append("")
    
    if profile_data.get('competencies_json'):
        competencies = json.loads(profile_data['competencies_json'])
        if competencies:
            result.append("⚡ КЛЮЧЕВЫЕ КОМПЕТЕНЦИИ")
            result.append("-" * 40)
            result.append(", ".join(competencies))
            result.append("")
    
    if profile_data.get('superpowers_json'):
        superpowers = json.loads(profile_data['superpowers_json'])
        if superpowers:
            result.append("🚀 КАРТА СУПЕРСИЛ")
            result.append("-" * 40)
            for i, power in enumerate(superpowers, 1):
                result.append(f"{i}. {power}")
            result.append("")
    
    if profile_data.get('constraints_text'):
        result.append("⚠️ ДОПОЛНИТЕЛЬНЫЕ ОГРАНИЧЕНИЯ")
        result.append("-" * 40)
        result.append(profile_data['constraints_text'])
        result.append("")
    
    result.append(f"Создан: {profile_data['created_at'][:10]}")
    result.append(f"Обновлен: {profile_data['updated_at'][:10]}")
    
    return "\n".join(result)

async def start_profile_setup(message: types.Message, state: FSMContext):
    """Start profile setup wizard"""
    await state.finish()  # Clear any existing state
    
    welcome_text = """
📋 Мастер создания профиля кандидата

Этот профиль поможет анализировать вашу воронку поиска работы и будет использоваться для персонализированных рекомендаций.

🔒 Конфиденциальность: Ваш профиль доступен только вам и никому не передается.

Сейчас мы пройдем по основным полям. Обязательные поля отмечены *, остальные можно пропустить.

Начнем с вашей роли*:
"""
    
    await message.answer(welcome_text, reply_markup=get_back_keyboard())
    await ProfileStates.role.set()

async def process_role(message: types.Message, state: FSMContext):
    """Process role input"""
    role = message.text.strip()
    
    if not role or len(role) < 1 or len(role) > 100:
        await message.answer("Роль должна содержать от 1 до 100 символов. Попробуйте еще раз:")
        return
    
    await state.update_data(role=role)
    await message.answer("Отлично! Теперь укажите вашу текущую локацию*:")
    await ProfileStates.current_location.set()

async def process_current_location(message: types.Message, state: FSMContext):
    """Process current location"""
    location = message.text.strip()
    
    if not location or len(location) < 1 or len(location) > 100:
        await message.answer("Локация должна содержать от 1 до 100 символов. Попробуйте еще раз:")
        return
    
    await state.update_data(current_location=location)
    await message.answer("Теперь укажите локацию, где ищете работу*:")
    await ProfileStates.target_location.set()

async def process_target_location(message: types.Message, state: FSMContext):
    """Process target location"""
    location = message.text.strip()
    
    if not location or len(location) < 1 or len(location) > 100:
        await message.answer("Локация должна содержать от 1 до 100 символов. Попробуйте еще раз:")
        return
    
    await state.update_data(target_location=location)
    await message.answer("Выберите ваш уровень*:", reply_markup=get_level_keyboard())
    await ProfileStates.level.set()

async def process_deadline_weeks(message: types.Message, state: FSMContext):
    """Process deadline in weeks"""
    try:
        weeks = int(message.text.strip())
        if weeks < 1 or weeks > 52:
            await message.answer("Срок должен быть от 1 до 52 недель. Попробуйте еще раз:")
            return
    except ValueError:
        await message.answer("Введите число недель (1-52):")
        return
    
    target_end_date = calculate_target_end_date(weeks)
    await state.update_data(deadline_weeks=weeks, target_end_date=target_end_date)
    
    await message.answer(
        f"Отлично! Дедлайн установлен на {target_end_date}\n\n"
        "Теперь необязательные поля. Укажите синонимы вашей роли (до 4, через запятую):",
        reply_markup=get_skip_back_keyboard()
    )
    await ProfileStates.role_synonyms.set()

async def show_final_review(state: FSMContext):
    """Show final review before saving"""
    data = await state.get_data()
    
    review_text = ["📋 ФИНАЛЬНЫЙ ПРОСМОТР ПРОФИЛЯ", ""]
    review_text.append(f"Роль: {data['role']}")
    review_text.append(f"Уровень: {data['level']}")
    review_text.append(f"Текущая локация: {data['current_location']}")
    review_text.append(f"Локация поиска: {data['target_location']}")
    review_text.append(f"Срок: {data['deadline_weeks']} недель (до {data['target_end_date']})")
    
    if data.get('role_synonyms'):
        review_text.append(f"Синонимы ролей: {', '.join(data['role_synonyms'])}")
    
    if data.get('salary_info'):
        sal = data['salary_info']
        review_text.append(f"Зарплата: {sal['min_salary']:.0f}-{sal['max_salary']:.0f} {sal['currency']}/{sal['period']}")
    
    if data.get('company_types'):
        review_text.append(f"Типы компаний: {', '.join(data['company_types'])}")
    
    if data.get('industries'):
        review_text.append(f"Индустрии: {', '.join(data['industries'])}")
    
    if data.get('competencies'):
        review_text.append(f"Компетенции: {', '.join(data['competencies'])}")
    
    if data.get('superpowers'):
        review_text.append("Суперсилы:")
        for i, power in enumerate(data['superpowers'], 1):
            review_text.append(f"  {i}. {power}")
    
    if data.get('constraints_text'):
        review_text.append(f"Ограничения: {data['constraints_text']}")
    
    return "\n".join(review_text)

def prepare_profile_data(state_data: dict, user_id: int) -> dict:
    """Prepare profile data for database storage"""
    profile_data = {
        'role': state_data['role'],
        'current_location': state_data['current_location'],
        'target_location': state_data['target_location'],
        'level': state_data['level'],
        'deadline_weeks': state_data['deadline_weeks'],
        'target_end_date': state_data['target_end_date']
    }
    
    # Optional fields as JSON
    if state_data.get('role_synonyms'):
        profile_data['role_synonyms_json'] = json.dumps(state_data['role_synonyms'])
    
    if state_data.get('salary_info'):
        sal = state_data['salary_info']
        profile_data['salary_min'] = sal['min_salary']
        profile_data['salary_max'] = sal['max_salary']
        profile_data['salary_currency'] = sal['currency']
        profile_data['salary_period'] = sal['period']
    
    if state_data.get('company_types'):
        profile_data['company_types_json'] = json.dumps(state_data['company_types'])
    
    if state_data.get('industries'):
        profile_data['industries_json'] = json.dumps(state_data['industries'])
    
    if state_data.get('competencies'):
        profile_data['competencies_json'] = json.dumps(state_data['competencies'])
    
    if state_data.get('superpowers'):
        profile_data['superpowers_json'] = json.dumps(state_data['superpowers'])
    
    if state_data.get('constraints_text'):
        profile_data['constraints_text'] = state_data['constraints_text']
    
    return profile_data