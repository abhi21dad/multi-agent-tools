# LangGraph Chatbot

A powerful multi-tool AI chatbot built with LangGraph, LangChain, and OpenAI that integrates with Gmail, Google Drive, Twitter/X, and provides general utilities like web search, calculator, and stock price lookups.

## ⚠️ Important Security Notice

**Before deploying or sharing this project:**
1. Never commit your `.env` file
2. Use the provided `.env.example` as a template
3. Generate strong authentication tokens (use: `openssl rand -hex 32`)
4. Keep all API keys and credentials secret
5. Review [SECURITY.md](SECURITY.md) for security best practices

## Features

### 🤖 AI-Powered Chat Interface
- Natural language conversation with context retention
- Conversation history management with SQLite persistence
- Automatic conversation title generation

### 📧 Gmail Integration
- Send emails from your Gmail account
- Read and search emails
- List recent inbox messages

### 📁 Google Drive Integration
- Create and write files to Google Drive
- Read file contents
- List files and folders

### 🐦 Twitter/X Integration
- Post tweets directly from the chatbot
- Automated social media updates

### 💾 Local File System
- Secure sandboxed file operations
- Create, read, and list files
- Support for code file generation

### 🔧 General Utilities
- **Web Search**: DuckDuckGo integration for real-time information
- **Calculator**: Basic arithmetic operations
- **Stock Prices**: Real-time stock quotes via Alpha Vantage API

## Architecture

The project uses a microservices architecture where the main chatbot communicates with separate Flask servers for each integration:

```
┌─────────────────┐
│  Streamlit UI   │
│  (Frontend)     │
└────────┬────────┘
         │
         v
┌─────────────────┐
│   LangGraph     │
│   Chatbot       │
│   (Backend)     │
└────────┬────────┘
         │
         ├──────> Gmail Server (Port 5004)
         ├──────> Google Drive Server (Port 5003)
         ├──────> Twitter Server (Port 5001)
         └──────> File System Server (Port 5002)
```

## Prerequisites

- Python 3.11 or higher
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))
- Google Cloud credentials for Gmail/Drive (optional)
- Twitter API credentials (optional)
- Alpha Vantage API key for stock data (optional)

## Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd langgraph-chatbot
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys and tokens
nano .env  # or use your preferred editor
```

**Required variables:**
- `OPENAI_API_KEY`: Your OpenAI API key
- `FILE_SERVER_AUTH_TOKEN`: Generate with `openssl rand -hex 32`
- `GMAIL_SERVER_AUTH_TOKEN`: Generate with `openssl rand -hex 32`
- `GOOGLE_DRIVE_SERVER_AUTH_TOKEN`: Generate with `openssl rand -hex 32`
- `TWITTER_COMMAND_SERVER_AUTH_TOKEN`: Generate with `openssl rand -hex 32`

**Optional variables:**
- Twitter API credentials (for Twitter integration)
- Alpha Vantage API key (for stock price lookups)
- LangSmith API key (for debugging and tracing)

### 5. Set Up Google OAuth (Optional)

For Gmail and Google Drive integration:

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Gmail API and Google Drive API
3. Create OAuth 2.0 credentials
4. Download credentials as `credentials.json` in the project root
5. Run the authenticator script:

```bash
python one_time_gmail_authenticator.py
```

This will create `token_gmail.json` and `token_drive.json` files.

### 6. Start the Services

You need to start each service in a separate terminal:

**Terminal 1: File Server**
```bash
python file_command_server1.py
```

**Terminal 2: Gmail Server** (if using Gmail integration)
```bash
python gmail_command_server2.py
```

**Terminal 3: Google Drive Server** (if using Drive integration)
```bash
python google_drive_command_server.py
```

**Terminal 4: Twitter Server** (if using Twitter integration)
```bash
python twitter_command_server.py
```

**Terminal 5: Streamlit Frontend**
```bash
streamlit run frontend_title.py
```

The chatbot will be available at http://localhost:8501

## Docker Deployment (Recommended for Production)

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

## Configuration

See `.env.example` for all available configuration options. Key settings:

- **Environment**: `development`, `staging`, or `production`
- **Debug**: Enable/disable debug mode
- **Database**: Path to SQLite database file
- **Service URLs**: Configure endpoints for each microservice
- **CORS**: Configure allowed origins for production
- **Rate Limiting**: Set API rate limits

## Usage Examples

### Basic Chat
```
You: What's the weather like today?
Bot: [Uses web search to find current weather]
```

### Send Email
```
You: Send an email to john@example.com with subject "Meeting tomorrow" 
     and tell him the meeting is at 2 PM
Bot: [Sends email via Gmail integration]
```

### Create a File
```
You: Create a Python script that prints "Hello World"
Bot: [Creates hello.py in the file sandbox]
```

### Post a Tweet
```
You: Tweet "Just built an awesome AI chatbot with LangGraph!"
Bot: [Posts to your Twitter account]
```

### Stock Price
```
You: What's the current price of Apple stock?
Bot: [Fetches AAPL stock price from Alpha Vantage]
```

## Development

### Project Structure

```
langgraph-chatbot/
├── config.py                    # Centralized configuration
├── gmail3.py                    # Main chatbot backend
├── frontend_title.py            # Streamlit UI
├── file_command_server1.py      # File system service
├── gmail_command_server2.py     # Gmail service
├── google_drive_command_server.py  # Google Drive service
├── twitter_command_server.py    # Twitter service
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (not in git)
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
└── file_sandbox/                # Sandboxed file storage
```

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## Security

- All sensitive credentials are stored in environment variables
- Inter-service communication uses authentication tokens
- File system operations are sandboxed
- See [SECURITY.md](SECURITY.md) for detailed security information

## Troubleshooting

### "Configuration Error" on startup

Make sure your `.env` file has all required variables set. Run:
```bash
python config.py
```
This will validate your configuration and show any missing variables.

### Services can't connect

Ensure all services are running on their designated ports:
- File Server: 5002
- Google Drive Server: 5003
- Gmail Server: 5004
- Twitter Server: 5001

Check if ports are already in use:
```bash
lsof -i :5001  # Check if port 5001 is in use
```

### Google OAuth Not Working

1. Make sure `credentials.json` exists in the project root
2. Run the authenticator script: `python one_time_gmail_authenticator.py`
3. Follow the browser authorization flow
4. Check that `token_gmail.json` and `token_drive.json` were created

### Rate Limiting Issues

If you're hitting API rate limits, adjust these in your `.env`:
```
RATE_LIMIT_PER_MINUTE=30
```

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

[Add your license here]

## Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph)
- Powered by [OpenAI](https://openai.com/)
- UI built with [Streamlit](https://streamlit.io/)

## Support

For issues, questions, or contributions, please open an issue on GitHub.
