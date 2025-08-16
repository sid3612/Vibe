"""
Integration module for PRD v3 reflection forms
Connects reflection system to existing week data input handlers
"""

from aiogram import types
from aiogram.dispatcher import FSMContext
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
    """Register all reflection form handlers with dispatcher"""
    from reflection_forms import (
        handle_reflection_yes, handle_reflection_no,
        cmd_log_event, cmd_pending_forms, cmd_last_events
    )
    from reflection_handlers import (
        process_stage_type, process_rating, process_strengths, process_weaknesses,
        process_mood_rating, process_rejection_reason, process_rejection_other,
        handle_continue_forms, handle_stop_forms, handle_skip_form, handle_cancel_form
    )
    
    # Callback handlers for reflection triggers
    dp.register_callback_query_handler(handle_reflection_yes, lambda c: c.data.startswith("reflection_yes_"))
    dp.register_callback_query_handler(handle_reflection_no, lambda c: c.data == "reflection_no")
    
    # Stage type selection
    dp.register_callback_query_handler(
        process_stage_type, 
        lambda c: c.data.startswith("stage_"), 
        state="*"
    )
    
    # Rating selection
    dp.register_callback_query_handler(
        process_rating,
        lambda c: c.data.startswith("rating_"),
        state="*"
    )
    
    # Mood rating
    dp.register_callback_query_handler(
        process_mood_rating,
        lambda c: c.data.startswith("rating_") and c.message.text and "самочувствие" in c.message.text.lower(),
        state="*"
    )
    
    # Rejection reasons
    dp.register_callback_query_handler(
        process_rejection_reason,
        lambda c: c.data.startswith("reason_") or c.data == "reasons_done",
        state="*"
    )
    
    # Form navigation
    dp.register_callback_query_handler(handle_continue_forms, lambda c: c.data == "continue_forms")
    dp.register_callback_query_handler(handle_stop_forms, lambda c: c.data == "stop_forms")
    dp.register_callback_query_handler(handle_skip_form, lambda c: c.data == "skip_form")
    dp.register_callback_query_handler(handle_cancel_form, lambda c: c.data == "cancel_form")
    
    # Text message handlers for reflection states
    from reflection_forms import ReflectionStates
    dp.register_message_handler(process_strengths, state=ReflectionStates.strengths)
    dp.register_message_handler(process_weaknesses, state=ReflectionStates.weaknesses)
    dp.register_message_handler(process_rejection_other, state=ReflectionStates.rejection_other)
    
    # Commands
    dp.register_message_handler(cmd_log_event, commands=['log_event'])
    dp.register_message_handler(cmd_pending_forms, commands=['pending_forms'])
    dp.register_message_handler(cmd_last_events, commands=['last_events'])

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