import os
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from dotenv import load_dotenv
import sqlite3
import requests

# --- Configuration ---
load_dotenv()
# ... (all your other server URLs and tokens remain here) ...
FILE_SERVER_URL = "http://127.0.0.1:5002"
FILE_AUTH_TOKEN = os.getenv("FILE_SERVER_AUTH_TOKEN")
GDRIVE_SERVER_URL = "http://127.0.0.1:5003"
GDRIVE_AUTH_TOKEN = os.getenv("GOOGLE_DRIVE_SERVER_AUTH_TOKEN")
GMAIL_SERVER_URL = "http://127.0.0.1:5004"
GMAIL_AUTH_TOKEN = os.getenv("GMAIL_SERVER_AUTH_TOKEN")


# -------------------
# 1. LLM
# -------------------
# We use the standard LLM for conversation
llm = ChatOpenAI()
# We'll use a specific, fast model for title generation inside the new tool
title_generation_llm = ChatOpenAI(model="gpt-3.5-turbo")

# -------------------
# 2. Tools
# -------------------

# ... (All of your existing tools: post_tweet, calculator, search, all file/drive/gmail tools remain here) ...
# --- Twitter Tool ---
@tool
def post_tweet(tweet_text: str) -> dict:
    """Use this tool ONLY to post a message to X (formerly Twitter)."""
    server_url = "http://127.0.0.1:5001/tweet"
    auth_token = os.getenv("TWITTER_COMMAND_SERVER_AUTH_TOKEN")
    if not auth_token:
        return {"error": "Twitter auth token not configured."}
    payload = {"text": tweet_text, "token": auth_token}
    try:
        response = requests.post(server_url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to connect to Twitter server: {e}"}

# --- General Tools ---
search_tool = DuckDuckGoSearchRun(region="us-en")

@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """Perform a basic arithmetic operation."""
    try:
        ops = {"add": lambda a, b: a + b, "sub": lambda a, b: a - b, "mul": lambda a, b: a * b, "div": lambda a, b: a / b}
        if operation == "div" and second_num == 0:
            return {"error": "Division by zero is not allowed."}
        result = ops[operation](first_num, second_num)
        return {"result": result}
    except (KeyError, Exception) as e:
        return {"error": str(e)}

@tool
def get_stock_price(symbol: str) -> dict:
    """Fetch latest stock price for a given symbol."""
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=C9PE94QUEW9VWGFM"
    try:
        r = requests.get(url)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch stock price: {e}"}

# --- Local Filesystem Tools ---
@tool
def list_files(path: str = '.') -> dict:
    """
    Lists files and directories. Accessible locations:
    - Relative paths: defaults to file_sandbox folder
    - ~/Downloads, ~/Documents, ~/Desktop: use absolute paths like ~/Downloads/folder
    """
    payload = {"path": path, "token": FILE_AUTH_TOKEN}
    try:
        response = requests.post(f"{FILE_SERVER_URL}/list", json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to connect to file server: {e}"}

@tool
def read_file(path: str) -> dict:
    """
    Reads content of a file. Accessible locations:
    - Relative paths: defaults to file_sandbox folder
    - ~/Downloads, ~/Documents, ~/Desktop: use absolute paths like ~/Downloads/file.txt
    """
    payload = {"path": path, "token": FILE_AUTH_TOKEN}
    try:
        response = requests.post(f"{FILE_SERVER_URL}/read", json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to connect to file server: {e}"}

@tool
def write_file(path: str, content: str, mode: str = 'overwrite') -> dict:
    """
    Creates, writes, or appends to a file. Accessible locations:
    - Relative paths (like 'file.txt'): saves to file_sandbox folder
    - ~/Downloads/file.txt: saves to user's Downloads folder
    - ~/Documents/file.txt: saves to user's Documents folder  
    - ~/Desktop/file.txt: saves to user's Desktop
    
    When user asks to save to Downloads, Documents, or Desktop, use the absolute path format.
    Example: write_file("~/Downloads/myfile.txt", "content here")
    """
    payload = {"path": path, "content": content, "mode": mode, "token": FILE_AUTH_TOKEN}
    try:
        response = requests.post(f"{FILE_SERVER_URL}/write", json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to connect to file server: {e}"}
    
# --- Google Drive Tools ---
@tool
def list_google_drive_files() -> dict:
    """Lists recent files and folders in your Google Drive."""
    payload = {"token": GDRIVE_AUTH_TOKEN}
    try:
        response = requests.post(f"{GDRIVE_SERVER_URL}/list", json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to connect to Google Drive server: {e}"}

@tool
def read_google_drive_file(filename: str) -> dict:
    """Reads the text content of a file from Google Drive."""
    payload = {"filename": filename, "token": GDRIVE_AUTH_TOKEN}
    try:
        response = requests.post(f"{GDRIVE_SERVER_URL}/read", json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to connect to Google Drive server: {e}"}

@tool
def write_to_google_drive(filename: str, content: str) -> dict:
    """
    Creates or overwrites a file in Google Drive with content YOU ALREADY HAVE.
    Use this ONLY when the user provides the exact content to write.
    
    DO NOT use this for: conflicts, news, current events, or any topic requiring research.
    For those topics, use research_and_write_to_drive instead.
    """
    payload = {"filename": filename, "content": content, "token": GDRIVE_AUTH_TOKEN}
    try:
        response = requests.post(f"{GDRIVE_SERVER_URL}/write", json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to connect to Google Drive server: {e}"}

@tool
def research_and_write_to_drive(filename: str, topic: str) -> dict:
    """
    ALWAYS use this tool when the user asks to write about:
    - Conflicts (e.g., USA-Iran, Russia-Ukraine, any country conflicts)
    - Current events or recent news
    - Any topic that requires up-to-date information from the web
    - Topics the user hasn't provided specific content for
    
    This tool will:
    1. Search the web for recent information about the topic
    2. Generate well-researched content based on search results  
    3. Write the content to a Google Drive file
    
    Examples that MUST use this tool:
    - "Write about conflicts between countries"
    - "Add recent conflict information to Google Drive"
    - "Create a file about USA-Iran situation"
    """
    try:
        # Step 1: Search for recent information
        search_query = f"{topic} recent news 2024 2025"
        search_results = search_tool.run(search_query)
        
        # Step 2: Use LLM to create well-researched content
        prompt = f"""Based on the following search results about "{topic}", write a comprehensive, 
well-structured document with approximately 50-100 lines of content. Include:
- Background/Overview
- Key facts and recent developments
- Different perspectives
- Conclusion

Search Results:
{search_results}

Write the content in a clear, informative style suitable for a document."""
        
        response = title_generation_llm.invoke(prompt)
        content = response.content
        
        # Step 3: Write to Google Drive
        payload = {"filename": filename, "content": content, "token": GDRIVE_AUTH_TOKEN}
        drive_response = requests.post(f"{GDRIVE_SERVER_URL}/write", json=payload)
        drive_response.raise_for_status()
        
        return {
            "success": True,
            "message": f"Successfully researched '{topic}' and wrote to '{filename}'",
            "content_preview": content[:500] + "..." if len(content) > 500 else content
        }
    except Exception as e:
        return {"error": f"Failed to research and write: {str(e)}"}


# --- Gmail Tools ---
@tool
def send_email(recipient: str, subject: str, body: str) -> dict:
    """Use this tool to send an email from your personal Gmail account."""
    payload = {"recipient": recipient, "subject": subject, "body": body, "token": GMAIL_AUTH_TOKEN}
    try:
        response = requests.post(f"{GMAIL_SERVER_URL}/send", json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to connect to the Gmail server: {e}"}

@tool
def list_recent_emails() -> dict:
    """Use this tool to fetch a list of the most recent emails from your Gmail inbox."""
    payload = {"token": GMAIL_AUTH_TOKEN}
    try:
        response = requests.post(f"{GMAIL_SERVER_URL}/list_emails", json=payload)
        response.raise_for_status()
        data = response.json()
        if "emails" in data and data["emails"]:
            formatted_emails = [f"{i+1}. From: {e['from']} | Subject: {e['subject']}" for i, e in enumerate(data['emails'])]
            return {"status": "Success", "emails": "\n".join(formatted_emails)}
        return {"status": "Success", "message": "No recent emails found."}
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to connect to the Gmail server: {e}"}

@tool
def read_email_content(search_query: str) -> dict:
    """
    Use this tool to read the full body content of a specific email from your Gmail inbox.
    You must provide a search query, like the email's subject or sender, to find the email.
    For example: 'Subject: We Got You a Gift' or 'From: MakeMyTrip'.
    """
    payload = {"search_query": search_query, "token": GMAIL_AUTH_TOKEN}
    try:
        response = requests.post(f"{GMAIL_SERVER_URL}/read_email", json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to connect to the Gmail server: {str(e)}"}

# <<< --- NEW TOOL START --- >>>
# This tool is special. It's not meant for the main AI to use.
# It's a utility function we will call directly from our frontend.
def generate_conversation_title(first_message: str) -> str:
    """
    Uses a fast AI model to generate a short, descriptive title for a conversation.
    """
    # The prompt is very specific to get a clean, short title.
    prompt = f"The first message of a new chat is: '{first_message}'. Based on this, what is a short, 3-5 word title for this conversation? Do not use quotes in the title."
    try:
        response = title_generation_llm.invoke(prompt)
        # .content extracts the text from the AI's response
        return response.content.strip()
    except Exception as e:
        print(f"Error generating title: {e}")
        return "New Chat" # Fallback title
# <<< --- NEW TOOL END --- >>>

# --- RAG Tool ---
try:
    from rag_service import search_documents, get_context_for_query, list_uploaded_documents
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("RAG service not available")

@tool
def search_uploaded_documents(query: str) -> dict:
    """
    Search through uploaded PDF documents for relevant information.
    Use this tool when the user asks questions about documents they've uploaded,
    or when they want to find information in their PDFs.
    
    Examples:
    - "What does my contract say about termination?"
    - "Find information about revenue in the uploaded reports"
    - "Search my documents for machine learning concepts"
    """
    if not RAG_AVAILABLE:
        return {"error": "RAG service not available. Please upload documents first."}
    
    try:
        results = search_documents(query, k=5)
        
        if not results:
            return {"message": "No relevant documents found. Please make sure you've uploaded PDFs."}
        
        if len(results) == 1 and "error" in results[0]:
            return {"error": results[0]["error"]}
        
        # Format results for the AI
        formatted = []
        for r in results:
            formatted.append(f"[Source: {r['source']}, Page {r['page']}, Relevance: {r['relevance_score']}]\n{r['content']}")
        
        return {
            "success": True,
            "num_results": len(results),
            "results": "\n\n---\n\n".join(formatted)
        }
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}

@tool
def list_my_documents() -> dict:
    """
    List all PDF documents that have been uploaded and are available for search.
    Use this when the user asks what documents they have uploaded or what's in their knowledge base.
    """
    if not RAG_AVAILABLE:
        return {"error": "RAG service not available."}
    
    try:
        docs = list_uploaded_documents()
        if not docs:
            return {"message": "No documents have been uploaded yet. Upload PDFs using the sidebar."}
        return {
            "success": True,
            "documents": docs,
            "count": len(docs)
        }
    except Exception as e:
        return {"error": str(e)}


@tool
def list_my_capabilities() -> dict:
    """
    Use this tool when the user asks about your tools, capabilities, or what you can do.
    Examples: "what tools do you have?", "what can you do?", "list your capabilities"
    
    DO NOT use list_files for this - that lists files in a folder, not your AI capabilities.
    """
    capabilities = {
        "total_tools": 17,
        "categories": {
            "🔍 Search & Research": [
                "search_tool - Search the web using DuckDuckGo",
                "research_and_write_to_drive - Research a topic and save to Google Drive"
            ],
            "📊 Utilities": [
                "calculator - Perform mathematical calculations",
                "get_stock_price - Get current stock prices"
            ],
            "📁 Local Files": [
                "list_files - List files in a directory",
                "read_file - Read file contents",
                "write_file - Create or modify files (Downloads, Documents, Desktop)"
            ],
            "☁️ Google Drive": [
                "list_google_drive_files - List your Drive files",
                "read_google_drive_file - Read a file from Drive",
                "write_to_google_drive - Create a file in Drive"
            ],
            "📧 Email (Gmail)": [
                "send_email - Send an email",
                "list_recent_emails - View recent emails",
                "read_email_content - Read a specific email"
            ],
            "🐦 Social Media": [
                "post_tweet - Post to Twitter/X"
            ],
            "📚 Knowledge Base (RAG)": [
                "search_uploaded_documents - Search your uploaded PDFs",
                "list_my_documents - List uploaded documents"
            ],
            "ℹ️ Info": [
                "list_my_capabilities - List these capabilities"
            ]
        }
    }
    return capabilities


# --- Tool Registration ---
# Note: generate_conversation_title is NOT added to this list.
# It's not a tool for the agent, it's a tool for our UI.
tools = [
    search_tool, get_stock_price, calculator, post_tweet, list_files, read_file,
    write_file, list_google_drive_files, read_google_drive_file,
    write_to_google_drive, research_and_write_to_drive, send_email, list_recent_emails, read_email_content,
    search_uploaded_documents, list_my_documents, list_my_capabilities
]
llm_with_tools = llm.bind_tools(tools)

# -------------------
# 3. State & Graph
# -------------------
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

graph = StateGraph(ChatState)
graph.add_node("chat_node", lambda state: {"messages": [llm_with_tools.invoke(state["messages"])]})
graph.add_node("tools", ToolNode(tools))
graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge('tools', 'chat_node')

# -------------------
# 4. Checkpointer & Compilation
# -------------------
checkpointer = SqliteSaver(conn=sqlite3.connect(database="chatbot.db", check_same_thread=False))
chatbot = graph.compile(checkpointer=checkpointer)

# -------------------
# 5. Helper
# -------------------
def retrieve_all_threads(limit: int = 20):
    """
    Retrieve conversation threads from the database with titles.
    Limited to recent threads for performance.
    """
    try:
        all_threads = []
        seen_thread_ids = set()  # Track unique thread IDs
        
        # Get checkpoints from the checkpointer
        checkpoints = list(checkpointer.list(None))
        
        # Limit iteration to avoid slow startup
        for checkpoint in checkpoints[:100]:  # Only check first 100 checkpoints
            try:
                thread_id = checkpoint.config["configurable"]["thread_id"]
                
                # Skip if we've already processed this thread
                if thread_id in seen_thread_ids:
                    continue
                seen_thread_ids.add(thread_id)
                
                # Stop if we've reached the limit
                if len(all_threads) >= limit:
                    break
                
                # Get the conversation state to find title
                state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
                messages = state.values.get("messages", [])
                
                title = "New Chat"  # Default title
                
                # Try to get title from first message metadata
                if messages and len(messages) > 0:
                    first_msg = messages[0]
                    if hasattr(first_msg, 'metadata') and first_msg.metadata:
                        title = first_msg.metadata.get("conversation_title", None)
                    
                    # If no title in metadata, create one from first user message content
                    if not title or title == "New Chat":
                        # Get first user message content for title
                        first_content = first_msg.content if hasattr(first_msg, 'content') else ""
                        if first_content:
                            # Truncate to first 30 chars as title
                            title = first_content[:30] + ("..." if len(first_content) > 30 else "")
                
                all_threads.append({"thread_id": thread_id, "title": title})
            except Exception as e:
                print(f"Error retrieving thread: {e}")
                continue
        return all_threads
    except Exception as e:
        print(f"Error retrieving threads: {e}")
        return []  # Return empty list on error

