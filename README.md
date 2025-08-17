# 🚀 DeFi Portfolio Manager

**DeFi Portfolio Manager** is a comprehensive web application built with **Streamlit** that allows users to manage, analyze, and interact with their cryptocurrency and DeFi portfolio. The app integrates real-time blockchain data, portfolio analytics, and an AI assistant capable of providing insights, trading strategies, and risk assessment.

---

## Features

### 1. Wallet Management

* Connect your **Ethereum** or **Base** wallet.
* View balances of all tokens, including crypto assets, DeFi positions, and miscellaneous tokens (e.g., airdrops).
* Refresh wallet data in real-time.
* Overview of portfolio metrics like total value, crypto assets, DeFi positions, and estimated monthly yield.

### 2. Portfolio Dashboard

* **Crypto Asset Allocation** via interactive pie charts.
* **Portfolio Performance** over the last 30 days (simulated historical trend).
* Detailed tables showing token balances, prices, and USD value.
* Summary of portfolio metrics like total balance, crypto holdings, DeFi positions, and estimated yield.

### 3. AI DeFi Assistant

* Ask questions about your portfolio, yield strategies, or general DeFi insights.
* AI is powered by **LangGraph + OpenAI GPT-4o-mini** and integrates wallet context for personalized responses.
* Quick action buttons:

  * Analyze Portfolio
  * Yield Optimization
  * Risk Assessment
  * Rebalancing Advice

### 4. Chat History

* Keep track of conversations with the AI assistant.
* Export chat history as JSON.
* Clear chat history anytime.

### 5. Blockchain & DeFi Integration

* **Uniswap V3**: Swap tokens, add/remove liquidity.
* **CCTP (Cross-Chain Transfer)**: Bridge USDC between ETH and Base chains.
* Fetch trending crypto coins via **CoinGecko** API.
* Real-time token prices using **DexScreener API**.

---

## Tech Stack

* **Frontend / Web**: Streamlit
* **AI / NLP**: LangGraph, LangChain, OpenAI GPT-4o-mini
* **Blockchain Interaction**: Web3.py, CDP Client, Uniswap V3, CCTP
* **Data Visualization**: Plotly, Pandas, NumPy
* **APIs**: CoinGecko, DexScreener, TavilySearch
* **Python**: 3.10+

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/defi-portfolio-manager.git
cd defi-portfolio-manager
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate      # Linux / macOS
venv\Scripts\activate         # Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file with the following keys:

```
OPENAI_API_KEY=<your_openai_api_key>
TAVILY_API_KEY=<your_tavily_api_key>
WALLET_PRIVATE_KEY=<your_wallet_private_key>
INFURA_MAINNET_RPC=<your_infura_rpc_url>
CDP_API_KEY_ID=<your_cdp_api_key_id>
CDP_API_KEY_SECRET=<your_cdp_api_key_secret>
```

---

## Usage

Run the Streamlit app:

```bash
streamlit run app.py
```

Open your browser and navigate to:

```
http://localhost:8501
```

---

## How to Use

1. Enter your wallet address and select a network (Ethereum or Base).
2. Click **Connect Wallet** to fetch balances and DeFi positions.
3. Explore your portfolio dashboard for crypto allocation and performance.
4. Interact with the **AI DeFi Assistant** for insights or strategy suggestions.
5. Check **Chat History** or export your conversations.
6. Use **Quick Actions** for immediate AI analysis or portfolio recommendations.

---


## Notes

* Only **USDC** is supported for cross-chain bridging.
* Real-time token prices are fetched from DexScreener and may not include all tokens.

