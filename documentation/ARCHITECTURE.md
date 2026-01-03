# System Architecture: Memory and Error Handling

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Flask Application                        │
│                           (main.py)                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
        ┌───────▼────────┐      ┌──────▼──────┐
        │  AgentManager  │      │  Blueprints │
        │                │      │             │
        │ - memory       │      │ - workflow  │
        │ - error_handler│      │ - questions │
        │ - agents       │      │ - results   │
        │                │      │ - monitoring│
        └───────┬────────┘      └─────────────┘
                │
      ┌─────────┼─────────┐
      │         │         │
┌─────▼────┐ ┌──▼───────┐ ┌───▼──────┐
│  Memory  │ │  Error   │ │  Agents  │
│  System  │ │  Handler │ │          │
│          │ │          │ │ - Illness│
│ 200 max  │ │ 4 levels │ │ - Filter │
│ entries  │ │ severity │ │ - Question│
└──────────┘ └──────────┘ │ - Explain│
                           └──────────┘
```

## Data Flow

```
1. User Request
   ↓
2. Flask Route (workflow_bp)
   ↓
3. AgentManager.chat_with_retry_async()
   ↓
4. Memory: Save USER_INPUT
   ↓
5. Agent.chat_async()
   ↓
6. Success?
   ├─ YES → Memory: Save AGENT_RESPONSE
   │        ErrorHandler: Add SUCCESS feedback
   │        Return response
   │
   └─ NO → ErrorHandler: Create ErrorContext
           Memory: Save ERROR
           Retry with increased severity
           ├─ Attempt 1: MEDIUM
           ├─ Attempt 2: MEDIUM  
           ├─ Attempt 3: HIGH
           └─ All fail: CRITICAL → Execute callbacks
```

## Memory System Architecture

```
┌──────────────────────────────────────────┐
│            AgentMemory                   │
│  ┌────────────────────────────────────┐ │
│  │  memories: List[MemoryEntry]       │ │
│  │  max_entries: 200                  │ │
│  │                                    │ │
│  │  MemoryEntry:                      │ │
│  │  - timestamp                       │ │
│  │  - memory_type                     │ │
│  │  - content                         │ │
│  │  - metadata                        │ │
│  │  - agent_name                      │ │
│  └────────────────────────────────────┘ │
│                                          │
│  Methods:                                │
│  ├─ add_memory()                         │
│  ├─ get_recent_memories()                │
│  ├─ get_conversation_history()           │
│  ├─ export_memories()                    │
│  └─ get_summary()                        │
└──────────────────────────────────────────┘
```

## Error Handler Architecture

```
┌──────────────────────────────────────────┐
│           ErrorHandler                   │
│  ┌────────────────────────────────────┐ │
│  │  error_history: List[ErrorContext] │ │
│  │  feedback_history: List[Feedback]  │ │
│  │  callbacks: Dict[severity, func]   │ │
│  │                                    │ │
│  │  ErrorContext:                     │ │
│  │  - error_type                      │ │
│  │  - error_message                   │ │
│  │  - severity (LOW/MED/HIGH/CRIT)    │ │
│  │  - timestamp                       │ │
│  │  - context                         │ │
│  │  - stack_trace                     │ │
│  │                                    │ │
│  │  Feedback:                         │ │
│  │  - feedback_type (SUCCESS/WARN)    │ │
│  │  - message                         │ │
│  │  - timestamp                       │ │
│  │  - metadata                        │ │
│  └────────────────────────────────────┘ │
│                                          │
│  Methods:                                │
│  ├─ handle_error()                       │
│  ├─ add_feedback()                       │
│  ├─ register_error_callback()            │
│  ├─ get_error_summary()                  │
│  └─ get_feedback_summary()               │
└──────────────────────────────────────────┘
```

## Monitoring Endpoints Architecture

```
┌───────────────────────────────────────────────┐
│         Monitoring Blueprint                  │
│         (monitoring_routes.py)                │
├───────────────────────────────────────────────┤
│                                               │
│  GET /system/status                           │
│  ├─ Returns: agents, memory stats,            │
│  │           error stats, feedback stats      │
│  └─ Calls: manager.get_system_status()        │
│                                               │
│  GET /agent/<name>/context                    │
│  ├─ Returns: conversation history,            │
│  │           memories, errors                 │
│  └─ Calls: manager.get_agent_context(name)    │
│                                               │
│  GET /memory/export                           │
│  ├─ Returns: timestamp, total entries,        │
│  │           all memory entries               │
│  └─ Calls: manager.memory.export_memories()   │
│                                               │
└───────────────────────────────────────────────┘
```

## Retry Flow with Severity Escalation

```
Agent Call
    │
    ├─ Attempt 1
    │  ├─ Success → Return response
    │  └─ Fail → ErrorSeverity.MEDIUM
    │            Log warning
    │            Wait 1 second
    │
    ├─ Attempt 2
    │  ├─ Success → Return response
    │  └─ Fail → ErrorSeverity.MEDIUM
    │            Log warning
    │            Wait 2 seconds
    │
    └─ Attempt 3
       ├─ Success → Return response
       └─ Fail → ErrorSeverity.HIGH
                 Log error
                 ErrorSeverity.CRITICAL
                 Execute callbacks
                 Raise exception
```

## Memory Entry Lifecycle

```
1. User Input
   ↓
   add_memory(USER_INPUT, content, agent_name)
   ↓
2. Create MemoryEntry
   - timestamp: now()
   - memory_type: USER_INPUT
   - content: user message
   - metadata: {agent_name, ...}
   ↓
3. Append to memories list
   ↓
4. Check if len(memories) > max_entries
   - YES → Remove oldest entry
   - NO → Continue
   ↓
5. Entry available for:
   - get_recent_memories()
   - get_conversation_history()
   - export_memories()
   - get_summary()
```

## Integration with Clinical Trial Workflow

```
User enters patient info
    ↓
Workflow Route (/process_workflow)
    ↓
1. IllnessAnalyzer agent
   - Memory: Save user input
   - Memory: Save agent response (illness info)
   - Feedback: SUCCESS
    ↓
2. Fetch trials from API
   - Memory: Save SYSTEM_EVENT
    ↓
3. TrialFilter agent
   - Memory: Save filtering request
   - Memory: Save filtered results
   - Feedback: SUCCESS
    ↓
4. QuestionGenerator agent
   - Memory: Save criteria extraction
   - Memory: Save generated questions
   - Feedback: SUCCESS
    ↓
User answers questions
    ↓
Results Route (/get_results)
    ↓
5. ExplanationAgent
   - Memory: Save explanation request
   - Memory: Save explanation
   - If evaluation fails:
     * ErrorHandler: Track failure
     * Memory: Save ERROR
     * Retry with ExplanationRewriter
   - Feedback: SUCCESS

All interactions tracked in memory
All errors handled with severity
All feedback collected
System status available via /system/status
```

## Callback System

```
┌─────────────────────────────────────────┐
│     Error Callback Registration         │
├─────────────────────────────────────────┤
│                                         │
│  error_handler.register_error_callback( │
│      ErrorSeverity.CRITICAL,            │
│      callback_function                  │
│  )                                      │
│                                         │
│  When CRITICAL error occurs:            │
│  1. Create ErrorContext                 │
│  2. Execute registered callback         │
│  3. Pass ErrorContext to callback       │
│  4. Continue with error propagation     │
│                                         │
│  Example callbacks:                     │
│  - send_email_alert()                   │
│  - send_slack_notification()            │
│  - log_to_monitoring_service()          │
│  - trigger_incident_response()          │
│                                         │
└─────────────────────────────────────────┘
```

## Memory Export Format

```json
{
  "timestamp": "2024-01-15T11:00:00",
  "total_entries": 145,
  "max_entries": 200,
  "entries": [
    {
      "timestamp": "2024-01-15T10:30:45",
      "memory_type": "USER_INPUT",
      "content": "Patient has type 2 diabetes",
      "metadata": {
        "agent_name": "IllnessAnalyzer",
        "use_history": false
      }
    },
    {
      "timestamp": "2024-01-15T10:30:46",
      "memory_type": "AGENT_RESPONSE",
      "content": "{\"illness_type\": \"diabetes\", ...}",
      "metadata": {
        "agent_name": "IllnessAnalyzer",
        "attempt": 1
      }
    },
    {
      "timestamp": "2024-01-15T10:30:47",
      "memory_type": "ERROR",
      "content": "Error: Validation failed",
      "metadata": {
        "agent_name": "ExplanationAgent",
        "attempt": 1,
        "exception_type": "ValidationError"
      }
    }
  ]
}
```

## Summary

The system provides:
- **Complete observability** of all agent interactions
- **Automatic error tracking** with severity classification
- **Feedback collection** for success monitoring
- **Real-time monitoring** via HTTP endpoints
- **Memory export** for analysis and debugging
- **Callback system** for critical error alerting
- **Agent-specific context** for troubleshooting
- **Conversation history** for context preservation
