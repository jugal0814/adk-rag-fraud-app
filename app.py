import streamlit as st
import uuid
import time
from vertexai import agent_engines

# Set page config
st.set_page_config(
    page_title="Fraud Support Agent",
    page_icon="🤖",
    layout="centered"
)

# Custom CSS for styling assistant messages only
st.markdown("""
<style>
.assistant-response {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 15px 20px;
    border-radius: 10px;
    margin: 5px 0;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
    border-left: 3px solid #4f46e5;
}
</style>
""", unsafe_allow_html=True)

# Constants
APP_NAME = "fraud_rag_agent"
AGENT_ID = "3854843786517544960"  # Fraud RAG Agent ID

# Initialize session state variables
if "user_id" not in st.session_state:
    st.session_state.user_id = f"user-{uuid.uuid4()}"
    
if "session_id" not in st.session_state:
    st.session_state.session_id = None
    
if "messages" not in st.session_state:
    st.session_state.messages = []

if "audio_files" not in st.session_state:
    st.session_state.audio_files = []

if "waiting_for_response" not in st.session_state:
    st.session_state.waiting_for_response = False

def create_session(resource_id: str, user_id: str) -> bool:
    """
    Create a new session with the fraud rag agent.
    
    This function:
    1. Generates a unique session ID based on timestamp
    2. Sends a POST request to the ADK API to create a session
    3. Updates the session state variables if successful
    
    Returns:
        bool: True if session was created successfully, False otherwise
    
    API Endpoint:
        POST /apps/{app_name}/users/{user_id}/sessions/{session_id}
    """
    session_id = f"session-{int(time.time())}"
    """Creates a new session for the specified user."""
    remote_app = agent_engines.get(resource_id)
    remote_session = remote_app.create_session(user_id=user_id)
    print("Created session:")
    print(f"  Session ID: {remote_session['id']}")
    print(f"  User ID: {remote_session['user_id']}")
    print(f"  App name: {remote_session['app_name']}")
    print(f"  Last update time: {remote_session['last_update_time']}")
    print("\nUse this session ID with --session_id when sending messages.")
    
    if remote_session is not None:
        st.session_state.session_id = remote_session['id']
        st.session_state.messages = []
        st.session_state.waiting_for_response = False
        return True
    else:
        st.error(f"Failed to create session for user {user_id}.")
        return False

def send_message_to_api(message):
    """
    Send a message to the fraud rag agent and process the response.
    
    This function:
    1. Sends the message to the ADK API
    2. Processes the response to extract text and audio information
    3. Updates the chat history with the assistant's response
    
    Args:
        message (str): The user's message to send to the agent
        
    Returns:
        bool: True if message was sent and processed successfully, False otherwise
    
    API Endpoint:
        POST /run
        
    Response Processing:
        - Parses the ADK event structure to extract text responses
        - Looks for text_to_speech function responses to find audio file paths
        - Adds both text and audio information to the chat history
    """
    if not st.session_state.session_id:
        st.error("No active session. Please create a session first.")
        return False
    
    try:
        """Sends a message to the deployed agent."""
        remote_app = agent_engines.get(AGENT_ID)

        print(f"Sending message to session {st.session_state.session_id}:")
        print(f"Message: {message}")
        print("\nResponse:")
        events = remote_app.stream_query(
            user_id=st.session_state.user_id,
            session_id=st.session_state.session_id,
            message=message,
        )
        
        # Extract assistant's text response
        assistant_message = None
        
        for event in events:
            print(event)  # Debug: print the event structure
            # Look for the final text response from the model
            if event.get("content", {}).get("role") == "model" and "text" in event.get("content", {}).get("parts", [{}])[0]:
                assistant_message = event["content"]["parts"][0]["text"]
        
        # Add assistant response to chat
        if assistant_message:
            st.session_state.messages.append({"role": "assistant", "content": assistant_message})
        else:
            st.session_state.messages.append({"role": "assistant", "content": "I received your message but couldn't generate a response."})
        
        return True
        
    except Exception as e:
        st.error(f"Error sending message: {str(e)}")
        st.session_state.messages.append({"role": "assistant", "content": "Sorry, there was an error processing your request."})
        return False

def handle_user_input(user_input):
    """
    Handle user input by immediately adding it to chat and then processing the API call.
    
    Args:
        user_input (str): The user's message
    """
    # Immediately add user message to chat
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.waiting_for_response = True
    
    # Rerun to show the user message immediately
    st.rerun()

# Remove the custom display_message function - we'll use original Streamlit approach

# UI Components
st.title("Fraud Support Agent")

# Sidebar for session management
with st.sidebar:
    st.header("Session Management")
    
    if st.session_state.session_id:
        st.success(f"Active session: {st.session_state.session_id}")
        if st.button("➕ New Session"):
            if st.session_state.user_id:
                # Create a new session with the same user ID
                create_session(AGENT_ID, st.session_state.user_id)
            else:
                create_session(AGENT_ID, f"user-{uuid.uuid4()}")
    else:
        st.warning("No active session")
        if st.button("➕ Create Session"):
            if st.session_state.user_id:
                # Create a new session with the same user ID
                create_session(AGENT_ID, st.session_state.user_id)
            else:
                create_session(AGENT_ID, f"user-{uuid.uuid4()}")
    
    st.divider()
    st.caption("This app interacts with the Fraud RAG Agent via the ADK API Server.")
    st.caption("Make sure the ADK API Server is running on port 8000.")

# Chat interface
st.subheader("Conversation")

# Display messages
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        with st.chat_message("assistant"):
            # Use custom styling for assistant response with proper HTML escaping
            # import html
            # escaped_content = html.escape(msg["content"]).replace('\n', '<br>')
            st.markdown(f"""
            <div class="assistant-response">
                {msg["content"]}
            </div>
            """, unsafe_allow_html=True)      

# Show typing indicator when waiting for response
if st.session_state.waiting_for_response:
    with st.chat_message("assistant"):
        st.write("🤔 Thinking...")

# Process API call if we're waiting for a response
if st.session_state.waiting_for_response:
    # Get the last user message to send to API
    user_messages = [msg for msg in st.session_state.messages if msg["role"] == "user"]
    if user_messages:
        last_user_message = user_messages[-1]["content"]
        
        # Send message to API and get response
        success = send_message_to_api(last_user_message)
        
        # Reset waiting state
        st.session_state.waiting_for_response = False
        
        # Rerun to show the assistant's response
        st.rerun()

# Input for new messages
if st.session_state.session_id:  # Only show input if session exists
    user_input = st.chat_input("Type your message...")
    if user_input and not st.session_state.waiting_for_response:
        handle_user_input(user_input)
else:
    st.info("👈 Create a session to start chatting")