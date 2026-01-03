# Memory and Error Handling System

## Overview
The clinical trial matching system now includes comprehensive memory tracking and error handling capabilities for all AI agents.

## Components

### 1. AgentMemory (`src/utils/agent_memory.py`)
Tracks all interactions with agents including user inputs, agent responses, system events, errors, and feedback.

**Features:**
- **Memory Types**: USER_INPUT, AGENT_RESPONSE, SYSTEM_EVENT, ERROR, FEEDBACK
- **Max Entries**: 200 (configurable, auto-prunes oldest when exceeded)
- **Timestamped**: All entries include ISO format timestamps
- **Agent-specific**: Each entry tagged with agent name
- **Export**: JSON export capability for analysis

**Usage:**
```python
# Add memory entry
memory.add_memory(
    MemoryType.USER_INPUT,
    "Patient has type 2 diabetes",
    agent_name="IllnessAnalyzer"
)

# Get recent memories
recent = memory.get_recent_memories(limit=10)

# Get conversation history (for context)
history = memory.get_conversation_history(limit=50)

# Export all memories
export_data = memory.export_memories()
```

### 2. ErrorHandler (`src/utils/error_handler.py`)
Manages error tracking, severity classification, and feedback collection.

**Severity Levels:**
- **LOW**: Minor issues, no impact on functionality
- **MEDIUM**: Recoverable errors, retries possible
- **HIGH**: Significant errors, may impact user experience
- **CRITICAL**: System-level failures requiring immediate attention

**Feedback Types:**
- **SUCCESS**: Successful operations
- **WARNING**: Potential issues to monitor
- **ERROR**: Error conditions
- **INFO**: Informational messages

**Usage:**
```python
# Handle error with context
error_context = error_handler.handle_error(
    exception,
    "Failed to process request",
    severity=ErrorSeverity.HIGH,
    agent_name="QuestionGenerator",
    additional_context="Trial NCT123456"
)

# Add feedback
error_handler.add_feedback(
    FeedbackType.SUCCESS,
    "Successfully generated 15 questions",
    agent_name="QuestionGenerator"
)

# Register error callback
def on_critical_error(context):
    send_alert_email(context)
    
error_handler.register_error_callback(
    ErrorSeverity.CRITICAL,
    on_critical_error
)

# Get summaries
error_summary = error_handler.get_error_summary()
feedback_summary = error_handler.get_feedback_summary()
```

### 3. AgentManager Integration
All agent interactions are automatically tracked with memory and error handling.

**Automatic Tracking:**
- Every user input saved to memory
- Every agent response saved to memory
- All errors tracked with severity levels
- Success feedback on successful completions
- Automatic retry with escalating severity

**Configuration:**
```python
# Initialize manager (done in main.py)
manager = AgentManager()

# Memory and error handler are automatically created
# memory: AgentMemory with max_entries=200
# error_handler: ErrorHandler with history tracking

# Chat with memory tracking
response = await manager.chat_with_retry_async(
    agent_name="IllnessAnalyzer",
    message="Patient has kidney disease",
    save_to_memory=True  # Default is True
)
```

## Monitoring Endpoints

### 1. System Status
**Endpoint:** `GET /system/status`

**Returns:**
```json
{
  "agents": ["IllnessAnalyzer", "QuestionGenerator", "ExplanationAgent"],
  "memory": {
    "total_entries": 145,
    "by_type": {
      "USER_INPUT": 48,
      "AGENT_RESPONSE": 48,
      "ERROR": 3,
      "FEEDBACK": 46
    },
    "by_agent": {
      "IllnessAnalyzer": 32,
      "QuestionGenerator": 28
    }
  },
  "errors": {
    "total": 3,
    "by_severity": {
      "MEDIUM": 2,
      "HIGH": 1
    },
    "by_agent": {
      "ExplanationAgent": 3
    }
  },
  "feedback": {
    "total": 46,
    "by_type": {
      "SUCCESS": 45,
      "WARNING": 1
    }
  }
}
```

### 2. Agent Context
**Endpoint:** `GET /agent/<agent_name>/context`

**Returns:**
```json
{
  "agent_name": "IllnessAnalyzer",
  "conversation_history": [
    {
      "role": "user",
      "content": "Patient has type 2 diabetes"
    },
    {
      "role": "assistant",
      "content": "Extracted: illness_type=diabetes, keywords=[diabetes, type 2]"
    }
  ],
  "memories": [
    {
      "timestamp": "2024-01-15T10:30:45",
      "memory_type": "USER_INPUT",
      "content": "Patient has type 2 diabetes",
      "agent_name": "IllnessAnalyzer"
    }
  ],
  "errors": [
    {
      "timestamp": "2024-01-15T10:31:20",
      "error_type": "ValidationError",
      "message": "Invalid response format",
      "severity": "MEDIUM"
    }
  ]
}
```

### 3. Memory Export
**Endpoint:** `GET /memory/export`

**Returns:**
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
        "agent_name": "IllnessAnalyzer"
      }
    }
  ]
}
```

## Error Handling Flow

### 1. Automatic Retries
```
Attempt 1: MEDIUM severity → Log warning → Retry in 1s
Attempt 2: MEDIUM severity → Log warning → Retry in 2s
Attempt 3: HIGH severity → Log error → Fail
Final: CRITICAL severity → Execute callbacks → Raise exception
```

### 2. Memory Tracking
```
User Input → Save to memory (USER_INPUT)
↓
Agent Call → Execute with retry
↓
Success → Save response (AGENT_RESPONSE) + Feedback (SUCCESS)
Error → Save error (ERROR) + Handle with severity
```

### 3. Severity Escalation
```
First attempt fails → MEDIUM severity
Middle attempts fail → MEDIUM severity
Last attempt fails → HIGH severity
All attempts exhausted → CRITICAL severity + callbacks
```

## Best Practices

### 1. Memory Management
- Default max_entries=200 is sufficient for most sessions
- Export memories periodically for long-running sessions
- Use `get_recent_memories()` for displaying recent context
- Clear memories when starting new patient sessions

### 2. Error Handling
- Register callbacks for CRITICAL errors to send alerts
- Monitor error summaries to identify problematic agents
- Use feedback tracking to measure success rates
- Review error patterns to improve prompts

### 3. Monitoring
- Check `/system/status` endpoint regularly
- Monitor error rates by agent and severity
- Review conversation history for context
- Export memories for debugging complex issues

## Configuration

### Memory Configuration
```python
# In agent_manager.py __init__
self.memory = AgentMemory(max_entries=200)

# Adjust max_entries based on session length
# 200 entries = ~100 user interactions (input + response)
```

### Error Handler Configuration
```python
# In agent_manager.py __init__
self.error_handler = ErrorHandler()

# Register critical error callbacks
self.error_handler.register_error_callback(
    ErrorSeverity.CRITICAL,
    send_admin_alert
)
```

### Retry Configuration
```python
# In agent_manager.py __init__
self.max_retries = 3
self.retry_delay = 1  # seconds

# Exponential backoff: 1s, 2s, 3s between retries
```

## Troubleshooting

### Issue: Memory growing too large
**Solution:** Reduce max_entries or export/clear memories periodically

### Issue: Too many error alerts
**Solution:** Register callbacks only for CRITICAL severity

### Issue: Lost conversation context
**Solution:** Use `get_conversation_history()` to review recent interactions

### Issue: Agent failing repeatedly
**Solution:** Check `/agent/<name>/context` for error patterns

## Future Enhancements

1. **Persistent Storage**: Save memories to database instead of in-memory
2. **Analytics Dashboard**: Web UI for visualizing memory and error data
3. **Automatic Prompt Tuning**: Use error patterns to adjust agent prompts
4. **Session Recovery**: Restore memory from previous sessions
5. **Distributed Tracing**: Track requests across multiple agents
