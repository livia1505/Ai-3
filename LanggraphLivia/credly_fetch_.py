import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage

# -------------------- Selenium Setup --------------------
def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=Service(), options=chrome_options)
    return driver

# -------------------- Core Function --------------------
def fetch_certificates(url: str):
    """
    Fetch badges from a Credly profile using Selenium.
    Returns list of dicts with 'title' and 'issued_date'.
    """
    driver = create_driver()
    try:
        driver.get(url)
        time.sleep(3)  # Wait for page to load

        badges_elements = driver.find_elements(By.CSS_SELECTOR, "div.profile-badge-card")  # CSS for badge cards
        badges = []

        for badge in badges_elements:
            try:
                title_el = badge.find_element(By.CSS_SELECTOR, "h3.badge-title")
                date_el = badge.find_element(By.CSS_SELECTOR, "p.badge-issue-date")
                title = title_el.text.strip()
                issued_date = date_el.text.replace("Issued", "").strip()
                badges.append({"title": title, "issued_date": issued_date})
            except:
                continue

        return badges
    finally:
        driver.quit()

# -------------------- LangGraph Tool --------------------
@tool
def get_certificates(url: str):
    """
    Fetch all badge names and issue dates from a Credly profile URL.
    """
    return fetch_certificates(url)

tools = [get_certificates]

# -------------------- Graph Definition --------------------
class State(dict):
    messages: list = []

graph_builder = StateGraph(State)

def chatbot(state: State):
    if "messages" not in state or not state["messages"]:
        return {"messages": [AIMessage(content="Please provide a Credly profile URL.")]}

    last_msg = state["messages"][-1]
    if isinstance(last_msg, str):
        last_msg = HumanMessage(content=last_msg)

    if isinstance(last_msg, HumanMessage):
        url = last_msg.content.strip()
        if url.startswith("https://www.credly.com"):
            try:
                badges = fetch_certificates(url)
                if badges:
                    content = f"Found {len(badges)} badges:\n"
                    for i, b in enumerate(badges, 1):
                        content += f"{i}. {b['title']} (Issued: {b['issued_date']})\n"
                else:
                    content = "No badges found for this profile."
                return {"messages": [AIMessage(content=content)]}
            except Exception as e:
                return {"messages": [AIMessage(content=f"Error fetching badges: {str(e)}")]}
        else:
            return {"messages": [AIMessage(content="Please provide a valid Credly profile URL.")]}
    
    return {"messages": [AIMessage(content="Invalid message type received.")]}

graph_builder.add_node("chatbot", chatbot)

tool_node = ToolNode(tools)
graph_builder.add_node("tools", tool_node)
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")

graph = graph_builder.compile()

# -------------------- CLI --------------------
if __name__ == "__main__":
    profile_url = input("Enter Credly profile URL: ").strip()
    try:
        badges = fetch_certificates(profile_url)
        print(f"Found {len(badges)} badges:")
        for i, badge in enumerate(badges, 1):
            print(f"{i}. {badge['title']} (Issued: {badge['issued_date']})")
    except Exception as e:
        print(f"Error fetching badges: {e}")
