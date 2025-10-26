import os
import requests
from typing import Annotated, TypedDict
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, END, START

# Read GROQ_API_KEY from environment
groq_api_key = os.environ.get("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY environment variable not set.")

# Global variable to store scraped data
credly_data = {"badges": [], "count": 0}

# -------------------- Tool Definitions --------------------

@tool
def get_certificates(url: str) -> str:
    """Call to get certificates from a Credly profile URL."""
    global credly_data
    print(f"[TOOL CALL] get_certificates called with: url={url}")
    try:
        # Convert the URL to JSON endpoint
        # Example: https://www.credly.com/users/cladius/badges -> https://www.credly.com/users/cladius/badges.json
        if not url.endswith('.json'):
            if url.endswith('/'):
                json_url = url + 'badges.json'
            elif '/badges' in url:
                json_url = url + '.json'
            else:
                json_url = url + '/badges.json'
        else:
            json_url = url
        
        print(f"[TOOL] Fetching from: {json_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        response = requests.get(json_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        credly_data['badges'] = []
        
        # Parse the JSON response
        if 'data' in data:
            for badge in data['data']:
                badge_info = {
                    'title': badge.get('badge_template', {}).get('name', 'Unknown'),
                    'issuer': ', '.join([entity.get('entity', {}).get('name', '') 
                                       for entity in badge.get('issuer', {}).get('entities', [])]),
                    'issued_date': badge.get('issued_at_date', 'Unknown'),
                    'image_url': badge.get('image_url', ''),
                    'badge_url': f"https://www.credly.com/badges/{badge.get('id', '')}"
                }
                credly_data['badges'].append(badge_info)
        
        credly_data['count'] = len(credly_data['badges'])
        result = f"Found {credly_data['count']} certificates."
        print("[TOOL RESULT] get_certificates returned:", result)
        return result
        
    except requests.exceptions.RequestException as e:
        result = f"Error fetching data: {str(e)}"
        print("[TOOL RESULT] get_certificates returned:", result)
        return result
    except Exception as e:
        result = f"Error parsing data: {str(e)}"
        print("[TOOL RESULT] get_certificates returned:", result)
        return result

@tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    print(f"[TOOL CALL] add called with: a={a}, b={b}")
    result = a + b
    print("[TOOL RESULT] add returned: ", result)
    return result

@tool
def subtract(a: int, b: int) -> int:
    """Subtract b from a."""
    print(f"[TOOL CALL] subtract called with: a={a}, b={b}")
    result = a - b
    print("[TOOL RESULT] subtract returned:", result)
    return result

@tool
def count_certificates() -> str:
    """Get the total count of certificates. If certificates haven't been fetched yet, this will tell you."""
    print(f"[TOOL CALL] count_certificates called")
    if credly_data['count'] == 0:
        result = "No certificates are currently loaded in memory. You need to fetch certificates first using the get_certificates tool with a Credly profile URL."
    else:
        result = f"You have {credly_data['count']} certificates."
    print("[TOOL RESULT] count_certificates returned:", result)
    return result

@tool
def list_all_certificates() -> str:
    """List all certificates with their titles and issuers."""
    print(f"[TOOL CALL] list_all_certificates called")
    if credly_data['count'] == 0:
        result = "No certificates loaded. Please fetch certificates first using get_certificates."
    else:
        cert_list = []
        for i, badge in enumerate(credly_data['badges'], 1):
            title = badge.get('title', 'Unknown')
            issuer = badge.get('issuer', 'Unknown Issuer')
            date = badge.get('issued_date', 'Unknown Date')
            cert_list.append(f"{i}. {title} (Issued by: {issuer}, Date: {date})")
        result = "\n".join(cert_list)
    print(f"[TOOL RESULT] list_all_certificates returned {credly_data['count']} certificates")
    return result

# List of available tools
tools = [get_certificates, count_certificates, list_all_certificates, add, subtract]

# -------------------- LLM Setup --------------------

# Initialize the LLM with Groq API key and model
llm = ChatGroq(groq_api_key=groq_api_key, model="llama-3.3-70b-versatile")
llm_with_tools = llm.bind_tools(tools)

# -------------------- State Definition --------------------

class State(TypedDict):
    messages: Annotated[list, add_messages]

# Create a state graph for the conversation flow
graph_builder = StateGraph(State)

# Node: Chatbot LLM invocation
def chatbot(state: State):
    # Pass conversation messages to the LLM and get the response
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

graph_builder.add_node("chatbot", chatbot)

# Node: Tool execution
tool_node = ToolNode(tools)
graph_builder.add_node("tools", tool_node)

# Conditional edge: If tool is needed, go to tool node
graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)

# After tool execution, return to chatbot
graph_builder.add_edge("tools", "chatbot")
# Start the graph at the chatbot node
graph_builder.add_edge(START, "chatbot")

# Compile the graph
graph = graph_builder.compile()

# -------------------- Chat Loop --------------------
def invoke_chat_loop():
    print("You can chat with the LLM. It will decide when to use tools (certificates, add, subtract). Type 'exit' to quit.")
    conversation = []
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Exiting chat.")
            break
        # Add user message to conversation
        conversation.append(HumanMessage(content=user_input))
        state = {"messages": conversation}
        # Invoke the graph with the current state
        result = graph.invoke(state)
        # Update conversation with new messages
        conversation = result["messages"]
        print("AI:", conversation[-1].content)
