# PRD v3 Implementation Plan - Reflection Forms System

## Overview
Implementing automatic reflection form system that triggers after counter increases, as specified in PRD v3. This is a major feature addition that provides users with structured reflection and learning capabilities.

## Core Components Created

### 1. Reflection Forms System (`reflection_forms.py`)
- **ReflectionQueue**: Manages reflection form queue in database
- **ReflectionTrigger**: Detects counter increases and offers reflection forms
- **Stage mapping**: Maps funnel stages to CVR calculations and hypotheses
- **Form creation logic**: Creates multiple forms based on delta increases

### 2. Reflection Handlers (`reflection_handlers.py`) 
- **Complete FSM workflow**: Step-by-step form completion process
- **Stage type selection**: ✉️ Ответ, 📞 Скрининг, 🧑‍💼 Онсайт, 🏁 Оффер, ❌ Отказ
- **Rating systems**: 1-5 ratings for performance and mood/motivation
- **Rejection reasons**: Multi-select with custom "other" option
- **Form navigation**: Skip, continue, cancel options

### 3. Integration Module (`integration_v3.py`)
- **Trigger detection**: Connects to existing week data input system
- **Handler registration**: Registers all reflection handlers with dispatcher
- **Backward compatibility**: Maintains existing functionality

## Database Schema Extension

### New Table: reflection_queue
```sql
CREATE TABLE reflection_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    week_start TEXT NOT NULL,
    channel TEXT NOT NULL,
    funnel_type TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    form_data TEXT NULL
)
```

## Key Features Implemented

### Trigger System
- **Automatic detection**: Monitors responses, screenings, onsites, offers, rejections
- **Delta calculation**: Creates one form per unit increase
- **User consent**: Only creates forms after user agrees
- **Context preservation**: Week + channel + funnel type context

### Form Content
- **Stage type selection**: With CVR hints and hypothesis links
- **Performance rating**: 1-5 scale
- **Strengths/weaknesses**: Optional text fields
- **Mood tracking**: 1-5 motivation scale
- **Rejection analysis**: Structured reason categorization

### Queue Management
- **Pending forms**: Shows count and allows bulk processing
- **Skip/cancel options**: Flexible user control
- **Void handling**: Manages counter decreases properly
- **Persistence**: Forms survive bot restarts

## Commands Added
- `/log_event` - Manual reflection form creation
- `/pending_forms` - View and fill pending forms
- `/last_events` - Show recent reflection entries

## Integration Points

### Modified Functions
- `add_week_data()`: Enhanced with trigger checking
- Added return values for old_data/new_data comparison

### Handler Registration
- All reflection handlers register with main dispatcher
- FSM states properly integrated
- Callback data handling for all form interactions

## Next Steps Required

1. **Update main.py**: Register reflection handlers
2. **Database initialization**: Create reflection_queue table
3. **Testing**: Comprehensive testing of trigger logic
4. **User experience**: Refine form flow and messaging
5. **Integration**: Connect to existing week data input handlers

## Technical Notes

- **FSM per user**: Each user has independent form state
- **JSON storage**: Complex form data stored as JSON in database
- **Scalable design**: Handles multiple concurrent forms per user
- **Error handling**: Graceful fallbacks for all operations

This implementation provides a comprehensive foundation for the PRD v3 reflection system while maintaining compatibility with existing v1/v2 functionality.