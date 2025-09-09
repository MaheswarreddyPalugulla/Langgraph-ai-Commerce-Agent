import json
import os
import re
from typing import TypedDict, List, Dict, Optional, Annotated, Any
from datetime import datetime
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage

from tools import commerce_tools

# Load environment variables
load_dotenv()

# Mock LLM for deterministic behavior
class MockLLM:
    """Mock LLM for testing without external dependencies"""
    def invoke(self, messages):
        user_message = messages[-1].content.lower()
        
        if any(word in user_message for word in ['wedding', 'dress', 'midi', 'product']):
            return AIMessage(content="I'll help you find wedding dresses within your budget.")
        elif 'cancel order' in user_message:
            return AIMessage(content="I'll look up your order and check our cancellation policy.")
        elif 'discount code' in user_message:
            return AIMessage(content="I cannot provide non-existent discount codes, but I can suggest legitimate offers.")
        else:
            return AIMessage(content="I'll help you with your request.")

def get_llm():
    """Get LLM based on environment configuration"""
    llm_provider = os.getenv("LLM_PROVIDER", "mock")
    
    if llm_provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")
        )
    elif llm_provider == "ollama":
        from langchain_ollama import ChatOllama
        model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        return ChatOllama(
            model=model,
            temperature=0
        )
    else:
        return MockLLM()

# State Definition
class CommerceState(TypedDict):
    messages: Annotated[List, add_messages]
    intent: str
    tools_called: List[str]
    evidence: List[Dict]
    policy_decision: Optional[Dict]
    final_message: str
    trace: Dict

# Node Functions
def router_node(state: CommerceState) -> Dict:
    """Classify user intent based on keywords"""
    if not state["messages"]:
        return {"intent": "other"}
    
    user_message = state["messages"][-1].content.lower()
    
    # Product assistance keywords
    product_keywords = ['dress', 'product', 'wedding', 'midi', 'size', 'price', 'eta', 'under']
    # Order help keywords  
    order_keywords = ['cancel', 'order', 'refund']
    
    # Determine intent based on keyword presence
    if any(word in user_message for word in product_keywords) and 'cancel' not in user_message:
        intent = "product_assist"
    elif any(word in user_message for word in order_keywords):
        intent = "order_help"
    else:
        intent = "other"
    
    return {"intent": intent}

def tool_selector_node(state: CommerceState) -> Dict:
    """Select tools to call based on intent"""
    intent = state.get("intent", "other")
    
    if intent == "product_assist":
        tools = ["product_search", "size_recommender", "eta"]
    elif intent == "order_help":
        tools = ["order_lookup", "order_cancel"]
    else:
        tools = []
    
    return {"tools_called": tools}

def execute_tools_node(state: CommerceState) -> Dict:
    """Execute selected tools and gather evidence"""
    user_message = state["messages"][-1].content if state["messages"] else ""
    tools_called = state.get("tools_called", [])
    evidence = []
    
    if "product_search" in tools_called:
        # Parse search parameters from user message
        price_max = 1000  # default
        query = ""
        tags = []
        
        # Extract price constraint
        message_lower = user_message.lower()
        price_match = re.search(r'under.*?(\d+)', message_lower)
        if price_match:
            price_max = int(price_match.group(1))
        
        # Parse query terms and tags
        if any(word in message_lower for word in ['wedding', 'midi']):
            query = "midi"
            tags = ["wedding", "midi"]
        
        products = commerce_tools.product_search(query, price_max, tags)
        evidence.extend([{"type": "product", "data": p} for p in products])
    
    if "order_lookup" in tools_called:
        # Extract order ID and email using regex
        order_match = re.search(r'order\s+([A-Z]\d+)', user_message, re.IGNORECASE)
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', user_message)
        
        if order_match and email_match:
            order_id = order_match.group(1)
            email = email_match.group(0)
            
            order = commerce_tools.order_lookup(order_id, email)
            if order:
                evidence.append({"type": "order", "data": order})
    
    return {"evidence": evidence}

def policy_guard_node(state: CommerceState) -> Dict:
    """Enforce business policies, especially 60-minute cancellation rule"""
    intent = state.get("intent")
    evidence = state.get("evidence", [])
    policy_decision = None
    
    if intent == "order_help":
        # Extract order details and check cancellation policy
        user_message = state["messages"][-1].content
        
        order_match = re.search(r'order\s+([A-Z]\d+)', user_message, re.IGNORECASE)
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', user_message)
        
        if order_match and email_match:
            order_id = order_match.group(1)
            email = email_match.group(0)
            
            # Call cancellation logic with 60-minute enforcement
            cancel_result = commerce_tools.order_cancel(order_id, email)
            
            if cancel_result["success"]:
                policy_decision = {
                    "cancel_allowed": True,
                    "reason": "within_policy",
                    "message": cancel_result["message"]
                }
            else:
                policy_decision = {
                    "cancel_allowed": False,
                    "reason": cancel_result["reason"],
                    "message": cancel_result["message"],
                    "alternatives": cancel_result.get("alternatives", [])
                }
    elif intent == "other":
        # Handle discount code guardrail
        user_message = state["messages"][-1].content.lower()
        if "discount code" in user_message and any(word in user_message for word in ["doesn't exist", "non-existent", "fake"]):
            policy_decision = {
                "refuse": True,
                "reason": "invalid_discount_request"
            }
    
    return {"policy_decision": policy_decision}

def responder_node(state: CommerceState) -> Dict:
    """Generate final response with JSON trace"""
    intent = state.get("intent", "other")
    tools_called = state.get("tools_called", [])
    evidence = state.get("evidence", [])
    policy_decision = state.get("policy_decision")
    user_message = state["messages"][-1].content if state["messages"] else ""
    
    # Generate JSON trace - REQUIRED FORMAT
    trace = {
        "intent": intent,
        "tools_called": tools_called,
        "evidence": [
            {
                "id": e["data"].get("id", e["data"].get("order_id", "unknown")),
                **{k: v for k, v in e["data"].items() if k in ["title", "price", "sizes", "order_id", "email", "color"]}
            } 
            for e in evidence
        ],
        "policy_decision": policy_decision,
        "final_message": ""
    }
    
    # Generate final message based on intent
    final_message = ""
    
    if intent == "product_assist":
        products = [e["data"] for e in evidence if e["type"] == "product"]
        
        if products:
            final_message = f"I found {len(products)} dress{'es' if len(products) > 1 else ''} for you:\n\n"
            
            for p in products:
                final_message += f"• {p['title']} (${p['price']}, {p['color']}) - Available in {', '.join(p['sizes'])}\n"
            
            # Add size recommendation if mentioned
            if "between m/l" in user_message.lower() or "m/l" in user_message.lower():
                size_rec = commerce_tools.size_recommender(user_message)
                final_message += f"\n{size_rec}.\n"
            
            # Add ETA if zip code mentioned
            zip_match = re.search(r'\b\d{6}\b', user_message)
            if zip_match:
                zip_code = zip_match.group(0)
                eta = commerce_tools.eta(zip_code)
                final_message += f"\nDelivery to {zip_code}: {eta}."
        else:
            final_message = "I couldn't find any products matching your criteria. Please try adjusting your price range or preferences."
    
    elif intent == "order_help":
        if policy_decision:
            if policy_decision.get("cancel_allowed"):
                final_message = policy_decision["message"]
            else:
                final_message = f"{policy_decision['message']}\n\nI can help you with these alternatives:\n"
                for i, alt in enumerate(policy_decision.get("alternatives", []), 1):
                    final_message += f"{i}. {alt}\n"
                final_message += "\nWhich option would you prefer?"
        else:
            final_message = "I need both your order ID and email address to help you with order-related requests."
    
    elif intent == "other":
        if policy_decision and policy_decision.get("refuse"):
            final_message = "I can't provide non-existent discount codes, but I can suggest these legitimate offers:\n"
            final_message += "• Sign up for our newsletter for 10% off your first order\n"
            final_message += "• Follow us on social media for exclusive deals\n"
            final_message += "• Check our current promotions page for active discounts"
        else:
            final_message = "I'm here to help with product searches and order management. How can I assist you today?"
    
    trace["final_message"] = final_message
    
    return {
        "final_message": final_message,
        "trace": trace
    }

# Build Graph
def create_commerce_graph():
    """Create and compile the commerce agent graph"""
    graph = StateGraph(CommerceState)
    
    # Add nodes in execution order
    graph.add_node("router", router_node)
    graph.add_node("tool_selector", tool_selector_node)
    graph.add_node("execute_tools", execute_tools_node)
    graph.add_node("policy_guard", policy_guard_node)
    graph.add_node("responder", responder_node)
    
    # Add edges - simple linear flow
    graph.add_edge(START, "router")
    graph.add_edge("router", "tool_selector")
    graph.add_edge("tool_selector", "execute_tools")
    graph.add_edge("execute_tools", "policy_guard")
    graph.add_edge("policy_guard", "responder")
    graph.add_edge("responder", END)
    
    return graph.compile()

# Main function for testing
def run_agent(user_input: str) -> Dict:
    """Run the agent with user input and return trace + response"""
    graph = create_commerce_graph()
    
    result = graph.invoke({
        "messages": [HumanMessage(content=user_input)],
        "intent": "",
        "tools_called": [],
        "evidence": [],
        "policy_decision": None,
        "final_message": "",
        "trace": {}
    })
    
    return {
        "trace": result["trace"],
        "final_message": result["final_message"]
    }