
# --- 1. Imports ---
import os
import json
import operator
from datetime import datetime
from typing import TypedDict, Annotated, Sequence, List, Dict, Any
from uuid import uuid4

# Third-party libraries
from dotenv import load_dotenv
from web3 import Web3
from pydantic import BaseModel
import requests

# LangChain and LangGraph
from langchain_core.messages import BaseMessage, FunctionMessage, HumanMessage, SystemMessage, ToolMessage
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_community.tools.tavily_search import TavilySearchResults

# uagents
from uagents import Context, Protocol, Agent
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

# Local project modules
from cctp import GeneralizedCCTP
from uniswap import UniswapV3Helper
from wallet_analyzer import get_wallet_balances
from graph_tool import find_pools, find_path, load_graph
from MeTTaGraphAnalyzer import MeTTaGraphAnalyzer

# --- 2. Configuration & Initialization ---
load_dotenv()

# Load secrets from environment variables
OPENAI_API_KEY = "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"
TAVILY_API_KEY = "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"
WALLET_PRIVATE_KEY = "4184b1b9490ab1aa145adec5aa4b5b178c4ba0d7b797a629d30fc1763d475acf"
INFURA_MAINNET_RPC = "https://mainnet.infura.io/v3/e417d64498544988b2cb4db9a6defad8"

if not all([OPENAI_API_KEY, TAVILY_API_KEY, WALLET_PRIVATE_KEY, INFURA_MAINNET_RPC]):
    raise ValueError("One or more required environment variables are not set. Please check your .env file.")

os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY

# Service configurations
RPC_URLS = {
    "ETH": INFURA_MAINNET_RPC,
    "BASE": "https://base-mainnet.publicnode.com"
}
CCTP_RECIPIENTS = {
    "ETH": Web3.to_checksum_address("0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"),
    "BASE": Web3.to_checksum_address("0x8bA372fB44ba0821D15Fa02659F96496929C45C6")
}
CCTP_DOMAINS = {"ETH": 0, "BASE": 6}

# Initialize helpers
cctp = GeneralizedCCTP(WALLET_PRIVATE_KEY, RPC_URLS)
uni = UniswapV3Helper(WALLET_PRIVATE_KEY, RPC_URLS)
G = load_graph()
analyzer = MeTTaGraphAnalyzer(G)


# --- 3. Helper Functions ---

def approve_token(chain: str, token: str, amount: int):
    """
    Helper function to approve a token for spending by the Uniswap router.
    Note: This is a placeholder implementation. The actual approval logic
    should exist within your `UniswapV3Helper` class.
    """
    print(f"Approving {amount} of {token} on {chain}...")
    # This assumes your UniswapV3Helper has an 'approve' method.
    # If it doesn't, you'll need to implement the Web3.py logic here.
    try:
        tx_hash = uni.approve(chain, token, amount)
        print(f"Approval successful. Tx: {tx_hash}")
        return tx_hash
    except Exception as e:
        print(f"Error approving token {token} on {chain}: {e}")
        raise


# --- 4. Tool Definitions ---

@tool
def MeTTaGraphAnalyzerTool(query: str) -> dict:
    """
    Analyzes a query using the MeTTaGraphAnalyzer. Note that MeTTa is rule-based so it might not always give correct answers.
    """
    return analyzer.reason(query)

@tool
def perform_cctp_bridge(source_chain: str, dest_chain: str, token: str, amount: float) -> dict:
    """
    Initiates a cross-chain token transfer using the CCTP protocol. Note that CCTP only bridges USDC tokens.
    `source_chain` and `dest_chain` can only be 'BASE' or 'ETH'. `token` must be 'USDC'.
    """
    if token.upper() != 'USDC':
        return {"error": "CCTP Bridge only supports USDC."}
    if source_chain.upper() not in CCTP_DOMAINS or dest_chain.upper() not in CCTP_DOMAINS:
        return {"error": "Invalid source or destination chain. Must be 'ETH' or 'BASE'."}

    # Convert amount to the correct decimal format (USDC has 6 decimals)
    amount_in_units = int(amount * 10**6)
    
    # 1. Approve USDC for burning
    tx1 = cctp.approve_usdc(source_chain, amount_in_units)
    
    # 2. Burn USDC on the source chain
    dest_domain = CCTP_DOMAINS[dest_chain.upper()]
    recipient_address = CCTP_RECIPIENTS[dest_chain.upper()]
    tx2 = cctp.burn_usdc(source_chain, amount_in_units, dest_domain=dest_domain, recipient=recipient_address)
    
    # 3. Get attestation for the burn transaction
    att = cctp.get_attestation(tx2)
    
    # 4. Mint USDC on the destination chain
    tx3 = cctp.mint_usdc(dest_chain, tx2, att)
    
    return {"approve_tx": tx1, "burn_tx": tx2, "mint_tx": tx3}

@tool
def perform_uniswap_swap(chain: str, token_in: str, token_out: str, fee: int, amount_in: int, amount_out_min: int):
    """
    Executes a token swap on Uniswap V3.
    """
    approve_tx = approve_token(chain, token_in, amount_in)
    swap_tx = uni.swap_exact_input_single(chain, token_in, token_out, fee, amount_in, amount_out_min)
    return {"approve_tx": approve_tx, "swap_tx": swap_tx}

@tool
def add_liquidity_uniswap(chain: str, token0: str, token1: str, fee: int, tick_lower: int, tick_upper: int, amount0: int, amount1: int):
    """
    Adds liquidity to a Uniswap V3 pool.
    """
    approve_tx0 = approve_token(chain, token0, amount0)
    approve_tx1 = approve_token(chain, token1, amount1)
    add_liquidity_tx = uni.add_liquidity(chain, token0, token1, fee, tick_lower, tick_upper, amount0, amount1)
    return {"approve_txs": [approve_tx0, approve_tx1], "add_liquidity_tx": add_liquidity_tx}

@tool
def remove_liquidity_uniswap(chain: str, token_id: int, liquidity: int):
    """Removes liquidity from a Uniswap V3 pool."""
    remove_liquidity_tx = uni.remove_liquidity(chain, token_id, liquidity)
    return {"remove_liquidity_tx": remove_liquidity_tx}

@tool
def get_wallet_info(wallet_address: str) -> dict:
    """Retrieves token balances for a given wallet address. Use this to understand a user's holdings."""
    return get_wallet_balances(wallet_address)

@tool
def search_thegraph_for_pools(min_liquidity: float = 0, min_volume: float = 0, has_token: str = None, chain: str = None) -> List[dict]:
    """Searches The Graph for liquidity pools based on liquidity, volume, token, or chain."""
    return find_pools(G, min_liquidity=min_liquidity, min_volume=min_volume, has_token=has_token, chain=chain)

@tool
def find_route(token_in: str, token_out: str) -> dict:
    """Finds the optimal swap route between two tokens."""
    return find_path(G, token_in, token_out)

@tool
def get_trending_coins() -> List[Dict[str, Any]]:
    """Fetches the top 5 trending coins from CoinGecko."""
    url = "https://api.coingecko.com/api/v3/search/trending"
    try:
        response = requests.get(url, headers={"accept": "application/json"})
        response.raise_for_status()
        data = response.json()
        return [coin.get('item', {}) for coin in data.get('coins', [])[:7]]
    except requests.exceptions.RequestException as e:
        return f"An error occurred while fetching data from CoinGecko: {e}"

web_search = TavilySearchResults(max_results=3, name="web_search")

# Combine all tools for the agent
tools = [
    get_wallet_info,
    search_thegraph_for_pools,
    find_route,
    get_trending_coins,
    web_search,
    add_liquidity_uniswap,
    remove_liquidity_uniswap,
    perform_uniswap_swap,
    perform_cctp_bridge,
    MeTTaGraphAnalyzerTool,
]
tool_node = ToolNode(tools)

# --- 5. LangGraph Agent Setup ---

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

SYSTEM_MESSAGE = """You are Synapse, a helpful DeFi (Decentralized Finance) assistant. You can:
1. Analyze wallet balances.
2. Find optimal swap routes.
3. Search for liquidity pools.
4. Get trending crypto information.
5. Execute swaps, add/remove liquidity, or bridge USDC between ETH and BASE.
6. Perform general web searches for DeFi and crypto research.

IMPORTANT GUIDELINES:
- Always provide a final answer to the user after using tools.
- Do not make unnecessary tool calls.
- If a tool returns an error, acknowledge it and inform the user.
- You are limited to 3 tool calls per query to avoid loops.
"""

MAX_TOOL_CALLS = 3

# Define the model and bind the tools
model = ChatOpenAI(
    temperature=0,
    streaming=True,
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY
).bind_tools(tools)

from langchain.schema import AIMessage, HumanMessage

def call_model(state: AgentState) -> dict:
    messages = state['messages']
    response = model.invoke(messages)
    
    # wrap single message in a list
    if isinstance(response, (AIMessage, HumanMessage)):
        response = [response]
    elif isinstance(response, list):
        # ensure all items are messages
        response = [msg if isinstance(msg, (AIMessage, HumanMessage)) else AIMessage(content=str(msg)) for msg in response]
    else:
        # fallback: wrap anything else in AIMessage
        response = [AIMessage(content=str(response))]

    return {"messages": response}


def call_tool_node(state: AgentState) -> dict:
    tool_messages = tool_node.invoke(state)
    # wrap single messages in a list
    if isinstance(tool_messages, (AIMessage, HumanMessage)):
        tool_messages = [tool_messages]
    if isinstance(tool_messages, ToolMessage):
        tool_messages = [tool_messages]
    elif not isinstance(tool_messages, list):
        
        # print(tool_messages)
        # tool_messages = [AIMessage(content=str(tool_messages))]
        tool_messages = tool_messages['messages']

    return {"messages": tool_messages}



def should_continue(state):
    """Controls the loop: continue with tools or finish."""
    if not hasattr(state['messages'][-1], 'tool_calls') or not state['messages'][-1].tool_calls:
        return "end"
    else:
        return "continue"
 
# Define the graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("action", call_tool_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"continue": "action", "end": END},
)
workflow.add_edge("action", "agent")
app = workflow.compile()


# --- 6. uAgent Definition ---
SEED_PHRASE = "ABRADAKAKANICUFJKDNSVIONSJDF"
agent = Agent( name = "Synapse",seed=SEED_PHRASE,port=8000,mailbox=True)


protocol = Protocol(spec=chat_protocol_spec)

@protocol.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    text = "".join(item.text for item in msg.content if isinstance(item, TextContent)).strip()
    if not text:
        return

    await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(), acknowledged_msg_id=msg.msg_id))
    
    ctx.logger.info(f"Executing DeFi query: '{text}'")
    initial_state = {"messages": [HumanMessage(content=text)]}

    try:
        # Stream the response back to the user
        for output in app.stream(initial_state):
            for key, value in output.items():
                if key == 'agent' and value.get('messages'):
                    messages = value['messages']
                    if isinstance(messages, dict):
                        messages = [messages]  # wrap single dict in a list
                    message = messages[-1]
                    if message.content:
                        ctx.logger.info(f"🤖 Agent: {message.content}")
                        await ctx.send(sender, ChatMessage(
                            timestamp=datetime.utcnow(),
                            msg_id=uuid4(),
                            content=[TextContent(type="text", text=f"🤖 Synapse: {message.content}")]))

                elif key == 'action' and value.get('messages'):
                    messages = value['messages']
                    if isinstance(messages, dict):
                        messages = [messages]  # wrap single dict in a list

                    print(messages)
                    tool_output = "\n".join([f"🛠️ Calling tool : {msg.name}" for msg in messages])
                    ctx.logger.info(tool_output)
                    await ctx.send(sender, ChatMessage(
                        timestamp=datetime.utcnow(),
                        msg_id=uuid4(), 
                        content=[TextContent(type="text", text=tool_output)]))

    except Exception as e:
        ctx.logger.exception(f"Error during query execution: {e}")
        response = "I'm sorry, an error occurred while processing your request."
        await ctx.send(sender, ChatMessage(
            timestamp=datetime.utcnow(),
            msg_id=uuid4(),
            content=[TextContent(type="text", text=response)]))



@protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass

agent.include(protocol, publish_manifest=True)

# --- 7. Main Execution ---
if __name__ == "__main__":
    print(f"Synapse agent running at address: {agent.address}")
    agent.run()