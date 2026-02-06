import streamlit as st
import base64
import os
import tempfile
import time
from backened_title import chatbot, generate_conversation_title
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import uuid

# Import services
try:
    from voice_service import transcribe_audio, text_to_speech
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

try:
    from rag_service import process_pdf, list_uploaded_documents
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

try:
    from audio_recorder_streamlit import audio_recorder
    AUDIO_RECORDER_AVAILABLE = True
except ImportError:
    AUDIO_RECORDER_AVAILABLE = False

from auth_service import (
    register_user, login_user, get_user_threads, 
    save_user_thread, update_thread_title, delete_thread,
    pin_thread, unpin_thread
)

try:
    from analytics_service import log_usage, log_tool_usage, get_user_stats
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False

# =========================== Page Config ===========================
st.set_page_config(
    page_title="LangGraph Chatbot",
    page_icon="🤖",
    layout="wide"
)

# =========================== Image Paths ===========================
IMAGE_DIR = os.path.join(os.path.dirname(__file__), "image")
BACKGROUND_IMAGE = os.path.join(IMAGE_DIR, "background.jpeg")
AUTH_BACKGROUND = os.path.join(IMAGE_DIR, "authentication.jpeg")
HUMAN_AVATAR = os.path.join(IMAGE_DIR, "human.jpeg")
CHATBOT_AVATAR = os.path.join(IMAGE_DIR, "chatbot.jpeg")

# =========================== Helper Functions ===========================
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return None

def get_avatar(role):
    if role == "user":
        return HUMAN_AVATAR if os.path.exists(HUMAN_AVATAR) else "👤"
    else:
        return CHATBOT_AVATAR if os.path.exists(CHATBOT_AVATAR) else "🤖"

def generate_thread_id():
    return str(uuid.uuid4())

def load_conversation(thread_id):
    state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
    messages = state.values.get("messages", [])
    history = []
    for msg in messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        content = ""
        if hasattr(msg, 'content'):
            content = msg.content
        elif isinstance(msg, ToolMessage) and msg.content:
            content = msg.content
        if content:
            history.append({"role": role, "content": content})
    return history

# =========================== Authentication Page ===========================
def show_auth_page():
    auth_bg = get_base64_image(AUTH_BACKGROUND)
    
    st.markdown(f"""
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.6)), 
                          url("data:image/jpeg;base64,{auth_bg}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    .auth-title {{ text-align: center; color: #e94560; font-size: 2.5rem; margin-bottom: 30px; }}
    .auth-subtitle {{ text-align: center; color: #ffffff; font-size: 1rem; margin-bottom: 20px; opacity: 0.8; }}
    .stTextInput > div > div > input {{
        background: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(233, 69, 96, 0.5) !important;
        border-radius: 10px !important;
        color: white !important;
    }}
    .stButton > button {{
        width: 100%;
        background: linear-gradient(90deg, #e94560 0%, #533483 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 12px 24px !important;
        font-weight: bold !important;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<h1 class="auth-title">🤖 LangGraph Chatbot</h1>', unsafe_allow_html=True)
        st.markdown('<p class="auth-subtitle">Your AI-powered assistant with 16+ tools</p>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔐 Sign In", "📝 Sign Up"])
        
        with tab1:
            st.markdown("### Welcome Back!")
            login_username = st.text_input("Username", key="login_username")
            login_password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("Sign In", key="login_btn"):
                if login_username and login_password:
                    result = login_user(login_username, login_password)
                    if result["success"]:
                        st.session_state["authenticated"] = True
                        st.session_state["user_id"] = result["user_id"]
                        st.session_state["username"] = result["username"]
                        st.success(f"Welcome back, {result['username']}! 🎉")
                        st.rerun()
                    else:
                        st.error(result["error"])
                else:
                    st.warning("Please enter username and password")
        
        with tab2:
            st.markdown("### Create Account")
            reg_username = st.text_input("Choose Username", key="reg_username")
            reg_email = st.text_input("Email (optional)", key="reg_email")
            reg_password = st.text_input("Choose Password", type="password", key="reg_password")
            reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")
            
            if st.button("Sign Up", key="register_btn"):
                if not reg_username or not reg_password:
                    st.warning("Please fill in username and password")
                elif reg_password != reg_confirm:
                    st.error("Passwords do not match")
                else:
                    result = register_user(reg_username, reg_password, reg_email)
                    if result["success"]:
                        st.success("Account created! Please sign in. 🎉")
                    else:
                        st.error(result["error"])


# =========================== Main Chat Page ===========================
def show_chat_page():
    bg_image = get_base64_image(BACKGROUND_IMAGE)
    
    if bg_image:
        st.markdown(f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), 
                              url("data:image/jpeg;base64,{bg_image}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
            border-right: 1px solid #0f3460;
        }}
        [data-testid="stSidebar"] .stButton > button {{
            background: linear-gradient(90deg, #0f3460 0%, #533483 100%);
            color: white; border: none; border-radius: 10px;
            padding: 8px 12px; margin: 3px 0; transition: all 0.3s ease;
        }}
        [data-testid="stSidebar"] .stButton > button:hover {{
            background: linear-gradient(90deg, #533483 0%, #0f3460 100%);
        }}
        .stChatMessage {{
            background: rgba(255, 255, 255, 0.1) !important;
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 15px;
            margin: 10px 0;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        h1 {{ color: #e94560 !important; }}
        h2, h3 {{ color: #ffffff !important; }}
        .stMarkdown, p, span {{ color: #ffffff !important; }}
        .user-badge {{
            background: linear-gradient(90deg, #e94560 0%, #533483 100%);
            padding: 5px 15px; border-radius: 20px; color: white; font-size: 14px;
        }}
        .stat-box {{
            background: rgba(255, 255, 255, 0.1);
            padding: 10px; border-radius: 10px; margin: 5px 0;
            border: 1px solid rgba(233, 69, 96, 0.3);
        }}
        .pin-icon {{ color: #ffd700; }}
        </style>
        """, unsafe_allow_html=True)
    
    # Initialize session state
    if "message_history" not in st.session_state:
        st.session_state["message_history"] = []
    if "thread_info" not in st.session_state:
        st.session_state["thread_info"] = {"thread_id": generate_thread_id(), "title": "New Chat", "is_pinned": False}
    if "chat_threads" not in st.session_state:
        st.session_state["chat_threads"] = get_user_threads(st.session_state["user_id"])
    if "tts_enabled" not in st.session_state:
        st.session_state["tts_enabled"] = False
    if "show_analytics" not in st.session_state:
        st.session_state["show_analytics"] = False
    
    # ============================ Sidebar ============================
    st.sidebar.markdown(f'<span class="user-badge">👤 {st.session_state["username"]}</span>', unsafe_allow_html=True)
    st.sidebar.title("🤖 LangGraph Chatbot")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🚪 Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    with col2:
        if st.button("➕ New Chat", use_container_width=True):
            new_thread = {"thread_id": generate_thread_id(), "title": "New Chat", "is_pinned": False}
            st.session_state["thread_info"] = new_thread
            st.session_state["message_history"] = []
            st.rerun()
    
    # ---------- Analytics Dashboard ----------
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Analytics")
    
    if ANALYTICS_AVAILABLE:
        if st.sidebar.toggle("Show Dashboard", value=st.session_state.get("show_analytics", False), key="analytics_toggle"):
            st.session_state["show_analytics"] = True
            stats = get_user_stats(st.session_state["user_id"])
            
            st.sidebar.markdown('<div class="stat-box">', unsafe_allow_html=True)
            st.sidebar.metric("💬 Messages", stats["total_messages"])
            st.sidebar.metric("🔤 Tokens Used", f"{stats['total_tokens']:,}")
            st.sidebar.metric("💰 Est. Cost", f"${stats['estimated_cost']:.4f}")
            st.sidebar.metric("⏱️ Avg Response", f"{stats['avg_response_time_ms']}ms")
            st.sidebar.markdown('</div>', unsafe_allow_html=True)
            
            # Tool breakdown
            if stats["tool_breakdown"]:
                st.sidebar.markdown("**🔧 Tool Usage:**")
                for tool, count in list(stats["tool_breakdown"].items())[:5]:
                    st.sidebar.caption(f"• {tool}: {count}")
        else:
            st.session_state["show_analytics"] = False
    else:
        st.sidebar.caption("Analytics not available")
    
    # ---------- Voice Settings ----------
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎤 Voice")
    if VOICE_AVAILABLE:
        st.session_state["tts_enabled"] = st.sidebar.toggle("Text-to-Speech", value=st.session_state.get("tts_enabled", False))
    
    # ---------- PDF Upload ----------
    st.sidebar.markdown("---")
    st.sidebar.subheader("📚 Knowledge Base")
    if RAG_AVAILABLE:
        uploaded_file = st.sidebar.file_uploader("Upload PDF", type=["pdf"], key="pdf_upload")
        if uploaded_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            with st.sidebar.status("Processing...") as status:
                result = process_pdf(tmp_path, uploaded_file.name)
                status.update(label="✅ Done" if result["success"] else "❌ Error", state="complete" if result["success"] else "error")
            os.unlink(tmp_path)
    
    # ---------- Conversations List ----------
    st.sidebar.markdown("---")
    st.sidebar.subheader("📜 Conversations")
    
    for thread in st.session_state["chat_threads"]:
        pin_icon = "📌 " if thread.get("is_pinned") else ""
        display_title = thread["title"][:18] + "..." if len(thread["title"]) > 18 else thread["title"]
        
        col1, col2, col3 = st.sidebar.columns([5, 1, 1])
        with col1:
            if st.button(f"{pin_icon}{display_title}", key=f"chat_{thread['thread_id']}", use_container_width=True):
                st.session_state["thread_info"] = thread
                st.session_state["message_history"] = load_conversation(thread["thread_id"])
                st.rerun()
        with col2:
            # Pin/Unpin button
            if thread.get("is_pinned"):
                if st.button("📌", key=f"unpin_{thread['thread_id']}", help="Unpin"):
                    unpin_thread(st.session_state["user_id"], thread["thread_id"])
                    st.session_state["chat_threads"] = get_user_threads(st.session_state["user_id"])
                    st.rerun()
            else:
                if st.button("📍", key=f"pin_{thread['thread_id']}", help="Pin"):
                    pin_thread(st.session_state["user_id"], thread["thread_id"])
                    st.session_state["chat_threads"] = get_user_threads(st.session_state["user_id"])
                    st.rerun()
        with col3:
            # Delete button
            if st.button("🗑️", key=f"del_{thread['thread_id']}", help="Delete"):
                delete_thread(st.session_state["user_id"], thread["thread_id"])
                st.session_state["chat_threads"] = get_user_threads(st.session_state["user_id"])
                if st.session_state["thread_info"]["thread_id"] == thread["thread_id"]:
                    st.session_state["thread_info"] = {"thread_id": generate_thread_id(), "title": "New Chat", "is_pinned": False}
                    st.session_state["message_history"] = []
                st.rerun()
    
    # ============================ Main Chat Area ============================
    st.title(f"💬 {st.session_state['thread_info']['title']}")
    
    # Render message history
    for idx, message in enumerate(st.session_state["message_history"]):
        with st.chat_message(message["role"], avatar=get_avatar(message["role"])):
            st.markdown(message["content"])
    
    # Regenerate button (show if there are assistant messages)
    if len(st.session_state["message_history"]) >= 2:
        col1, col2, col3 = st.columns([4, 1, 1])
        with col2:
            if st.button("🔄 Regenerate", help="Regenerate last response", use_container_width=True):
                # Remove last assistant message
                if st.session_state["message_history"][-1]["role"] == "assistant":
                    st.session_state["message_history"].pop()
                    # Get last user message to regenerate
                    if st.session_state["message_history"] and st.session_state["message_history"][-1]["role"] == "user":
                        st.session_state["regenerating"] = True
                        st.rerun()
    
    # Voice & Text Input
    col1, col2 = st.columns([6, 1])
    with col1:
        user_input = st.chat_input("Type your message...")
    with col2:
        voice_input = None
        if VOICE_AVAILABLE and AUDIO_RECORDER_AVAILABLE:
            audio_bytes = audio_recorder(text="", recording_color="#e94560", neutral_color="#6c757d", icon_size="2x", pause_threshold=2.0)
            if audio_bytes:
                with st.spinner("🎤 Transcribing..."):
                    result = transcribe_audio(audio_bytes, "recording.wav")
                    if result["success"]:
                        voice_input = result["text"]
                        st.toast(f"🎤 {voice_input[:50]}...")
    
    if voice_input and not user_input:
        user_input = voice_input
    
    # Handle regeneration
    if st.session_state.get("regenerating") and st.session_state["message_history"]:
        user_input = st.session_state["message_history"][-1]["content"]
        st.session_state["regenerating"] = False
        st.session_state["message_history"].pop()  # Remove old user message, will add fresh
    
    # Process Input
    if user_input:
        start_time = time.time()
        is_new_chat = len(st.session_state["message_history"]) == 0
        
        if is_new_chat:
            with st.spinner("✨ Naming conversation..."):
                new_title = generate_conversation_title(user_input)
                st.session_state["thread_info"]["title"] = new_title
                save_user_thread(st.session_state["user_id"], st.session_state["thread_info"]["thread_id"], new_title)
                st.session_state["chat_threads"].insert(0, st.session_state["thread_info"].copy())
        
        st.session_state["message_history"].append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar=get_avatar("user")):
            st.markdown(user_input)
        
        messages_to_send = [HumanMessage(content=user_input)]
        if is_new_chat:
            messages_to_send[0].metadata = {"conversation_title": st.session_state["thread_info"]["title"]}
        
        CONFIG = {"configurable": {"thread_id": st.session_state["thread_info"]["thread_id"]}}
        
        with st.chat_message("assistant", avatar=get_avatar("assistant")):
            status_box = st.empty()
            full_response = ""
            message_placeholder = st.empty()
            tools_used = []
            
            for chunk in chatbot.stream({"messages": messages_to_send}, config=CONFIG):
                messages = []
                for node_output in chunk.values():
                    if isinstance(node_output, dict) and "messages" in node_output:
                        messages.extend(node_output["messages"])
                
                tool_messages = [msg for msg in messages if isinstance(msg, ToolMessage)]
                if tool_messages:
                    tool_name = getattr(tool_messages[-1], "name", "tool")
                    tools_used.append(tool_name)
                    status_box.status(f"🔧 Using `{tool_name}`…", expanded=True)
                    # Log tool usage
                    if ANALYTICS_AVAILABLE:
                        log_tool_usage(st.session_state["user_id"], tool_name)
                
                ai_message = next((msg for msg in reversed(messages) if isinstance(msg, AIMessage)), None)
                if ai_message and ai_message.content:
                    full_response = ai_message.content
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            status_box.empty()
            
            # Log usage
            response_time = int((time.time() - start_time) * 1000)
            if ANALYTICS_AVAILABLE:
                # Estimate tokens (rough: 4 chars = 1 token)
                input_tokens = len(user_input) // 4
                output_tokens = len(full_response) // 4
                log_usage(st.session_state["user_id"], st.session_state["thread_info"]["thread_id"],
                         input_tokens, output_tokens, response_time_ms=response_time)
            
            # TTS
            if st.session_state.get("tts_enabled") and full_response and VOICE_AVAILABLE:
                with st.spinner("🔊 Generating audio..."):
                    audio_bytes = text_to_speech(full_response)
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/mp3", autoplay=True)
        
        st.session_state["message_history"].append({"role": "assistant", "content": full_response})
        
        if is_new_chat:
            st.rerun()


# =========================== Main App ===========================
def main():
    if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
        show_auth_page()
    else:
        show_chat_page()

if __name__ == "__main__":
    main()
