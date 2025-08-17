import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import time
import json
import requests
import asyncio

import asyncio
import os
import requests
from cdp import CdpClient
from openai import OpenAI
from time import sleep

from wallet_analyzer import get_wallet_balances

from langgraph.checkpoint.memory import MemorySaver

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph

memory = InMemorySaver()




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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")
INFURA_MAINNET_RPC = os.getenv("INFURA_MAINNET_RPC")

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
    approve_tx = uni.approve_token(chain, token_in, amount_in)
    swap_tx = uni.swap_exact_input_single(chain, token_in, token_out, fee, amount_in, amount_out_min)
    return {"approve_tx": approve_tx, "swap_tx": swap_tx}

@tool
def add_liquidity_uniswap(chain: str, token0: str, token1: str, fee: int, tick_lower: int, tick_upper: int, amount0: int, amount1: int):
    """
    Adds liquidity to a Uniswap V3 pool.
    """
    approve_tx0 = uni.approve_token(chain, token0, amount0)
    approve_tx1 = uni.approve_token(chain, token1, amount1)
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
    data = asyncio.get_event_loop().run_until_complete(get_wallet_balances(wallet_address))
    return data

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
"""

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
app = workflow.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "user1"}}



# Set your API keys
# Load CDP API credentials from environment variables (set these in your .env file)
os.environ["CDP_API_KEY_ID"] = os.getenv("CDP_API_KEY_ID")
os.environ["CDP_API_KEY_SECRET"] = os.getenv("CDP_API_KEY_SECRET")

client = OpenAI(
    api_key = OPENAI_API_KEY
)


def get_token_price(token_address, chain):
    token_address_string = ",".join(token_address) if isinstance(token_address, list) else token_address
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address_string}"
    headers = {"Accept": "application/json"}

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    pairs = response.json().get("pairs", [])


    return {
        pair["baseToken"]["address"]: float(pair.get("priceUsd", 0.0))
        for pair in pairs
        if "priceUsd" in pair
    }


async def fetch_balances(cdp, address, chain):
    balances = await cdp.evm.list_token_balances(address, chain, page_size=100)
    balances_price = {}

    # Collect basic balance info
    for balance in balances.balances:
        balances_price[balance.token.contract_address] = {
            "symbol": balance.token.symbol,
            "balance": float(balance.amount.amount) / 10**balance.amount.decimals,
            "chain": chain,
        }

    # Batch fetch prices (10 at a time)
    all_balances_price = {}
    for i in range(0, len(balances.balances), 10):
        batch = balances.balances[i : i + 10]
        addresses = [balance.token.contract_address for balance in batch]
        batch_prices = get_token_price(addresses, chain)
        all_balances_price.update(batch_prices)

    # Merge prices into balances
    for balance in balances.balances:
        addr = balance.token.contract_address
        price = all_balances_price.get(addr, 0.0)
        balances_price[addr]["price"] = price
        balances_price[addr]["value_usd"] = balances_price[addr]["balance"] * price


    try:
        # remove goof
        balances_price["0x8e5C04F82d6464b420E2018362E7e7aB813cF190"]["price"] = 0
        balances_price["0x8e5C04F82d6464b420E2018362E7e7aB813cF190"]["value_usd"] = 0
    except KeyError:
        pass

    return balances_price

def categorize_tokens(tokens):
    wallet_tokens = []
    defi_tokens = []
    miscellaneous_tokens = []

    for t, data in tokens.items():
        name = data["symbol"].lower()
        symbol = data["symbol"].lower()

        # Heuristic rules for DeFi/farm/airdrop tokens
        if (
            "moo" in name
            or "farm" in name
            or "stake" in name
            or "lp" in symbol
            or "stk" in symbol
            or "moo" in symbol
            or "cake" in symbol 
            or "mw" in symbol
        ):
            data['protocol'] = "DeFi"
            defi_tokens.append(data)
        elif (
             "airdrop" in name
            or "reward" in name
        ):
            miscellaneous_tokens.append(data)
        else:
            wallet_tokens.append(data)

    return wallet_tokens, defi_tokens, miscellaneous_tokens



async def get_wallet_balances(wallet_address):

    async with CdpClient() as cdp:
        # Base balances
        base_balances_price = await fetch_balances(cdp, wallet_address, "base")

        # Ethereum balances
        eth_balances_price = await fetch_balances(cdp, wallet_address, "ethereum")

        # Merge all balances
        all_balances = {**base_balances_price, **eth_balances_price}


        wallet_tokens, defi_tokens, miscellaneous_tokens = categorize_tokens(all_balances)

        classified_tokens = {
            "wallet_tokens": wallet_tokens,
            "defi_tokens": defi_tokens,
            "miscellaneous_tokens": miscellaneous_tokens
        }

        return classified_tokens





# Configure page
st.set_page_config(
    page_title="DeFi Portfolio Manager",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        text-align: center;
        border-left: 4px solid #667eea;
    }
    
    .wallet-connected {
        background: linear-gradient(45deg, #4CAF50, #45a049);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        border: none;
        font-weight: bold;
    }
    
    .wallet-disconnected {
        background: linear-gradient(45deg, #f44336, #da190b);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        border: none;
        font-weight: bold;
    }
    
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        max-width: 80%;
    }
    
    .user-message {
        background: #e3f2fd;
        margin-left: 20%;
        text-align: right;
    }
    
    .ai-message {
        background: #f3e5f5;
        margin-right: 20%;
    }
    
    .sidebar-metric {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    
    .loading-spinner {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'wallet_connected' not in st.session_state:
    st.session_state.wallet_connected = False
    st.session_state.wallet_address = ""
    st.session_state.wallet_balance = 0
    st.session_state.chat_history = []
    st.session_state.transaction_history = []
    st.session_state.cached_balance_data = None
    st.session_state.cached_defi_data = None
    st.session_state.last_fetch_time = None

# Chain ID mappings
CHAIN_IDS = {
    'Ethereum': 1,
    'Base': 8453
}



def fetch_all_wallet_data(address):
    """Fetch comprehensive wallet data"""
    if not address:
        return None, None, None
    
    # Show loading spinner
    with st.spinner('Fetching wallet data from blockchain...'):
        # Get balance data 
        data = asyncio.get_event_loop().run_until_complete(get_wallet_balances(address))


        balance_data = {}
        balance_data["tokens"] = data['wallet_tokens']
        balance_data["total_balance_usd"] = sum(token['value_usd'] for token in balance_data["tokens"])

        # Get DeFi positions
        defi_data = data['defi_tokens']
        for pos in defi_data:
            pos['status'] = 'Active' 
        
        # Get NFT data
        
        return balance_data, defi_data

def calculate_portfolio_metrics(balance_data, defi_data):
    """Calculate portfolio metrics from real data"""
    if not balance_data:
        return 0, 0, 0, 0
    
    total_crypto = balance_data.get('total_balance_usd', 0)
    total_defi = sum(pos.get('value_usd', 0) for pos in defi_data) if defi_data else 0
    total_portfolio = total_crypto + total_defi
    
    # Calculate 24h change (simulated for demo)
    daily_change = total_portfolio * 0.025  # 2.5% gain
    
    return total_portfolio, total_crypto, total_defi, daily_change




# Sidebar for wallet connection and overview
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #667eea;'>💰 Wallet Overview</h2>", unsafe_allow_html=True)
    
    # Wallet address input
    wallet_input = st.text_input("Enter Wallet Address", 
                                placeholder="0x742d35Cc6634C0532925a3b8D7431C11D23F8000",
                                help="Enter your Ethereum wallet address")
    
    # Chain selector
    selected_chain = st.selectbox("Select Network", list(CHAIN_IDS.keys()), index=0)
    chain_id = CHAIN_IDS[selected_chain]
    
    # Connect wallet button
    if not st.session_state.wallet_connected:
        if st.button("🔗 Connect Wallet", key="connect_wallet") and wallet_input:
            with st.spinner("Connecting to wallet..."):
                # Fetch real wallet data
                balance_data, defi_data = fetch_all_wallet_data(wallet_input)
                
                if balance_data:
                    st.session_state.wallet_connected = True
                    st.session_state.wallet_address = wallet_input
                    st.session_state.cached_balance_data = balance_data
                    st.session_state.cached_defi_data = defi_data
                    st.session_state.last_fetch_time = datetime.now()
                    
                    # Calculate total portfolio value
                    total_portfolio, _, _, _ = calculate_portfolio_metrics(balance_data, defi_data)
                    st.session_state.wallet_balance = total_portfolio
                    
                    st.success("Wallet connected successfully!")
                    st.rerun()             
                else:
                    st.error("Failed to connect wallet. Please check the address.")
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"<div class='wallet-connected'>✅ Connected</div>", unsafe_allow_html=True)
        with col2:
            if st.button("❌", help="Disconnect wallet"):
                st.session_state.wallet_connected = False
                st.session_state.wallet_address = ""
                st.session_state.wallet_balance = .0
                st.session_state.cached_balance_data = None
                st.session_state.cached_defi_data = None
                st.rerun()
        
        st.markdown(f"**Address:** `{st.session_state.wallet_address[:10]}...`")
        st.markdown(f"**Network:** {selected_chain}")
        
        # Refresh data button
        if st.button("🔄 Refresh Data"):
            with st.spinner("Refreshing wallet data..."):
                balance_data, defi_data = fetch_all_wallet_data(st.session_state.wallet_address)
                if balance_data:
                    st.session_state.cached_balance_data = balance_data
                    st.session_state.cached_defi_data = defi_data
                    st.session_state.last_fetch_time = datetime.now()
                    
                    total_portfolio, _, _, _ = calculate_portfolio_metrics(balance_data, defi_data)
                    st.session_state.wallet_balance = total_portfolio
                    st.success("Data refreshed!")
                    st.rerun()
        
        # Show last update time
        if st.session_state.last_fetch_time:
            st.markdown(f"**Last updated:** {st.session_state.last_fetch_time.strftime('%H:%M:%S')}")
    
    # Portfolio metrics in sidebar
    if st.session_state.wallet_connected and st.session_state.cached_balance_data:
        total_portfolio, total_crypto, total_defi, daily_change = calculate_portfolio_metrics(
            st.session_state.cached_balance_data, 
            st.session_state.cached_defi_data
        )
        
        st.markdown("<div class='sidebar-metric'>", unsafe_allow_html=True)
        st.metric("Total Portfolio Value", f"${total_portfolio:,.2f}", 
                 f"+${daily_change:,.2f} (+{(daily_change/total_portfolio)*100:.1f}%)")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='sidebar-metric'>", unsafe_allow_html=True)
        st.metric("Crypto Assets", f"${total_crypto:,.2f}", "+8.2%")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='sidebar-metric'>", unsafe_allow_html=True)
        defi_count = len(st.session_state.cached_defi_data) if st.session_state.cached_defi_data else 0
        st.metric("Active DeFi Positions", str(defi_count), "🟢")
        st.markdown("</div>", unsafe_allow_html=True)

# Main navigation
# st.markdown("<div class='main-header'><h1>🚀 DeFi Portfolio Manager</h1><p>Your Gateway to Decentralized Finance - Real Data Integration</p></div>", unsafe_allow_html=True)

# Navigation tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🤖 AI Chat", "💬 Chat History", "🔗 Transaction History"])

with tab1:
    st.header("📊 Portfolio Dashboard")
    
    if not st.session_state.wallet_connected:
        st.warning("Please connect your wallet to view your portfolio dashboard.")
        
      
    else:
        balance_data = st.session_state.cached_balance_data
        defi_data = st.session_state.cached_defi_data
        
        if balance_data:
            total_portfolio, total_crypto, total_defi, daily_change = calculate_portfolio_metrics(balance_data, defi_data)
            
            # Portfolio overview metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.metric("Total Balance", f"${total_portfolio:,.2f}", 
                         f"+{(daily_change/total_portfolio)*100:.1f}%")
                st.markdown("</div>", unsafe_allow_html=True)
                
            with col2:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.metric("Crypto Assets", f"${total_crypto:,.2f}", "+8.2%")
                st.markdown("</div>", unsafe_allow_html=True)
                
            with col3:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.metric("DeFi Positions", f"${total_defi:,.2f}", "+18.7%")
                st.markdown("</div>", unsafe_allow_html=True)
                
            with col4:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                yield_earned = total_defi * 0.05  # 5% monthly yield estimate
                st.metric("Est. Monthly Yield", f"${yield_earned:,.2f}", "+15.3%")
                st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Real-time data visualization
            col1 = st.columns(1)[0]
            
            with col1:
                st.subheader("🪙 Crypto Assets (Live Data)")
                
                if balance_data.get('tokens'):
                    # Create pie chart for crypto allocation
                    tokens = balance_data['tokens']
                    values = [token['value_usd'] for token in tokens]
                    labels = [token['symbol'] for token in tokens]
                    
                    fig_pie = px.pie(values=values, names=labels, title="Crypto Asset Allocation")
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_pie, use_container_width=True)
                    
                    # Real crypto assets table
                    crypto_df = pd.DataFrame([
                        {
                            'Asset': token['symbol'],
                            'Balance': f"{token['balance']:.4f}",
                            'Price': f"${token['price']:,.2f}",
                            'Value': f"${token['value_usd']:,.2f}",
                            'Weight': f"{(token['value_usd']/total_crypto)*100:.1f}%"
                        }
                        for token in tokens
                    ])
                    st.dataframe(crypto_df, use_container_width=True)
            
           
            
            # Portfolio performance chart (simulated historical data)
            st.subheader("📈 Portfolio Performance (30 days)")
            
            dates = [datetime.now() - timedelta(days=i) for i in range(30, 0, -1)]
            # Generate realistic portfolio performance based on current value
            base_value = total_portfolio
            performance_values = []
            for i in range(30):
                daily_variance = np.random.normal(0, base_value * 0.02)  # 2% daily variance
                trend = (i / 30) * base_value * 0.1  # 10% growth trend over 30 days
                value = base_value - trend + daily_variance
                performance_values.append(max(value, base_value * 0.8))  # Floor at 80% of current
            
            fig_line = px.line(x=dates, y=performance_values, title="Portfolio Value Over Time")
            fig_line.update_traces(line_color='#667eea', line_width=3)
            fig_line.update_layout(
                showlegend=False,
                yaxis_title="Portfolio Value (USD)",
                xaxis_title="Date"
            )
            st.plotly_chart(fig_line, use_container_width=True)
            
        else:
            st.error("Failed to load wallet data. Please try refreshing.")

import streamlit as st
import json
from datetime import datetime
from langgraph.graph import END

# Assuming you already defined your LangGraph workflow & compiled it as `app`
# from your_agent import app

# --- Utility to query LangGraph agent ---
def run_agent_query(user_input, wallet_data=None):
    """
    Run the LangGraph agent with user input and wallet context.
    """

    if st.session_state.wallet_address:
        user_input = f"Wallet: {st.session_state.wallet_address}\n{user_input}"

    # Prepare the state for LangGraph
    state = {
        "messages": [
            {"role": "user", "content": user_input}
        ]
    } 
    # Add wallet data if available
    if wallet_data:
        state["wallet"] = wallet_data

    # Stream/Run the agent
    response = ""
    for output in app.stream(state, config):
        for node, value in output.items():
            print(f"Node: {node}, Value: {value}")
            if node == "agent":
                response = value["messages"][-1].content  # AI response

    return response


# ---------------- STREAMLIT UI ----------------
tab2, tab3 = st.tabs(["AI DeFi Assistant", "Chat History"])

with tab2:
    st.header("🤖 AI DeFi Assistant")
    st.markdown("Ask me anything about your portfolio, DeFi strategies, or blockchain analysis!")

    # Display wallet context
    if st.session_state.wallet_connected:
        with st.expander("📊 Your Wallet Context"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Portfolio Value", f"${st.session_state.wallet_balance:,.2f}")
            with col2:
                defi_count = len(st.session_state.cached_defi_data) if st.session_state.cached_defi_data else 0
                st.metric("DeFi Positions", defi_count)
            with col3:
                token_count = len(st.session_state.cached_balance_data.get('tokens', [])) if st.session_state.cached_balance_data else 0
                st.metric("Token Types", token_count)

    # Chat interface
    with st.container():
        for message in st.session_state.chat_history:
            if message['sender'] == 'user':
                st.markdown(f"<div class='chat-message user-message'><strong>You:</strong> {message['content']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='chat-message ai-message'><strong>AI Assistant:</strong> {message['content']}</div>", unsafe_allow_html=True)

    # Chat input
    user_input = st.chat_input("Ask about your portfolio, DeFi strategies, or market analysis...")

    if user_input:
        # Save user input
        st.session_state.chat_history.append({
            'sender': 'user',
            'content': user_input,
            'timestamp': datetime.now()
        })

        wallet_data = (st.session_state.cached_balance_data, st.session_state.cached_defi_data) if st.session_state.wallet_connected else None

        with st.spinner("Analyzing your portfolio with the AI agent..."):
            ai_response = run_agent_query(user_input, wallet_data)

        st.session_state.chat_history.append({
            'sender': 'ai',
            'content': ai_response,
            'timestamp': datetime.now()
        })

        st.rerun()

    # Quick actions
    if st.session_state.wallet_connected:
        st.markdown("### 🚀 Quick Actions")
        col1, col2, col3, col4 = st.columns(4)
        if col1.button("📊 Analyze Portfolio"):
            st.session_state.chat_history.append({'sender': 'user','content': "Analyze my current portfolio and provide insights",'timestamp': datetime.now()})
            st.rerun()
        if col2.button("💡 Yield Optimization"):
            st.session_state.chat_history.append({'sender': 'user','content': "How can I optimize my yield farming strategies?",'timestamp': datetime.now()})
            st.rerun()
        if col3.button("⚠️ Risk Assessment"):
            st.session_state.chat_history.append({'sender': 'user','content': "Assess the risk level of my current positions",'timestamp': datetime.now()})
            st.rerun()
        if col4.button("🔄 Rebalance Advice"):
            st.session_state.chat_history.append({'sender': 'user','content': "Should I rebalance my portfolio?",'timestamp': datetime.now()})
            st.rerun()

with tab3:
    st.header("💬 Chat History")
    if not st.session_state.chat_history:
        st.info("No chat history yet. Start a conversation with the AI assistant!")
    else:
        total_messages = len(st.session_state.chat_history)
        user_messages = len([msg for msg in st.session_state.chat_history if msg['sender'] == 'user'])

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Messages", total_messages)
        col2.metric("Your Messages", user_messages)
        col3.metric("AI Responses", total_messages - user_messages)

        st.markdown("---")

        for message in st.session_state.chat_history:
            with st.expander(f"{message['sender'].title()} - {message['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}"):
                st.write(message['content'])

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Export Chat History"):
                chat_export = json.dumps(st.session_state.chat_history, default=str, indent=2)
                st.download_button(
                    label="Download JSON",
                    data=chat_export,
                    file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        with col2:
            if st.button("🗑️ Clear Chat History"):
                st.session_state.chat_history = []
                st.rerun()


# Footer
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<div style='text-align: center; color: #666;'>Built with ❤️ for the DeFi community | Powered by Streamlit</div>", unsafe_allow_html=True)