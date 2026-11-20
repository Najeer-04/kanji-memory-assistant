
# Agentic AI Extension - Change Log

## Purpose
Track all changes made while extending the Kanji Memory Assistant with Agentic AI.

## Existing Project
The original Kanji Memory Assistant is functional.
Its existing functionality should be preserved.

## File Change History

| Date | File Path | Action | Purpose | Dependencies |
|---|---|---|---|---|
| 2026-11-20 | AGENTIC_AI_CHANGELOG.md | Created | Track Agentic AI project changes | None |
| 2026-11-20 | Python virtual environment | Dependencies installed | Added LangChain, LangGraph, LangChain-Ollama and LangSmith | Existing backend environment |

## Cleanup Notes
- Keep existing application files unless explicitly required.
- Record every new, modified, or deleted file.
- Record experimental files separately.
- Check imports and dependencies before deleting files.
- Update this log after every implementation step.

## Experimental Files
None yet.

## Pending Cleanup
None yet.

## Environment setup

### Installed dependencies
- langchain: 1.5.2
- langgraph: 1.2.24
- langchain-ollama: 1.1.0
- langsmith: 0.15.1
- pydantic: 2.14.1

### Runtime
- Python: 3.13.5
- Ollama: 0.40.16
- Model: qwen2.5:7b

### Notes
- pip check completed successfully.
- No agent implementation files created yet.

## First tool-calling experiment

| Date | File Path | Action | Purpose |
|---|---|---|---|
| 2026-11-20 | backend/agent/tool_calling_demo.py | Created | Demonstrates LangChain tool calling with Qwen through Ollama |

### Dependencies used
- langchain
- langchain-ollama
- langchain-core

### Notes
- Uses a temporary in-memory kanji dictionary.
- Does not modify the existing PostgreSQL or ChromaDB services.
- Demonstrates model tool requests, Python execution and returning ToolMessage results.

## First tool-calling experiment

| Date | File Path | Action | Purpose |
|---|---|---|---|
| 2026-11-20 | backend/agent/tool_calling_demo.py | Created | Demonstrates LangChain tool calling with Qwen through Ollama |

### Notes
- Uses a temporary in-memory kanji dictionary.
- Does not modify existing PostgreSQL or ChromaDB services.
- Demonstrates tool requests, Python execution and ToolMessage responses.