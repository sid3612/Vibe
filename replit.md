# Job Funnel Coach - Telegram Bot

## Overview

Job Funnel Coach is a Telegram bot designed to help users track and analyze job search funnels with automated CVR (Conversion Rate) metrics calculation. The bot supports two types of job search approaches: active (applications) and passive (profile views), allowing users to manage multiple channels (LinkedIn, HH.ru, referrals, etc.) and track their progress over time. The primary goal is to measure progress through the key metric of offers received over N weeks, with comprehensive data export capabilities and reminder functionality.

## Recent Changes (August 2025)

### Profile-Integrated Funnel Type Selection (August 16, 2025)
- **One-Time Funnel Selection**: Integrated funnel type choice into profile creation process
- **Database Schema Update**: Added `preferred_funnel_type` column to profiles table with automatic migration
- **Enhanced User Experience**: Replaced manual funnel selection with one-time preference in profile workflow
- **Smart Funnel Detection**: System now uses profile preference as primary source, falling back to user settings
- **Consistent Terminology**: Standardized all rejection interfaces to use "Отказ" instead of mixed terminology
- **Descriptive Button Labels**: Added emoji indicators to funnel type buttons for clearer user understanding:
  - "🧑‍💻 Активный поиск (я подаюсь)" for active funnel
  - "👀 Пассивный поиск (мне пишут)" for passive funnel
- **Profile Display Enhancement**: Added funnel type preference to profile view for transparency
- **Automatic Synchronization**: Profile preference automatically updates user's active funnel setting
- **UI/UX Improvements**: 
  - Fixed "Пропустить" and "Назад" buttons in profile creation wizard with proper callback handling
  - Moved "Сменить воронку" button from main menu to profile menu for better logical grouping
  - Added contextual navigation that returns to profile menu after funnel changes
- **Comprehensive Testing**: Full integration test suite validates funnel type workflow and button functionality

### PRD v3.1 Implementation Complete (August 16, 2025)
- **Major Architecture Update**: Replaced queue-based reflection system with simplified single-form MVP
- **Simplified Trigger Logic**: Reflection form now triggers only after completing all 5 statistical fields with ≥1 increase
- **Single Combined Form**: One form with multiple sections instead of individual forms per event
- **Database Schema**: Added `event_feedback` table with section-based storage per PRD v3.1 specification
- **Enhanced User Experience**: "Yes/No" prompt followed by combined form with skip/save options
- **Statistical Fields Only**: Only Responses, Screenings, Onsites, Offers, Rejections trigger forms
- **CVR Exclusion**: Applications/Views changes do not trigger reflection forms
- **Form Sections**: Dynamic sections based on which statistical fields increased
- **Rejection Handling**: Special multi-select reasons interface for rejection stages
- **State Management**: Improved FSM flow with proper completion handling
- **Rejection Type Classification**: Added granular rejection type selection (без интервью, после рекрутера, после тех интервью)
- **Reflection History**: Implemented "История рефлексий" showing last 10 reflections with details
- **History Menu**: Split history into "История данных" and "История рефлексий" for better UX
- **IndexError Fix**: Resolved section index bounds checking in save_rejection_reasons_and_continue
- **Hypotheses Integration Prep**: Added hypotheses.xlsx file and hypotheses_manager.py module for future ChatGPT integration
- **CVR Analysis Framework**: Created structure for analyzing user CVR data and preparing ChatGPT prompts

- **UTF-8 CSV Export**: Fixed CSV export to include UTF-8 BOM for proper Excel compatibility
- **Table Formatting**: Expanded table width to prevent CVR4 column overflow (70→75 chars)
- **Enhanced Data Input UX**: Added week information display and clearer field descriptions
- **Step-by-Step Flow**: Improved prompts with descriptive field names for better user understanding
- **Data Deduplication**: Fixed duplicate data issue - same week/channel entries now automatically sum values
- **Database Cleanup**: Added functionality to clean up existing duplicates and prevent future occurrences
- **Comprehensive Testing**: Added regression testing framework to prevent future issues
- **PRD v2 Implementation**: Added candidate profile management system with core functionality
- **Profile Database Schema**: Extended database with profiles table supporting all required and optional fields
- **Profile FSM Workflow**: Implemented step-by-step profile creation wizard with validation
- **Profile Integration**: Added profile menu to main interface with view/edit/delete capabilities
- **FSM State Filtering**: Fixed aiogram v3 compatibility with StateFilter(None) for proper message routing
- **Profile Workflow Complete**: End-to-end profile creation working: role → location → level → timeline
- **Optional Fields System**: Complete implementation of all PRD v2 optional fields with skip functionality:
  * Role synonyms (≤4) 
  * Salary expectations (min-max + currency + period)
  * Company types (text input with comma separation)
  * Industries (≤3)
  * Key competencies (≤10) 
  * Superpowers map (3-5)
  * Additional constraints
  * LinkedIn profile URL
- **Profile Management**: Fixed edit/delete functionality with proper keyboards and state handling
- **LinkedIn Field Integration**: Added LinkedIn URL as final optional step in profile creation
- **Plain Text Profile Display**: Changed from styled card format to clean text messages with action buttons
- **Regression Testing Suite**: Implemented comprehensive testing covering all critical functionality
- **Bug Fixes Applied**: Fixed constraints field mapping and date calculation accuracy issues
- **PRD v3.1 Implementation Complete**: Fully replaced PRD v3 with simplified single-form reflection system
  * **Simplified Architecture**: Replaced complex queue-based system with single combined form approach
  * **Enhanced Trigger Logic**: Reflection triggers only on statistical field increases (Responses, Screenings, Onsites, Offers, Rejections)
  * **Single Form Experience**: One combined form with multiple sections instead of individual event forms
  * **New Database Schema**: `event_feedback` table with section-stage storage architecture
  * **Improved UX Flow**: Simple "Yes/No" prompt → Combined form → Save/Cancel completion
  * **Dynamic Sections**: Form sections dynamically generated based on which statistical fields increased
  * **Rejection Workflow**: Specialized multi-select interface for rejection reason collection
  * **State Management**: Clean FSM flow with proper state clearing and error handling
  * **Type Safety**: Comprehensive null checking and message accessibility validation
  * **Comprehensive Testing**: Full test suite validating trigger logic, data saving, and UI components

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Bot Framework and Communication
The application uses the aiogram library for Telegram bot interactions, providing a modern async/await architecture for handling user commands and callbacks. The bot implements a state machine pattern using aiogram's FSM (Finite State Machine) for managing multi-step user interactions like data input and channel management.

### Data Storage Design
The system uses SQLite as the local database solution, chosen for its simplicity and compatibility with Replit hosting. The database schema includes:
- Users table for storing user preferences and settings
- User_channels table for managing custom channel configurations per user
- Week_data table for storing funnel metrics by user, week, and channel
- Profiles table for comprehensive candidate profile management (PRD v2)
This approach ensures data isolation between users while maintaining referential integrity across all functional modules.

### Funnel Type Architecture
The application implements a dual-funnel system:
- **Active Funnel**: Applications → Responses → Screenings → Onsites → Offers
- **Passive Funnel**: Views → Incoming → Screenings → Onsites → Offers

This design allows users to switch between funnel types dynamically, with different CVR calculations applied based on the selected type.

### Metrics Calculation Engine
The metrics module implements automatic CVR calculation with the following conversion rates:
- CVR1: Second stage / First stage
- CVR2: Third stage / Second stage
- CVR3: Fourth stage / Third stage  
- CVR4: Fifth stage / Fourth stage

The system handles division by zero gracefully, displaying "—" for undefined metrics, and rounds percentages to whole numbers for clarity.

### Data Input and Validation
The bot supports flexible data input patterns:
- Bulk weekly data entry through structured text commands
- Individual field updates for specific weeks and channels
- Channel management (add/remove channels dynamically)
- Data validation to ensure numeric inputs and proper formatting

### Export Functionality
The export system generates CSV files containing complete user history across all channels and weeks, including calculated metrics. This provides users with data portability and enables external analysis tools integration.

### Reminder System
Implements APScheduler for automated reminder functionality with configurable frequencies (daily/weekly). The system uses timezone-aware scheduling and maintains user preference persistence across bot restarts.

### User Interface Design
The bot uses inline keyboards for navigation and menu systems, combined with formatted text tables using monospace fonts for data display. This approach ensures readability within Telegram's constraints while maintaining a professional appearance.

### Profile Management System (PRD v2)
The candidate profile system implements a comprehensive FSM-based wizard for collecting and managing user career information:
- **Required Fields**: Role, current location, target location, experience level, job search timeline
- **Optional Fields**: Role synonyms, salary expectations, company preferences, industries, key competencies, achievements, constraints
- **Validation Layer**: Pydantic-based validation for data integrity and type safety
- **Database Integration**: JSON storage for complex field types within SQLite schema
- **User Experience**: Step-by-step guided input with skip options and inline keyboard navigation
- **Privacy Protection**: User-isolated data access with no cross-user data sharing

## External Dependencies

### Core Framework
- **aiogram**: Modern Telegram Bot API framework providing async/await support and FSM capabilities
- **APScheduler**: Task scheduling library for reminder functionality with cron-like triggers

### Data Processing
- **pandas**: Data manipulation and analysis for metrics calculations and export generation
- **sqlite3**: Built-in Python SQLite interface for local data persistence
- **pydantic**: Advanced data validation and parsing for profile management system

### Timezone and Date Management
- **pytz**: Timezone handling for accurate reminder scheduling across different user locations
- **datetime**: Standard Python datetime utilities for week-based data organization

### Infrastructure
- **Replit**: Cloud hosting platform providing 24/7 bot availability
- **SQLite Database**: Local file-based database storage within Replit environment
- **Telegram Bot API**: External service for message delivery and user interaction

### Optional Monitoring
- **UptimeRobot**: External monitoring service for ensuring continuous bot availability (mentioned as possible integration)

The architecture prioritizes simplicity and reliability, using well-established libraries and patterns to ensure stable operation in the Replit environment while providing comprehensive job search funnel tracking capabilities.