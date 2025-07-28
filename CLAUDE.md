# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an agricultural AI agent system called "Agri_AI5" that uses LangGraph for multi-agent architecture. The system provides LINE-based conversational AI for farmers, integrating natural language processing with agricultural data management.

### Core Architecture

The system follows a **Supervisor-Worker multi-agent pattern** using LangGraph:

- **SupervisorAgent**: Central orchestrator that receives LINE webhook messages, analyzes user intent, and routes to appropriate specialist agents
- **ReadAgent**: Handles all read-only queries (work history, field information, etc.)  
- **WriteAgent**: Manages data writing operations with user confirmation flows
- **RecommendationAgent**: Analyzes weather, work history, and crop data to suggest optimal farming actions
- **NotificationAgent**: Handles proactive notifications and scheduled reminders via LINE

### Key Technologies

- **AI Framework**: Python 3.9+, LangChain, LangGraph
- **LLM**: Google Gemini Pro/Flash
- **Database**: MongoDB Atlas with Motor (async access)
- **UI/UX**: LINE Messaging API + LIFF (LINE Front-end Framework)
- **Infrastructure**: Google Cloud (Functions for webhooks, Cloud Run for agents, Pub/Sub for async processing)
- **Monitoring**: LangSmith

## Development Commands

**Note**: This repository currently contains only documentation and design specifications. No executable code, build scripts, or package managers are present yet.

Once implementation begins, typical commands will likely include:
- Python dependency management (requirements.txt or poetry)
- MongoDB connection and migration scripts
- Google Cloud deployment commands
- LINE webhook testing utilities

## Data Architecture

### MongoDB Schema Design

The system uses a document-oriented MongoDB design with the following core collections:

- **work_logs**: Central collection storing structured agricultural work records extracted from natural language LINE messages
- **fields**: Farm field master data with current cultivation status and scheduled work
- **crops**: Crop master data including cultivation calendars and disease/pest risk information
- **materials**: Agricultural materials (pesticides, fertilizers) with usage guidelines
- **users**: User profiles with LINE integration and personalized terminology dictionaries

### State Management

Uses `AgriAgentState` (TypedDict) for conversation context and task state management:
- Persisted via `MongoDBSaver` for session continuity
- Includes user_id, thread_id, next_agent routing, and pending confirmations
- Supports user-specific data extensions and dynamic schema growth

## Development Phases

The project follows a 4-phase development approach:

1. **Phase 1 (3 weeks)**: Basic foundation with Supervisor + ReadAgent for LINE Q&A
2. **Phase 2 (3 weeks)**: WriteAgent implementation with user confirmation flows + basic LIFF dashboard  
3. **Phase 3 (4 weeks)**: RecommendationAgent for work suggestions + advanced LIFF features
4. **Phase 4 (4 weeks)**: NotificationAgent for proactive alerts + async processing infrastructure

## Key Design Principles

- **LINE-First Interface**: All user interactions start through LINE chat or LIFF apps
- **Natural Language Processing**: Convert farmers' casual Japanese messages into structured agricultural data
- **Human-in-the-Loop**: Critical database operations require user confirmation via LINE
- **Personalization**: System learns user-specific terminology and work patterns
- **Legacy Integration**: 100% reuse of existing tools from Agri_AI3 project

## Important Context

- This system is designed specifically for Japanese agricultural operations
- Focuses on reducing farmers' cognitive load - goal is "0 minutes" thinking time for work decisions
- Emphasizes safety with confirmation flows for data modifications
- Designed to work seamlessly across field work (mobile LINE) and office planning (LIFF dashboard)

## File Structure Context

Currently the repository contains only design documentation in the `docs/` directory:
- Project task lists and development roadmaps
- Comprehensive system requirements and architecture specifications  
- MongoDB schema design documents
- Multi-language documentation (Japanese)

Implementation code will be added as development progresses through the defined phases.