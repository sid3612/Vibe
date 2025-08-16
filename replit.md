# Job Funnel Coach - Telegram Bot

## Overview

Job Funnel Coach is a Telegram bot designed to help users track and analyze job search funnels with automated CVR (Conversion Rate) metrics calculation. The bot supports two types of job search approaches: active (applications) and passive (profile views), allowing users to manage multiple channels (LinkedIn, HH.ru, referrals, etc.) and track their progress over time. The primary goal is to measure progress through the key metric of offers received over N weeks, with comprehensive data export capabilities and reminder functionality.

## Recent Changes (August 2025)

- **UTF-8 CSV Export**: Fixed CSV export to include UTF-8 BOM for proper Excel compatibility
- **Table Formatting**: Expanded table width to prevent CVR4 column overflow (65→70 chars)
- **Enhanced Data Input UX**: Added week information display and clearer field descriptions
- **Step-by-Step Flow**: Improved prompts with descriptive field names for better user understanding
- **Comprehensive Testing**: Added regression testing framework to prevent future issues

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
This approach ensures data isolation between users while maintaining referential integrity.

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

## External Dependencies

### Core Framework
- **aiogram**: Modern Telegram Bot API framework providing async/await support and FSM capabilities
- **APScheduler**: Task scheduling library for reminder functionality with cron-like triggers

### Data Processing
- **pandas**: Data manipulation and analysis for metrics calculations and export generation
- **sqlite3**: Built-in Python SQLite interface for local data persistence

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