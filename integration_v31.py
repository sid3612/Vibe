"""
Integration module for PRD v3.1 reflection forms
Connects the simplified single-form reflection system to existing week data handlers
"""

from aiogram import types
from aiogram.fsm.context import FSMContext
from reflection_v31 import ReflectionV31System
from db import add_week_data

async def handle_week_data_with_v31_reflection(message: types.Message, user_id: int, 
                                             week_start: str, channel: str, funnel_type: str,
                                             new_data: dict, state: FSMContext = None):
    """
    Enhanced week data handler that checks for PRD v3.1 reflection triggers
    This should be called after week data is successfully processed
    """
    
    # Add data and get old/new values for trigger checking
    old_data, updated_data = add_week_data(user_id, week_start, channel, funnel_type, new_data, check_triggers=True)
    
    if old_data is None:
        # No trigger checking was done, return
        return
    
    # Check for reflection triggers using PRD v3.1 logic
    sections = ReflectionV31System.check_reflection_trigger(user_id, week_start, channel, funnel_type, old_data, updated_data)
    
    if sections:
        # Offer reflection form to user
        await ReflectionV31System.offer_reflection_form(
            message, user_id, week_start, channel, funnel_type, sections
        )

def register_v31_reflection_handlers(dp):
    """Register all PRD v3.1 reflection form handlers with dispatcher - aiogram v3 style"""
    from reflection_v31 import (
        handle_reflection_v31_yes, handle_reflection_v31_no, handle_reflection_v31_cancel,
        handle_section_rating, handle_section_reject_type, handle_section_strengths, handle_section_weaknesses, 
        handle_section_mood, handle_rejection_reasons, handle_rejection_other,
        handle_skip_strengths, handle_skip_weaknesses, ReflectionV31States
    )
    from aiogram.filters import StateFilter
    from aiogram import F
    
    # Callback handlers for reflection triggers - aiogram v3 style
    @dp.callback_query(F.data.startswith("reflection_v31_yes_"))
    async def _handle_reflection_v31_yes(callback: types.CallbackQuery, state: FSMContext):
        await handle_reflection_v31_yes(callback, state)
        
    @dp.callback_query(F.data == "reflection_v31_no")
    async def _handle_reflection_v31_no(callback: types.CallbackQuery):
        await handle_reflection_v31_no(callback)
        
    @dp.callback_query(F.data == "reflection_v31_cancel")
    async def _handle_reflection_v31_cancel(callback: types.CallbackQuery, state: FSMContext):
        await handle_reflection_v31_cancel(callback, state)
    
    # Form section handlers
    @dp.callback_query(F.data.startswith("rating_"), StateFilter(ReflectionV31States.section_rating))
    async def _handle_section_rating(callback: types.CallbackQuery, state: FSMContext):
        await handle_section_rating(callback, state)
    
    # Rejection type handlers
    @dp.callback_query(F.data.startswith("reject_type_"), StateFilter(ReflectionV31States.section_reject_type))
    async def _handle_section_reject_type(callback: types.CallbackQuery, state: FSMContext):
        await handle_section_reject_type(callback, state)
        
    @dp.callback_query(F.data.startswith("rating_"), StateFilter(ReflectionV31States.section_mood))
    async def _handle_section_mood(callback: types.CallbackQuery, state: FSMContext):
        await handle_section_mood(callback, state)
    
    @dp.callback_query(F.data.startswith("reason_v31_"))
    async def _handle_rejection_reasons(callback: types.CallbackQuery, state: FSMContext):
        await handle_rejection_reasons(callback, state)
        
    @dp.callback_query(F.data == "reasons_v31_done")
    async def _handle_reasons_done(callback: types.CallbackQuery, state: FSMContext):
        await handle_rejection_reasons(callback, state)
    
    # Skip button handlers
    @dp.callback_query(F.data == "skip_strengths")
    async def _handle_skip_strengths(callback: types.CallbackQuery, state: FSMContext):
        await handle_skip_strengths(callback, state)
        
    @dp.callback_query(F.data == "skip_weaknesses") 
    async def _handle_skip_weaknesses(callback: types.CallbackQuery, state: FSMContext):
        await handle_skip_weaknesses(callback, state)
    
    # Text message handlers for reflection states - aiogram v3 style
    @dp.message(ReflectionV31States.section_strengths, F.text)
    async def _handle_section_strengths(message: types.Message, state: FSMContext):
        await handle_section_strengths(message, state)
        
    @dp.message(ReflectionV31States.section_weaknesses, F.text)
    async def _handle_section_weaknesses(message: types.Message, state: FSMContext):
        await handle_section_weaknesses(message, state)
        
    @dp.message(ReflectionV31States.section_reject_other, F.text)
    async def _handle_rejection_other(message: types.Message, state: FSMContext):
        await handle_rejection_other(message, state)