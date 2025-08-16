"""
Integration module for PRD v3 reflection forms
Connects reflection system to existing week data input handlers
"""

from aiogram import types
from aiogram.fsm.context import FSMContext
from reflection_forms import ReflectionTrigger

async def handle_week_data_with_reflection_check(message: types.Message, user_id: int, 
                                               week_start: str, channel: str, funnel_type: str,
                                               new_data: dict, state: FSMContext = None):
    """
    Enhanced week data handler that checks for reflection triggers
    This should be called after week data is successfully added
    """
    from db import add_week_data
    
    # Add data and get old/new values for trigger checking
    old_data, updated_data = add_week_data(user_id, week_start, channel, funnel_type, new_data, check_triggers=True)
    
    if old_data is None:
        # No trigger checking was done
        return
    
    # Check for reflection triggers
    triggers = ReflectionTrigger.check_triggers(user_id, week_start, channel, funnel_type, old_data, updated_data)
    
    if triggers:
        # Offer reflection form to user
        await ReflectionTrigger.offer_reflection_form(
            message, user_id, week_start, channel, funnel_type, triggers
        )

def register_reflection_handlers(dp):
    """Register all reflection form handlers with dispatcher - aiogram v3 style"""
    from reflection_forms import (
        handle_reflection_yes, handle_reflection_no,
        cmd_log_event, cmd_pending_forms, cmd_last_events, ReflectionStates
    )
    from reflection_handlers import (
        process_stage_type, process_rating, process_strengths, process_weaknesses,
        process_mood_rating, process_rejection_reason, process_rejection_other,
        handle_continue_forms, handle_stop_forms, handle_skip_form, handle_cancel_form
    )
    from aiogram.filters import Command, StateFilter
    from aiogram import F
    
    # Callback handlers for reflection triggers - aiogram v3 style
    @dp.callback_query(F.data.startswith("reflection_yes_"))
    async def _handle_reflection_yes(callback: types.CallbackQuery, state: FSMContext):
        await handle_reflection_yes(callback, state)
        
    @dp.callback_query(F.data == "reflection_no")
    async def _handle_reflection_no(callback: types.CallbackQuery):
        await handle_reflection_no(callback)
    
    @dp.callback_query(F.data.startswith("stage_"))
    async def _process_stage_type(callback: types.CallbackQuery, state: FSMContext):
        await process_stage_type(callback, state)
    
    @dp.callback_query(F.data.startswith("rating_"))
    async def _process_rating(callback: types.CallbackQuery, state: FSMContext):
        await process_rating(callback, state)
    
    @dp.callback_query(F.data.startswith("reason_"))
    async def _process_rejection_reason(callback: types.CallbackQuery, state: FSMContext):
        await process_rejection_reason(callback, state)
        
    @dp.callback_query(F.data == "reasons_done")
    async def _process_reasons_done(callback: types.CallbackQuery, state: FSMContext):
        await process_rejection_reason(callback, state)
        
    @dp.callback_query(F.data == "continue_forms")
    async def _handle_continue_forms(callback: types.CallbackQuery, state: FSMContext):
        await handle_continue_forms(callback, state)
        
    @dp.callback_query(F.data == "stop_forms")
    async def _handle_stop_forms(callback: types.CallbackQuery):
        await handle_stop_forms(callback)
        
    @dp.callback_query(F.data == "skip_form")
    async def _handle_skip_form(callback: types.CallbackQuery, state: FSMContext):
        await handle_skip_form(callback, state)
        
    @dp.callback_query(F.data == "cancel_form")
    async def _handle_cancel_form(callback: types.CallbackQuery, state: FSMContext):
        await handle_cancel_form(callback, state)
    
    # Text message handlers for reflection states - aiogram v3 style
    @dp.message(ReflectionStates.strengths, F.text)
    async def _process_strengths(message: types.Message, state: FSMContext):
        await process_strengths(message, state)
        
    @dp.message(ReflectionStates.weaknesses, F.text)
    async def _process_weaknesses(message: types.Message, state: FSMContext):
        await process_weaknesses(message, state)
        
    @dp.message(ReflectionStates.rejection_other, F.text)
    async def _process_rejection_other(message: types.Message, state: FSMContext):
        await process_rejection_other(message, state)
    
    # Commands - aiogram v3 style
    @dp.message(Command("log_event"))
    async def _cmd_log_event(message: types.Message, state: FSMContext):
        await cmd_log_event(message, state)
        
    @dp.message(Command("pending_forms"))
    async def _cmd_pending_forms(message: types.Message, state: FSMContext):
        await cmd_pending_forms(message, state)
        
    @dp.message(Command("last_events"))
    async def _cmd_last_events(message: types.Message):
        await cmd_last_events(message)

# Helper function to modify existing handlers
def modify_existing_week_data_handler(original_handler):
    """
    Decorator to modify existing week data handlers to include reflection checking
    """
    async def wrapper(*args, **kwargs):
        result = await original_handler(*args, **kwargs)
        
        # Extract parameters for reflection checking
        if len(args) >= 1:
            message = args[0]
            if hasattr(message, 'from_user'):
                user_id = message.from_user.id
                # Additional logic to extract week_start, channel, funnel_type, data
                # would need to be implemented based on the specific handler structure
        
        return result
    
    return wrapper