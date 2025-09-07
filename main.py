from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime
import json
import re
import os

app = FastAPI(title="Bot Deployment API", version="1.0.0")

# Get base URL from environment or use default
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (use database in production)
deployments: Dict[str, Dict] = {}
logs: Dict[str, List[Dict]] = {}

# Pydantic models
class BotConfig(BaseModel):
    title: Optional[str] = None
    primaryColor: Optional[str] = None
    backgroundColor: Optional[str] = None
    apiEndpoint: Optional[str] = None
    welcomeMessage: Optional[str] = None
    refreshInterval: Optional[int] = None

class CreateBotRequest(BaseModel):
    botname: str
    frontendType: str  # "LLM" or "Logs"
    config: BotConfig

class ChatRequest(BaseModel):
    botname: str
    userMessage: str
    timestamp: str

class LogsRequest(BaseModel):
    botname: str
    level: str = "all"
    limit: int = 50
    timestamp: str

class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str
    botname: str

# Utility functions
def generate_subdomain(botname: str) -> str:
    """Generate a clean subdomain from botname"""
    return re.sub(r'[^a-z0-9]', '-', botname.lower())

def generate_llm_html(config: Dict) -> str:
    """Generate HTML template for LLM chat frontend"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.get('title', 'AI Chat')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: {config.get('backgroundColor', '#f5f5f5')};
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .chat-container {{
            width: 100%;
            max-width: 600px;
            height: 80vh;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        .chat-header {{
            background: {config.get('primaryColor', '#007bff')};
            color: white;
            padding: 1rem;
            text-align: center;
            font-weight: 600;
        }}
        .messages {{
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
            background: #fafafa;
        }}
        .message {{
            margin-bottom: 1rem;
            padding: 0.8rem 1rem;
            border-radius: 8px;
            max-width: 80%;
        }}
        .user-message {{
            background: {config.get('primaryColor', '#007bff')};
            color: white;
            margin-left: auto;
        }}
        .bot-message {{
            background: white;
            border: 1px solid #e0e0e0;
        }}
        .input-area {{
            padding: 1rem;
            background: white;
            border-top: 1px solid #e0e0e0;
            display: flex;
            gap: 0.5rem;
        }}
        .message-input {{
            flex: 1;
            padding: 0.8rem;
            border: 1px solid #ddd;
            border-radius: 6px;
            outline: none;
        }}
        .send-btn {{
            padding: 0.8rem 1.5rem;
            background: {config.get('primaryColor', '#007bff')};
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
        }}
        .send-btn:hover {{
            opacity: 0.9;
        }}
        .typing {{
            font-style: italic;
            opacity: 0.7;
        }}
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            {config.get('title', 'AI Assistant')}
        </div>
        <div class="messages" id="messages">
            <div class="message bot-message">
                {config.get('welcomeMessage', 'Hello! How can I help you today?')}
            </div>
        </div>
        <div class="input-area">
            <input type="text" class="message-input" id="messageInput" placeholder="Type your message...">
            <button class="send-btn" onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        const messagesContainer = document.getElementById('messages');
        const messageInput = document.getElementById('messageInput');
        const API_ENDPOINT = '{config.get('apiEndpoint', BASE_URL + '/api/chat')}';
        const BOTNAME = '{config.get('botname', 'default')}';

        function addMessage(content, isUser = false) {{
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${{isUser ? 'user-message' : 'bot-message'}}`;
            messageDiv.textContent = content;
            messagesContainer.appendChild(messageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }}

        function showTyping() {{
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message bot-message typing';
            typingDiv.textContent = 'Bot is typing...';
            typingDiv.id = 'typing-indicator';
            messagesContainer.appendChild(typingDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }}

        function removeTyping() {{
            const typing = document.getElementById('typing-indicator');
            if (typing) typing.remove();
        }}

        async function sendMessage() {{
            const message = messageInput.value.trim();
            if (!message) return;

            addMessage(message, true);
            messageInput.value = '';
            showTyping();

            try {{
                const response = await fetch(API_ENDPOINT, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        botname: BOTNAME,
                        userMessage: message,
                        timestamp: new Date().toISOString()
                    }})
                }});

                const data = await response.json();
                removeTyping();

                if (data.botResponse) {{
                    addMessage(data.botResponse);
                }} else {{
                    addMessage('Sorry, I encountered an error. Please try again.');
                }}
            }} catch (error) {{
                removeTyping();
                addMessage('Connection error. Please check your internet and try again.');
                console.error('Chat error:', error);
            }}
        }}

        messageInput.addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') sendMessage();
        }});
    </script>
</body>
</html>"""

def generate_logs_html(config: Dict) -> str:
    """Generate HTML template for Logs dashboard"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.get('title', 'Logs Dashboard')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: {config.get('backgroundColor', '#f5f5f5')};
            padding: 1rem;
        }}
        .dashboard {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .title {{
            color: {config.get('primaryColor', '#333')};
            font-size: 1.5rem;
            font-weight: 600;
        }}
        .controls {{
            background: white;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            display: flex;
            gap: 1rem;
            align-items: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .filter-select, .refresh-btn {{
            padding: 0.5rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            outline: none;
        }}
        .refresh-btn {{
            background: {config.get('primaryColor', '#007bff')};
            color: white;
            cursor: pointer;
            font-weight: 500;
        }}
        .logs-container {{
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .logs-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .logs-table th {{
            background: #f8f9fa;
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
            font-weight: 600;
        }}
        .logs-table td {{
            padding: 0.8rem 1rem;
            border-bottom: 1px solid #dee2e6;
        }}
        .log-level {{
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 500;
        }}
        .level-info {{ background: #d1ecf1; color: #0c5460; }}
        .level-success {{ background: #d4edda; color: #155724; }}
        .level-warning {{ background: #fff3cd; color: #856404; }}
        .level-error {{ background: #f8d7da; color: #721c24; }}
        .auto-refresh {{
            margin-left: auto;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #28a745;
        }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1 class="title">{config.get('title', 'Bot Logs Dashboard')}</h1>
        </div>
        
        <div class="controls">
            <select class="filter-select" id="levelFilter">
                <option value="all">All Levels</option>
                <option value="info">Info</option>
                <option value="success">Success</option>
                <option value="warning">Warning</option>
                <option value="error">Error</option>
            </select>
            
            <button class="refresh-btn" onclick="fetchLogs()">Refresh</button>
            
            <div class="auto-refresh">
                <div class="status-dot"></div>
                <span>Auto-refresh: {config.get('refreshInterval', 3000)}ms</span>
            </div>
        </div>
        
        <div class="logs-container">
            <table class="logs-table">
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Level</th>
                        <th>Message</th>
                        <th>Bot</th>
                    </tr>
                </thead>
                <tbody id="logsTableBody">
                    <tr>
                        <td colspan="4" style="text-align: center; padding: 2rem;">
                            Loading logs...
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const API_ENDPOINT = '{config.get('apiEndpoint', BASE_URL + '/api/logs')}';
        const BOTNAME = '{config.get('botname', 'default')}';
        const REFRESH_INTERVAL = {config.get('refreshInterval', 3000)};
        
        function formatTimestamp(timestamp) {{
            return new Date(timestamp).toLocaleString();
        }}
        
        function getLevelClass(level) {{
            return `level-${{level}}`;
        }}
        
        function renderLogs(logs) {{
            const tbody = document.getElementById('logsTableBody');
            
            if (!logs || logs.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 2rem;">No logs found</td></tr>';
                return;
            }}
            
            tbody.innerHTML = logs.map(log => `
                <tr>
                    <td>${{formatTimestamp(log.timestamp)}}</td>
                    <td><span class="log-level ${{getLevelClass(log.level)}}">${{log.level.toUpperCase()}}</span></td>
                    <td>${{log.message}}</td>
                    <td>${{log.botname || BOTNAME}}</td>
                </tr>
            `).join('');
        }}
        
        async function fetchLogs() {{
            const level = document.getElementById('levelFilter').value;
            
            try {{
                const response = await fetch(API_ENDPOINT, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        botname: BOTNAME,
                        level: level,
                        limit: 50,
                        timestamp: new Date().toISOString()
                    }})
                }});
                
                const data = await response.json();
                renderLogs(data.logs);
            }} catch (error) {{
                console.error('Failed to fetch logs:', error);
                document.getElementById('logsTableBody').innerHTML = 
                    '<tr><td colspan="4" style="text-align: center; padding: 2rem; color: #dc3545;">Failed to load logs</td></tr>';
            }}
        }}
        
        // Initial load
        fetchLogs();
        
        // Auto-refresh
        setInterval(fetchLogs, REFRESH_INTERVAL);
        
        // Filter change handler
        document.getElementById('levelFilter').addEventListener('change', fetchLogs);
    </script>
</body>
</html>"""

# API Routes

@app.get("/", response_class=HTMLResponse)
async def root():
    """Main landing page"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Bot Deployment Platform</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 2rem auto; padding: 2rem; }
            .header { text-align: center; margin-bottom: 2rem; }
            .api-section { background: #f5f5f5; padding: 1.5rem; border-radius: 8px; margin: 1rem 0; }
            code { background: #e0e0e0; padding: 0.2rem 0.4rem; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🤖 Bot Deployment Platform</h1>
            <p>Create and deploy bot frontends instantly!</p>
        </div>
        
        <div class="api-section">
            <h2>🚀 Quick Start</h2>
            <p>Create a chat bot:</p>
            <code>POST /api/create</code>
            <pre>{
  "botname": "my-bot",
  "frontendType": "LLM",
  "config": {
    "title": "My AI Assistant",
    "primaryColor": "#007bff"
  }
}</pre>
        </div>
        
        <div class="api-section">
            <h2>📚 API Documentation</h2>
            <p><a href="/docs">View Interactive API Docs</a></p>
        </div>
        
        <div class="api-section">
            <h2>📊 All Deployments</h2>
            <p><a href="/api/deployments">View All Deployed Bots</a></p>
        </div>
    </body>
    </html>
    """)

@app.post("/api/create")
async def create_bot(request: CreateBotRequest):
    """Create a new bot frontend"""
    try:
        subdomain = generate_subdomain(request.botname)
        
        # Check if botname already exists
        if subdomain in deployments:
            return {
                "error": "Botname already exists",
                "existing_url": f"{BASE_URL}/bot/{subdomain}"
            }
        
        # Generate HTML based on frontend type
        config = request.config.dict()
        config['botname'] = request.botname
        
        if request.frontendType == "LLM":
            html = generate_llm_html(config)
        elif request.frontendType == "Logs":
            html = generate_logs_html(config)
        else:
            raise HTTPException(
                status_code=400,
                detail='Invalid frontendType. Must be "LLM" or "Logs"'
            )
        
        # Store deployment info
        deployment = {
            "id": str(uuid.uuid4()),
            "botname": request.botname,
            "subdomain": subdomain,
            "frontendType": request.frontendType,
            "config": config,
            "html": html,
            "created": datetime.now().isoformat(),
            "status": "deployed"
        }
        
        deployments[subdomain] = deployment
        
        return {
            "success": True,
            "url": f"{BASE_URL}/bot/{subdomain}",
            "botname": request.botname,
            "frontendType": request.frontendType,
            "status": "deployed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/bot/{subdomain}", response_class=HTMLResponse)
async def serve_bot_frontend(subdomain: str):
    """Serve bot frontend HTML"""
    if subdomain not in deployments:
        raise HTTPException(status_code=404, detail=f"Bot '{subdomain}' not found")
    
    deployment = deployments[subdomain]
    return HTMLResponse(content=deployment["html"])

@app.get("/api/status/{subdomain}")
async def get_deployment_status(subdomain: str):
    """Get deployment status"""
    if subdomain not in deployments:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    deployment = deployments[subdomain]
    return {
        "botname": deployment["botname"],
        "status": deployment["status"],
        "created": deployment["created"],
        "frontendType": deployment["frontendType"]
    }

@app.get("/api/deployments")
async def list_deployments():
    """List all deployments"""
    all_deployments = []
    
    for d in deployments.values():
        deployment_info = {
            "botname": d["botname"],
            "subdomain": d["subdomain"],
            "frontendType": d["frontendType"],
            "status": d["status"],
            "created": d["created"],
            "url": f"{BASE_URL}/bot/{d['subdomain']}"
        }
        all_deployments.append(deployment_info)
    
    return {"deployments": all_deployments}

@app.delete("/api/delete/{subdomain}")
async def delete_deployment(subdomain: str):
    """Delete deployment"""
    if subdomain not in deployments:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    deployment = deployments[subdomain]
    del deployments[subdomain]
    
    return {
        "success": True,
        "message": f"Bot '{deployment['botname']}' deleted successfully"
    }

@app.post("/api/chat")
async def handle_chat(request: ChatRequest):
    """Handle chat messages (replace with your AI logic)"""
    # Log the conversation
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "level": "info",
        "message": f"User: {request.userMessage}",
        "botname": request.botname
    }
    
    if request.botname not in logs:
        logs[request.botname] = []
    logs[request.botname].append(log_entry)
    
    # Simple echo response (REPLACE THIS with your AI logic)
    bot_response = f"You said: {request.userMessage}"
    
    # Add some variety to responses
    if "hello" in request.userMessage.lower():
        bot_response = "Hello! Nice to meet you! 👋"
    elif "how are you" in request.userMessage.lower():
        bot_response = "I'm doing great! Thanks for asking. How can I help you today?"
    elif "help" in request.userMessage.lower():
        bot_response = "I'm here to help! Ask me anything and I'll do my best to assist you."
    
    # Log the response
    logs[request.botname].append({
        "timestamp": datetime.now().isoformat(),
        "level": "success",
        "message": f"Bot: {bot_response}",
        "botname": request.botname
    })
    
    return {
        "botResponse": bot_response,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/logs")
async def get_logs(request: LogsRequest):
    """Get logs for a bot"""
    all_logs = logs.get(request.botname, [])
    
    # Filter by level if specified
    if request.level and request.level != "all":
        all_logs = [log for log in all_logs if log["level"] == request.level]
    
    # Limit results
    limited_logs = all_logs[-request.limit:]
    
    return {
        "logs": list(reversed(limited_logs)),  # Most recent first
        "count": len(limited_logs)
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "deployments": len(deployments),
        "base_url": BASE_URL,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
