# AnyQB Quick Setup Guide

## 1. Prerequisites
- Python 3.8 or higher
- Git Bash or Command Prompt
- Claude API key from Anthropic

## 2. Quick Start

### Option A: Using the start script
```bash
cd C:\Users\nando\Projects\anyqb
python start.py
```

### Option B: Manual setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file
copy .env.example .env

# 3. Edit .env and add your API key
notepad .env

# 4. Start the server
python src/api/server.py
```

## 3. Configuration

### Required: Claude API Key
1. Get your API key from: https://console.anthropic.com/
2. Add to .env file:
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY-HERE
   ```

### Optional: QuickBooks Path
If you have the anyQBMCP codebase elsewhere:
```
QB_MCP_PATH=C:\Your\Path\To\anyQBMCP
```

## 4. Testing

### Test QB Connection
```bash
python test_qb.py
```

### Test the Web Interface
1. Start the server
2. Open browser to: http://localhost:8000
3. Try commands like:
   - "show jaciel's bill"
   - "list vendors"
   - "get week summary"

## 5. Mobile Access

### Same Network
1. Find your computer's IP address:
   ```bash
   ipconfig | grep "IPv4"
   ```
2. On your phone, open browser to:
   ```
   http://YOUR-IP:8000
   ```

### Remote Access (Advanced)
Use ngrok or similar tunneling service:
```bash
ngrok http 8000
```

## 6. Common Issues

### "QB not connected"
- This is normal if QuickBooks is not installed
- The app will work with simulated data

### "Claude API not configured"
- Check your API key in .env file
- Make sure there are no extra spaces

### Port already in use
- Change port in .env:
  ```
  SERVER_PORT=8001
  ```

### Unicode errors on Windows
- The app uses ASCII characters only
- This should not be an issue

## 7. Development

### Project Structure
```
anyqb/
├── src/
│   ├── api/         # FastAPI server & Claude
│   ├── ui/          # Web interface
│   ├── qb/          # QuickBooks integration
│   └── config/      # Configuration
├── start.py         # Quick start script
├── test_qb.py       # Test QB connection
└── .env            # Your configuration
```

### Adding New Commands
1. Edit `src/config/commands.json`
2. Update `src/qb/connector.py`
3. Update Claude prompt in `src/api/claude.py`

### Testing Changes
```bash
# The server auto-reloads on changes
python src/api/server.py

# Or use the start script
python start.py
```

## 8. Performance

Expected response times:
- Claude API: ~0.8-0.9 seconds
- QB Command: ~0.1-0.2 seconds
- Total: < 1.5 seconds

## 9. Security

- Never commit .env file
- Keep API keys secret
- Use environment variables
- Claude is restricted to QB commands only

## 10. Support

For issues or questions:
- Check the README.md
- Review CLAUDE.md for AI instructions
- Test with test_qb.py first