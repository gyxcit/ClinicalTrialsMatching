# Clinical Trial Matching System

An intelligent AI-powered system that helps patients find suitable clinical trials based on their medical profile. The application uses Mistral AI agents to analyze patient information, filter relevant trials, generate eligibility questions, and provide personalized explanations in multiple languages.

## 🎯 Overview

This system provides:
- **Intelligent Patient Profiling**: Natural language processing of patient medical descriptions with both structured forms and free-text input
- **Smart Trial Matching**: Automated filtering and ranking of clinical trials from ClinicalTrials.gov database
- **Dynamic Questionnaires**: AI-generated eligibility questions tailored to each trial with simplified reformulations
- **Personalized Explanations**: Clear, comprehensible explanations validated for patient understanding (60+ comprehension score)
- **Multi-language Support**: Automatic language detection and translation (10+ languages supported)
- **Memory & Error Handling**: Comprehensive tracking and monitoring of all agent interactions with 4-level severity classification
- **Favorites System**: Save and track interesting trials across sessions

## 🏗️ Architecture

### Core Components

1. **Agent Manager** ([src/agent_manager.py](src/agent_manager.py))
   - Manages Mistral AI agents with automatic retry logic (exponential backoff)
   - Handles both synchronous and asynchronous operations
   - Integrates memory tracking and error handling
   - Supports structured responses with Pydantic models
   - 3 retry attempts with configurable delays

2. **Memory System** ([src/utils/agent_memory.py](src/utils/agent_memory.py))
   - Tracks all user inputs and agent responses
   - Maintains conversation history (up to 200 entries)
   - Supports memory export for analysis in JSON format
   - Auto-prunes oldest entries when limit reached
   - 5 memory types: USER_INPUT, AGENT_RESPONSE, SYSTEM_EVENT, ERROR, FEEDBACK

3. **Error Handler** ([src/utils/error_handler.py](src/utils/error_handler.py))
   - Classifies errors by severity (LOW, MEDIUM, HIGH, CRITICAL)
   - Implements callback system for critical errors
   - Tracks feedback and success metrics
   - Provides detailed error context with stack traces
   - Maintains error and feedback history

4. **Services**
   - **Illness Analyzer** ([src/services/illness_analyzer.py](src/services/illness_analyzer.py)): Extracts structured medical information (diagnosis, stage, biomarkers, etc.)
   - **Trial Filter** ([src/services/trial_filter.py](src/services/trial_filter.py)): Matches trials to patient profiles with relevance scoring
   - **Question Generator** ([src/services/question_generator.py](src/services/question_generator.py)): Creates eligibility questions from trial criteria
   - **Question Simplifier** ([src/services/question_simplifier.py](src/services/question_simplifier.py)): Reformulates medical questions into everyday language
   - **Explanation Service** ([src/services/explanation_service.py](src/services/explanation_service.py)): Generates and validates explanations with automatic rewriting
   - **Language Service** ([src/services/language_service.py](src/services/language_service.py)): Handles translation and language detection

### Monitoring Endpoints

- `GET /monitoring/system/status` - Overall system health and metrics (agents, memory, errors, feedback)
- `GET /monitoring/agent/<name>/context` - Agent-specific conversation history and recent memories
- `GET /monitoring/memory/export` - Full memory export in JSON format with timestamps

### User Workflows

1. **Patient Mode**
   - Simple landing page with mode selection
   - Patient profile form (structured fields or free-text clinical notes)
   - Trial matching workflow with loading page
   - Dynamic questionnaire with yes/no/unsure answers
   - Results page with match scores and explanations
   - Favorites management

2. **Professional Mode**
   - Advanced profile form with clinical staging (ECOG, TNM)
   - Biomarker input (EGFR, PD-L1, etc.)
   - Treatment history tracking
   - Comorbidities management

## 🚀 Getting Started

### Prerequisites

- Python 3.13+
- Mistral API account and agent
- Modern web browser (Chrome, Firefox, Safari, Edge)

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
      - **Model**: Select `mistral-small-latest` (recommended) or higher
      - **Instructions**: Add system instructions for medical context (optional)
      - **Temperature**: 0.7 (default, balances creativity and precision)
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
- ✓ Memory export

## 📖 Usage

### For Patients

1. Navigate to `http://localhost:5000`
2. Select **"I am a Patient"**
3. Choose input method:
   - **Simple Form**: Basic fields (name, diagnosis, stage)
   - **Free Text**: Paste clinical notes or describe your condition
4. Click "Continue" to start trial matching
5. Wait for analysis (loading page with progress indicator)
6. Answer eligibility questions for each trial:
   - Click **Yes**, **No**, or **Unsure** for each question
   - Use "Reformulate" to simplify medical terminology
   - Track progress with visual indicators
7. Review results:
   - Strong matches (eligible trials)
   - Potential matches (partial eligibility)
   - Match percentages and explanations
   - Click "🤖 Explain" for AI-generated explanations
8. Save favorite trials with ❤️ button
9. Access saved trials from "Favorites" page

### For Researchers/Professionals

1. Select **"I am a Healthcare Professional"**
2. Access advanced profile form:
   - ECOG performance status
   - TNM staging (if applicable)
   - Detailed biomarker input (EGFR, ALK, ROS1, PD-L1, etc.)
   - Prior treatment history
   - Comorbidities
3. Use "chips" interface to add multiple values
4. View detailed trial information with clinical relevance
5. Export trial data and matching results

### Monitoring System Health

Access monitoring endpoints to track system performance:

```bash
# System status
curl http://localhost:5000/monitoring/system/status

# Agent context (example: IllnessAnalyzer)
curl http://localhost:5000/monitoring/agent/IllnessAnalyzer/context

# Memory export
curl http://localhost:5000/monitoring/memory/export
```

Response includes:
- Active agents list
- Memory statistics (total entries, breakdown by type and agent)
- Error statistics (total, by severity, by agent)
- Feedback statistics (success rate, warnings)

## 🔧 Configuration

### Memory Settings

Adjust memory capacity in [src/agent_manager.py](src/agent_manager.py):
```python
self.memory = AgentMemory(max_entries=200)  # Default: 200
```

### Retry Configuration

Configure retry behavior in [src/agent_manager.py](src/agent_manager.py):
```python
manager = AgentManager(
    max_retries=3,      # Number of attempts
    retry_delay=1.0     # Base delay in seconds (exponential backoff)
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

### Explanation Quality Threshold

Adjust comprehension score threshold in [src/services/explanation_service.py](src/services/explanation_service.py):
```python
# Default: 60/100 for acceptable explanations
# Automatic rewriting if score < 60
```

## 📊 Key Features

### Automatic Tracking
- ✅ All user inputs saved to memory
- ✅ All agent responses tracked with metadata
- ✅ Success/failure metrics collected
- ✅ Error classification by severity
- ✅ Conversation history maintained (20-50 entries)
- ✅ Timestamped entries (ISO format)

### Error Handling
- **4 Severity Levels**: 
  - LOW: Minor issues, no impact
  - MEDIUM: Recoverable errors, retries possible
  - HIGH: Significant errors, may impact UX
  - CRITICAL: System failures, immediate attention required
- **Automatic Retries**: With exponential backoff (1s, 2s, 4s)
- **Callback System**: For critical error notifications
- **Detailed Logging**: Stack traces and context with Loguru

### Memory Management
- **Max 200 entries** (configurable, auto-prunes oldest)
- **5 Memory Types**: USER_INPUT, AGENT_RESPONSE, SYSTEM_EVENT, ERROR, FEEDBACK
- **Timestamped entries** with ISO format
- **Agent-specific tracking** (by agent name)
- **JSON export** capability for analysis

### Language Support
- **Automatic Detection**: Detects user's language from input
- **10+ Languages**: English, French, Spanish, German, Italian, Portuguese, Dutch, Polish, Arabic, Chinese
- **Context-Aware Translation**: Medical terminology preserved
- **Session Persistence**: Language preference saved across requests

### Question Simplification
- **On-Demand**: Click "Reformulate" to simplify any question
- **Everyday Language**: Replaces medical jargon
- **Maintains Meaning**: Preserves question intent
- **Context-Aware**: Uses trial information for better reformulation

### Explanation Validation
- **Automatic Evaluation**: Comprehension score (0-100)
- **Quality Criteria**: Clarity, structure, completeness, empathy
- **Automatic Rewriting**: If score < 60, rewrites up to 3 times
- **Feedback Loop**: Uses evaluation results to improve

## 📁 Project Structure

```
.
├── src/
│   ├── __init__.py
│   ├── agent_manager.py           # Core agent management with retry logic
│   ├── config.py                  # Configuration settings (API keys, paths)
│   ├── logger.py                  # Logging utilities (Loguru)
│   ├── response_models.py         # Pydantic models for structured responses
│   ├── example_llm.py             # Example LLM client test
│   ├── trials.py                  # Clinical trials data handling
│   ├── services/                  # Business logic services
│   │   ├── __init__.py
│   │   ├── illness_analyzer.py    # Patient profile analysis
│   │   ├── trial_filter.py        # Trial matching and filtering
│   │   ├── question_generator.py  # Eligibility question generation
│   │   ├── question_simplifier.py # Medical question simplification
│   │   ├── explanation_service.py # Result explanation generation
│   │   └── language_service.py    # Translation and language detection
│   ├── routes/                    # Flask blueprints
│   │   ├── __init__.py
│   │   ├── workflow_routes.py     # Main workflow endpoints
│   │   ├── questionnaire_routes.py # Questionnaire logic
│   │   ├── results_routes.py      # Results and explanations
│   │   ├── monitoring_routes.py   # System monitoring
│   │   ├── favorites_routes.py    # Favorites management
│   │   ├── home_routes.py         # Landing page
│   │   └── patient_routes.py      # Patient profile
│   └── utils/                     # Utility modules
│       ├── __init__.py
│       ├── agent_memory.py        # Memory tracking system
│       ├── error_handler.py       # Error handling and classification
│       ├── response_extractor.py  # Response parsing utilities
│       └── session_manager.py     # Session data management
├── templates/                     # HTML templates (Jinja2)
│   ├── base.html                  # Base template with sidebar
│   ├── home.html                  # Landing page
│   ├── patient_profile.html       # Profile form
│   ├── workflow_loading.html      # Loading/processing page
│   ├── questionnaire.html         # Dynamic questionnaire
│   ├── clinical_trials.html       # Trials listing
│   ├── favorites.html             # Saved trials
│   └── components/
│       ├── sidebar.html           # Navigation sidebar
│       └── trial_card.html        # Reusable trial card
├── static/                        # CSS, JS, images
│   └── styles.css                 # Main stylesheet (responsive)
├── documentation/                 # Detailed documentation
│   ├── ARCHITECTURE.md            # System architecture and diagrams
│   ├── MEMORY_ERROR_HANDLING.md   # Memory and error handling guide
│   ├── IMPLEMENTATION_SUMMARY.md  # Technical implementation details
│   ├── QUICK_START.md             # Quick start guide
│   ├── paper/                     # Research papers
│   └── trials docs/               # ClinicalTrials.gov schema docs
│       ├── IdentificationModule.csv
│       ├── StatusModule.csv
│       └── SponsorCollaboratorsModule.csv
├── logs/                          # Application logs (auto-created)
├── main.py                        # Application entry point (Flask)
├── requirements.txt               # Python dependencies
├── pyproject.toml                 # Project configuration (uv)
├── .env.example                   # Environment variables template
├── .gitignore                     # Git ignore rules
├── LICENSE                        # MIT License
└── README.md                      # This file
```

## 📚 Documentation

- **[Quick Start Guide](documentation/QUICK_START.md)** - Get started quickly (90 lines)
- **[Architecture Overview](documentation/ARCHITECTURE.md)** - System design and components (271+ lines)
- **[Memory & Error Handling](documentation/MEMORY_ERROR_HANDLING.md)** - Detailed monitoring guide (350+ lines)
- **[Implementation Summary](documentation/IMPLEMENTATION_SUMMARY.md)** - Technical implementation details (196+ lines)

## 🧪 Testing

### Run Test Suite
```bash
python test_memory_system.py
```

Expected output:
- ✓ Manager initialization
- ✓ Agent creation (IllnessAnalyzer)
- ✓ Memory tracking (user input and agent response)
- ✓ System status display
- ✓ Feedback collection
- ✓ Memory export (JSON)
- ✓ Agent context retrieval

### Manual Testing
1. Start the application: `python main.py`
2. Navigate to `http://localhost:5000`
3. Complete a patient profile
4. Answer questionnaire questions
5. Check system status: `http://localhost:5000/monitoring/system/status`
6. Review agent context: `http://localhost:5000/monitoring/agent/IllnessAnalyzer/context`
7. Export memories: `http://localhost:5000/monitoring/memory/export`

### Integration Testing
- Test illness analysis with various medical descriptions
- Verify trial filtering with different patient profiles
- Test question generation for multiple trials
- Validate explanation quality scores
- Test language detection and translation
- Verify favorites persistence across sessions

## 🐛 Troubleshooting

### Agent Not Found Error
- Verify your `MISTRAL_AGENT_ID` is correct in `.env`
- Ensure the agent exists in your Mistral AI console
- Check API key permissions
- Verify agent model is `mistral-small-latest` or higher

### Memory Growing Too Large
- Reduce `max_entries` in AgentMemory initialization (default: 200)
- Export and clear memories periodically via monitoring endpoint
- Monitor memory usage in system status

### Too Many Errors
- Check monitoring endpoints for error patterns
- Review agent prompts and response models in [src/services/](src/services/)
- Verify network connectivity to Mistral API
- Check error logs in [logs/](logs/) directory
- Verify JSON response format from agents

### Language Detection Issues
- Ensure user input is substantial enough (minimum 10-20 words)
- Check supported languages in [src/services/language_service.py](src/services/language_service.py)
- Verify language detection prompt in LanguageService
- Test with clear language-specific text

### Explanation Quality Issues
- Check comprehension scores in explanation responses
- Review evaluation criteria in [src/services/explanation_service.py](src/services/explanation_service.py)
- Adjust rewrite attempts (default: 3)
- Verify explanation prompts are clear and specific

### Session Timeout
- Sessions expire after inactivity
- Re-enter patient profile if session lost
- Check Flask session configuration in [main.py](main.py)

## 🔒 Security Notes

- **API Keys**: Keep your `.env` file secure and never commit it to version control
- **Environment Variables**: Store API keys in environment variables, not code
- **HTTPS**: Use HTTPS in production deployments
- **Rate Limiting**: Implement rate limiting for production (Flask-Limiter recommended)
- **Input Sanitization**: User inputs are processed through Pydantic models
- **Session Security**: Flask sessions use secure cookies (configure SECRET_KEY in production)
- **CORS**: Configure CORS policies for production
- **Logging**: Sensitive data is not logged (check [src/logger.py](src/logger.py))

## 🚧 Future Enhancements

- [ ] Persistent memory storage (database integration - PostgreSQL/MongoDB)
- [ ] Real-time monitoring dashboard (WebSocket-based)
- [ ] Advanced analytics and reporting (trial match trends, success rates)
- [ ] Session recovery from memories (auto-restore interrupted workflows)
- [ ] Automated prompt tuning based on error patterns (A/B testing)
- [ ] Email notifications for matched trials (SMTP integration)
- [ ] PDF report generation (trial match summaries)
- [ ] Clinical trial updates notifications (monitor ClinicalTrials.gov)
- [ ] Multi-user support with authentication (OAuth2)
- [ ] Batch processing for multiple patients (researcher tools)
- [ ] Integration with EHR systems (HL7 FHIR)
- [ ] Mobile app (React Native)

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable (see [test_memory_system.py](test_memory_system.py))
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guide
- Use type hints for function signatures
- Add docstrings for classes and methods
- Test with multiple patient profiles
- Update documentation for new features

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details

Copyright (c) 2026 gyxcit

## 🙏 Acknowledgments

- **Mistral AI** for providing the agent platform and API
- **ClinicalTrials.gov** for comprehensive trial data (via API)
- **Flask** for the lightweight web framework
- **Loguru** for beautiful and informative logging
- **Pydantic** for data validation and structured responses
- **Contributors** to this open-source project

---

**Need Help?** 
- Check the [documentation](documentation/) folder
- Review [QUICK_START.md](documentation/QUICK_START.md) for common tasks
- Open an issue on GitHub with detailed error logs
- Contact: [Your Contact Information]

**Project Statistics:**
- ~1,779 lines of new/modified code for memory and error handling
- 7 core services for AI-powered matching
- 5 Flask blueprints for modular routing
- 10+ HTML templates with responsive design
- 200+ memory entries tracked automatically
- 4 error severity levels for robust handling
