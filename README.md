# Clinical Trial Matching System

An intelligent AI-powered system that helps patients find suitable clinical trials based on their medical profile. The application uses Mistral AI agents to analyze patient information, filter relevant trials, generate eligibility questions, and provide personalized explanations.

## 🎯 Overview

This system provides:
- **Intelligent Patient Profiling**: Natural language processing of patient medical descriptions
- **Smart Trial Matching**: Automated filtering and ranking of clinical trials
- **Dynamic Questionnaires**: AI-generated eligibility questions tailored to each trial
- **Personalized Explanations**: Clear, comprehensible explanations of trial results
- **Multi-language Support**: Automatic language detection and translation
- **Memory & Error Handling**: Comprehensive tracking and monitoring of all agent interactions

## 🏗️ Architecture

### Core Components

1. **Agent Manager** ([src/agent_manager.py](src/agent_manager.py))
   - Manages Mistral AI agents with automatic retry logic
   - Handles both synchronous and asynchronous operations
   - Integrates memory tracking and error handling
   - Supports structured responses with Pydantic models

2. **Memory System** ([src/utils/agent_memory.py](src/utils/agent_memory.py))
   - Tracks all user inputs and agent responses
   - Maintains conversation history
   - Supports memory export for analysis
   - Auto-prunes oldest entries (max 200)

3. **Error Handler** ([src/utils/error_handler.py](src/utils/error_handler.py))
   - Classifies errors by severity (LOW, MEDIUM, HIGH, CRITICAL)
   - Implements callback system for critical errors
   - Tracks feedback and success metrics
   - Provides detailed error context

4. **Services**
   - **Illness Analyzer** ([src/services/illness_analyzer.py](src/services/illness_analyzer.py)): Extracts structured medical information
   - **Trial Filter** ([src/services/trial_filter.py](src/services/trial_filter.py)): Matches trials to patient profiles
   - **Question Generator** ([src/services/question_generator.py](src/services/question_generator.py)): Creates eligibility questions
   - **Explanation Service** ([src/services/explanation_service.py](src/services/explanation_service.py)): Generates and validates explanations
   - **Language Service** ([src/services/language_service.py](src/services/language_service.py)): Handles translation and language detection

### Monitoring Endpoints

- `GET /monitoring/system/status` - Overall system health and metrics
- `GET /monitoring/agent/<name>/context` - Agent-specific conversation history
- `GET /monitoring/memory/export` - Full memory export in JSON format

## 🚀 Getting Started

### Prerequisites

- Python 3.13+
- Mistral API account and agent

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd code
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
   Or using uv:
   ```bash
   uv pip install -r requirements.txt
   ```

3. **Create a Mistral AI Agent**
   
   ⚠️ **IMPORTANT**: Before running the application, you need to create an agent on the Mistral AI platform.
   
   1. Go to [Mistral AI Console](https://console.mistral.ai/)
   2. Sign in or create an account
   3. Navigate to **Agents** section
   4. Click **Create Agent**
   5. Configure your agent:
      - **Name**: Choose a descriptive name (e.g., "Clinical Trial Assistant")
      - **Model**: Select `mistral-small-latest` or higher
      - **Instructions**: Add system instructions for medical context (optional)
   6. Copy the generated **Agent ID**
   7. Go to **API Keys** section and copy your **API Key**

4. **Configure environment variables**
   
   Copy the example file:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your credentials:
   ```env
   MISTRAL_API_KEY=your_mistral_api_key_here
   MISTRAL_AGENT_ID=your_mistral_agent_id_here
   ```

5. **Run the application**
   ```bash
   python main.py
   ```
   
   The application will be available at `http://localhost:5000`

### Verification

Test the system with the included test script:
```bash
python test_memory_system.py
```

Expected output:
- ✓ Manager initialization
- ✓ Agent creation
- ✓ Memory tracking
- ✓ System status display

## 📖 Usage

### For Patients

1. Navigate to `http://localhost:5000`
2. Select **"I am a Patient"**
3. Enter your medical profile or condition description
4. Answer the eligibility questions for each trial
5. Review your matched trials with personalized explanations
6. Save favorite trials for future reference

### For Researchers/Professionals

1. Select **"I am a Researcher"**
2. Access advanced filtering options
3. View detailed trial information
4. Generate reports and analytics
5. Export trial data

### Monitoring System Health

Access monitoring endpoints to track system performance:

```bash
# System status
curl http://localhost:5000/monitoring/system/status

# Agent context
curl http://localhost:5000/monitoring/agent/IllnessAnalyzer/context

# Memory export
curl http://localhost:5000/monitoring/memory/export
```

## 🔧 Configuration

### Memory Settings

Adjust memory capacity in [src/agent_manager.py](src/agent_manager.py):
```python
self.memory = AgentMemory(max_entries=200)  # Default: 200
```

### Retry Configuration

Configure retry behavior:
```python
manager = AgentManager(
    max_retries=3,      # Number of attempts
    retry_delay=1.0     # Base delay in seconds
)
```

### Error Callbacks

Register custom callbacks for critical errors:
```python
def send_alert(error_context):
    # Your alert logic (email, SMS, Slack, etc.)
    print(f"CRITICAL: {error_context.error_message}")

manager.error_handler.register_error_callback(
    ErrorSeverity.CRITICAL,
    send_alert
)
```

## 📊 Key Features

### Automatic Tracking
- ✅ All user inputs saved to memory
- ✅ All agent responses tracked
- ✅ Success/failure metrics collected
- ✅ Error classification by severity
- ✅ Conversation history maintained

### Error Handling
- **4 Severity Levels**: LOW, MEDIUM, HIGH, CRITICAL
- **Automatic Retries**: With exponential backoff
- **Callback System**: For critical error notifications
- **Detailed Logging**: Stack traces and context

### Memory Management
- **Max 200 entries** (configurable)
- **5 Memory Types**: USER_INPUT, AGENT_RESPONSE, SYSTEM_EVENT, ERROR, FEEDBACK
- **Timestamped entries** with ISO format
- **Agent-specific tracking**
- **JSON export** capability

## 📁 Project Structure

```
.
├── src/
│   ├── agent_manager.py           # Core agent management
│   ├── config.py                  # Configuration settings
│   ├── logger.py                  # Logging utilities
│   ├── response_models.py         # Pydantic models
│   ├── services/                  # Business logic services
│   │   ├── illness_analyzer.py
│   │   ├── trial_filter.py
│   │   ├── question_generator.py
│   │   ├── explanation_service.py
│   │   └── language_service.py
│   ├── routes/                    # Flask blueprints
│   │   ├── workflow_routes.py
│   │   ├── questionnaire_routes.py
│   │   ├── results_routes.py
│   │   └── monitoring_routes.py
│   └── utils/                     # Utility modules
│       ├── agent_memory.py
│       ├── error_handler.py
│       └── response_extractor.py
├── templates/                     # HTML templates
├── static/                        # CSS, JS, images
├── documentation/                 # Detailed documentation
│   ├── ARCHITECTURE.md
│   ├── MEMORY_ERROR_HANDLING.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   └── QUICK_START.md
├── main.py                        # Application entry point
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## 📚 Documentation

- **[Quick Start Guide](documentation/QUICK_START.md)** - Get started quickly
- **[Architecture Overview](documentation/ARCHITECTURE.md)** - System design and components
- **[Memory & Error Handling](documentation/MEMORY_ERROR_HANDLING.md)** - Detailed monitoring guide
- **[Implementation Summary](documentation/IMPLEMENTATION_SUMMARY.md)** - Technical implementation details

## 🧪 Testing

### Run Test Suite
```bash
python test_memory_system.py
```

### Manual Testing
1. Start the application
2. Process a patient description
3. Check system status: `http://localhost:5000/monitoring/system/status`
4. Review agent context: `http://localhost:5000/monitoring/agent/IllnessAnalyzer/context`

## 🐛 Troubleshooting

### Agent Not Found Error
- Verify your `MISTRAL_AGENT_ID` is correct in `.env`
- Ensure the agent exists in your Mistral AI console
- Check API key permissions

### Memory Growing Too Large
- Reduce `max_entries` in AgentMemory initialization
- Export and clear memories periodically

### Too Many Errors
- Check monitoring endpoints for error patterns
- Review agent prompts and response models
- Verify network connectivity to Mistral API

### Language Detection Issues
- Ensure user input is substantial enough (minimum 10-20 words)
- Check supported languages in [src/services/language_service.py](src/services/language_service.py)

## 🔒 Security Notes

- Keep your `.env` file secure and never commit it to version control
- Store API keys in environment variables
- Use HTTPS in production
- Implement rate limiting for production deployments
- Sanitize user inputs before processing

## 🚧 Future Enhancements

- [ ] Persistent memory storage (database integration)
- [ ] Real-time monitoring dashboard
- [ ] Advanced analytics and reporting
- [ ] Session recovery from memories
- [ ] Automated prompt tuning based on error patterns
- [ ] Email notifications for matched trials
- [ ] PDF report generation

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

[Add your license information here]

## 👥 Authors

[Add author information here]

## 🙏 Acknowledgments

- **Mistral AI** for providing the agent platform
- **Clinical Trials API** (clinicaltrials.gov) for trial data
- **Flask** for the web framework
- **Loguru** for beautiful logging

---

**Need Help?** Check the documentation or open an issue on GitHub.
