# AnyQB - Mobile QuickBooks Chat Interface

## Overview
A fast, mobile-first web application that uses Claude API to execute QuickBooks commands through natural language. Built on the proven architecture from claude chat project with enhanced structure for scalability.

## Project Structure
```
anyqb/
├── src/                    # Source code
│   ├── api/               # API layer (FastAPI server, Claude integration)
│   │   ├── server.py      # Main FastAPI application
│   │   ├── claude.py      # Claude API integration
│   │   └── routes.py      # API endpoints
│   ├── ui/                # Frontend (HTML, mobile-optimized interface)
│   │   ├── index.html     # Main chat interface
│   │   ├── components.js  # UI components
│   │   └── chat.js        # Chat functionality
│   ├── qb/                # QuickBooks integration
│   │   ├── connector.py   # QB MCP connection handler
│   │   ├── commands.py    # QB command definitions
│   │   └── executor.py    # Command execution logic
│   ├── utils/             # Utility functions
│   │   ├── auth.py        # Authentication utilities
│   │   ├── logger.py      # Logging setup
│   │   └── validators.py  # Input validation
│   └── config/            # Configuration
│       ├── settings.py    # App settings
│       └── commands.json  # QB command mappings
├── public/                # Static assets
│   ├── css/              # Stylesheets
│   ├── js/               # Client-side scripts
│   └── assets/           # Images, icons
├── tests/                # Test suites
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── e2e/            # End-to-end tests
├── docs/                # Documentation
├── requirements.txt     # Python dependencies
├── package.json        # Node dependencies (if needed)
├── .env.example        # Environment variables template
├── CLAUDE.md          # Claude-specific instructions
└── README.md          # This file
```

## Architecture
```
User → Mobile Web UI → FastAPI Server → Claude API → QB MCP → QuickBooks Data
```

### Key Components
1. **Mobile Web UI**: Touch-optimized, dark theme, responsive design
2. **FastAPI Server**: Handles requests, manages sessions, coordinates API calls
3. **Claude API**: Natural language processing for QB commands
4. **QB MCP**: Direct connection to QuickBooks via anyQBMCP codebase
5. **Response Handler**: Formats and returns data to UI

## Features
- **Fast Response**: ~0.8-0.9 seconds using Claude API
- **Mobile First**: Designed for mobile devices from the ground up
- **60+ QB Commands**: Full QuickBooks command coverage
- **Natural Language**: Chat with QB using everyday language
- **Secure**: API key management, authentication support
- **Scalable**: Modular architecture for easy expansion

## Technology Stack
- **Backend**: Python, FastAPI, Uvicorn
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **API**: Claude API (Anthropic)
- **QB Integration**: anyQBMCP codebase
- **Testing**: Pytest, Selenium
- **Deployment**: Docker-ready

## Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js (optional, for build tools)
- Access to anyQBMCP codebase
- Claude API key

### Installation
```bash
# Clone the repository
cd C:\Users\nando\Projects\anyqb

# Install Python dependencies
pip install -r requirements.txt

# Copy environment template
copy .env.example .env

# Update .env with your API keys and paths
```

### Configuration
1. Update `ANTHROPIC_API_KEY` in `.env`
2. Set `QB_MCP_PATH` to your anyQBMCP location
3. Configure server port (default: 8000)

### Running the Application
```bash
# Start the server
python src/api/server.py

# Open in browser
http://localhost:8000
```

## Development Guidelines
- Mobile-first approach for all UI changes
- Test on mobile viewport (390x844) before desktop
- Use ASCII characters only (no Unicode)
- Follow existing code conventions
- Write tests for new features

## Testing
```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with coverage
pytest --cov=src
```

## API Endpoints
- `GET /` - Serve mobile web interface
- `POST /api/chat` - Process chat messages
- `GET /api/health` - Health check
- `GET /api/commands` - List available commands
- `POST /api/execute` - Execute QB command directly

## Security Considerations
- API keys stored in environment variables
- Claude restricted to QB commands only
- Input validation on all endpoints
- Rate limiting available
- Authentication ready (not implemented)

## Performance Targets
- Response time: < 1 second
- Mobile page load: < 2 seconds
- Command execution: < 1.5 seconds
- Error recovery: < 500ms

## Future Enhancements
- [ ] User authentication system
- [ ] Command history and favorites
- [ ] Voice input support
- [ ] Offline mode with caching
- [ ] Multi-tenant support
- [ ] Real-time QB data sync
- [ ] Export chat history
- [ ] Command shortcuts

## License
Private project - All rights reserved

## Support
Contact: nando936