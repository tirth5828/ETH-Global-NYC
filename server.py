"""
Cross-Chain Investment Analysis Agent for Agentverse
Provides AI-powered portfolio analysis and cross-chain yield optimization
"""

import requests
import json
from datetime import datetime
from uagents import Agent, Context, Model
from typing import Dict, List

# Data Models for Agentverse
class PortfolioQuery(Model):
    wallet_address: str
    chains: List[str]
    query: str
    sender_address: str

class MarketAnalysis(Model):
    analysis: str
    confidence: float
    timestamp: str
    portfolio_value: float
    recommendations: List[str]


class MarketAnalysis(Model):
    analysis: str
    confidence: float
    timestamp: str
    portfolio_value: float
    recommendations: List[str]

class RouteQuery(Model):
    src_chain: str = Field(..., description="Source chain key")
    src_token: str = Field(..., description="Token symbol or node id")
    dst_chain: str = Field(..., description="Destination chain key")
    dst_token: str = Field(..., description="Token symbol or node id")
    top_k: int = Field(default=3, description="Number of routes to return")

class RouteResult(Model):
    routes: list
    note: str

ROUTER_AGENT = "agent1qdyxx3zeumxz8fm6zwyxxcgm9kn02rn4jzxe6yk6j9rdz8yzj9h3wctesq6"


# Initialize agent for Agentverse
agent = Agent(
    name="cross_chain_investment_advisor",
    seed="investment_advisor_seed_2025"
)

def get_investment_analysis(query: str, wallet_data: Dict) -> str:
    """
    Generate comprehensive investment analysis
    Falls back to detailed analysis if API unavailable
    """
    
    # Enhanced fallback analysis for demo
    total_value = wallet_data.get('total_value_usd', 0)
    chains = list(wallet_data.get('chains', {}).keys())
    
    analysis = """
    🌐 CROSS-CHAIN INVESTMENT ANALYSIS
    ----------------------------------

    📊 PORTFOLIO OVERVIEW
    💰 Total Value: ${total_value:,.2f}
    🔗 Active Chains: {chains}
    📈 Analysis Type: {query}

    🎯 KEY RECOMMENDATIONS
    1. **YIELD OPTIMIZATION STRATEGY**
    • Bridge 30% of USDC to Polygon for Aave lending (4.2% APY)  
    • Consider QuickSwap MATIC/USDC LP farming (18.7% APY)  
    • Explore Arbitrum GMX GLP staking (15.3% APY)  

    2. **CROSS-CHAIN OPPORTUNITIES**
    • Ethereum: Maintain 40% for security (Aave, Compound)  
    • Polygon: 35% for high-yield farming (QuickSwap, SushiSwap)  
    • Arbitrum: 25% for emerging DeFi protocols (GMX, Camelot)  

    3. **RISK MANAGEMENT**
    • Current Portfolio Risk: MEDIUM  
    • Recommended Allocation: 60% stable, 40% growth  
    • Diversification Score: 8/10  
    • Impermanent Loss Risk: LOW–MEDIUM  

    4. **EXECUTION ROADMAP**
    1. Bridge assets using LI.FI for optimal routing  
    2. Start with 10% test positions  
    3. Monitor for 1 week before scaling  
    4. Set up automated rebalancing alerts  

    📈 EXPECTED RETURNS
    • Conservative estimate: 8–12% APY  
    • Moderate risk: 12–18% APY  
    • Higher risk strategies: 18–25% APY  

    ⚠️ RISK FACTORS
    • Smart contract risk across protocols  
    • Bridge security considerations  
    • Market volatility impact  
    • Gas cost optimization needed  

    💡 NEXT ACTIONS
    1. Use LI.FI SDK for cross-chain routing  
    2. Set up Circle Wallet for multi-chain management  
    3. Implement dollar-cost averaging  
    4. Monitor yield changes weekly  

    🎯 CONFIDENCE SCORE: 85%
    """.format(
        total_value=total_value,
        chains=", ".join(chains),
        query=query
    )

    
    # Try ASI1 API if available (optional for Agentverse)
    try:
        api_key = "ASI API key"
        
        if api_key and "json" not in query.lower():
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "asi1-mini",
                "messages": [
                    {"role": "system", "content": "You are an expert DeFi investment advisor specializing in cross-chain yield optimization."},
                    {"role": "user", "content": f"Analyze this portfolio and provide investment advice: {json.dumps(wallet_data)}. Query: {query}"}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            response = requests.post("https://api.asi1.ai/v1/chat/completions", 
                                   json=data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"].strip()
    
    except Exception as e:
        # Fallback to comprehensive analysis
        pass
    
    return analysis

async def fetch_portfolio_data(wallet_address: str, chains: List[str]) -> Dict:
    """
    Fetch comprehensive portfolio data across multiple chains
    """
    
    # Enhanced mock data that simulates real portfolio
    '''
    TODO: to put wallet data using coinbase from Teerth
    '''
    mock_portfolio_data = {
        "ethereum": {
            "chain": "ethereum",
            "value_usd": 5000.0,
            "tokens": [
                {"symbol": "ETH", "balance": "2.1", "value_usd": 3400, "price": 1619},
                {"symbol": "USDC", "balance": "1600", "value_usd": 1600, "price": 1.00}
            ],
            "defi_positions": [
                {"protocol": "Aave", "position": "ETH lending", "value_usd": 1000, "apy": 3.2},
                {"protocol": "Uniswap V3", "position": "ETH/USDC LP", "value_usd": 800, "apy": 12.5},
                {"protocol": "Compound", "position": "USDC lending", "value_usd": 500, "apy": 2.8}
            ],
            "gas_cost_24h": 45.20
        },
        "polygon": {
            "chain": "polygon",
            "value_usd": 2500.0,
            "tokens": [
                {"symbol": "MATIC", "balance": "1200", "value_usd": 800, "price": 0.67},
                {"symbol": "USDC", "balance": "1700", "value_usd": 1700, "price": 1.00}
            ],
            "defi_positions": [
                {"protocol": "QuickSwap", "position": "MATIC/USDC LP", "value_usd": 1200, "apy": 18.7},
                {"protocol": "Aave", "position": "USDC lending", "value_usd": 500, "apy": 4.1},
                {"protocol": "SushiSwap", "position": "WETH/USDC LP", "value_usd": 400, "apy": 15.3}
            ],
            "gas_cost_24h": 0.25
        },
        "arbitrum": {
            "chain": "arbitrum",
            "value_usd": 3000.0,
            "tokens": [
                {"symbol": "ARB", "balance": "800", "value_usd": 600, "price": 0.75},
                {"symbol": "ETH", "balance": "1.2", "value_usd": 1940, "price": 1617},
                {"symbol": "USDC", "balance": "460", "value_usd": 460, "price": 1.00}
            ],
            "defi_positions": [
                {"protocol": "GMX", "position": "GLP staking", "value_usd": 1500, "apy": 15.3},
                {"protocol": "Camelot", "position": "ARB/ETH LP", "value_usd": 900, "apy": 22.1},
                {"protocol": "Radiant", "position": "USDC lending", "value_usd": 300, "apy": 6.8}
            ],
            "gas_cost_24h": 1.50
        },
        "sepolia": {
            "chain": "sepolia",
            "value_usd": 500.0,
            "tokens": [
                {"symbol": "SepoliaETH", "balance": "0.8", "value_usd": 400, "price": 500},
                {"symbol": "TestUSDC", "balance": "100", "value_usd": 100, "price": 1.00}
            ],
            "defi_positions": [
                {"protocol": "Test Aave", "position": "ETH lending", "value_usd": 200, "apy": 5.0}
            ],
            "gas_cost_24h": 0.00
        }
    }
    
    # Build portfolio response
    portfolio = {
        "wallet_address": wallet_address,
        "total_value_usd": 0,
        "chains": {},
        "total_tokens": 0,
        "total_defi_positions": 0,
        "risk_score": 6.5,
        "diversification_score": 8.2
    }
    
    for chain in chains:
        chain_lower = chain.lower()
        if chain_lower in mock_portfolio_data:
            chain_data = mock_portfolio_data[chain_lower]
            portfolio["chains"][chain] = chain_data
            portfolio["total_value_usd"] += chain_data["value_usd"]
            portfolio["total_tokens"] += len(chain_data["tokens"])
            portfolio["total_defi_positions"] += len(chain_data["defi_positions"])
    
    return portfolio


# ======================
# Router Response Handler
# ======================
@agent.on_message(model=RouteResult)
async def handle_routes(ctx: Context, sender: str, msg: RouteResult):
    ctx.logger.info(f"📬 Received routes from router agent: {sender}")
    ctx.logger.info(f"🛤️ Note: {msg.note}")
    
    if msg.routes:
        for idx, r in enumerate(msg.routes, 1):
            ctx.logger.info(f"➡️ Route {idx}: hops={r['hops']} cost={r['total_cost']:.6f}")
            for step in r['steps']:
                ctx.logger.info(f"   {step}")
    else:
        ctx.logger.warning(" No routes received")


@agent.on_message(model=PortfolioQuery)
async def handle_portfolio_analysis(ctx: Context, sender: str, msg: PortfolioQuery):
    ctx.logger.info(f"📨 Portfolio analysis request from {sender}")
    try:
        portfolio_data = await fetch_portfolio_data(msg.wallet_address, msg.chains)
        analysis = get_investment_analysis(msg.query, portfolio_data)

        # Optional: Send routing query to external router
        route_query = RouteQuery(
            src_chain="eth", src_token="USDC",
            dst_chain="base", dst_token="WETH"
        )
        await ctx.send(ROUTER_AGENT, route_query)

        recommendations = [
            "Bridge 30% USDC to Polygon for higher yields",
            "Stake GLP on Arbitrum (15.3% APY)",
            "Monitor gas cost vs APY",
        ]

        result = MarketAnalysis(
            analysis=analysis,
            confidence=0.85,
            timestamp=datetime.now().isoformat(),
            portfolio_value=portfolio_data["total_value_usd"],
            recommendations=recommendations
        )
        await ctx.send(sender, result)
    except Exception as e:
        ctx.logger.error(f"❌ Error: {e}")
        await ctx.send(sender, MarketAnalysis(
            analysis=f"Error: {str(e)}",
            confidence=0.0,
            timestamp=datetime.now().isoformat(),
            portfolio_value=0.0,
            recommendations=["Check inputs", "Try again"]
        ))







@agent.on_event("startup")
async def startup_message(ctx: Context):
    """Initialize the Cross-Chain Investment Advisor"""
    ctx.logger.info("🚀 Cross-Chain Investment Advisor Agent Started!")
    ctx.logger.info(f"📍 Agent Address: {ctx.agent.address}")
    ctx.logger.info("🌐 Ready to analyze cross-chain portfolios and provide investment advice")
    ctx.logger.info("💡 Supports: Ethereum, Polygon, Arbitrum, and other major chains")
    ctx.logger.info("🎯 Features: Yield optimization, risk analysis, cross-chain routing")


@agent.on_message(model=PortfolioQuery)
async def handle_portfolio_analysis(ctx: Context, sender: str, msg: PortfolioQuery):
    ctx.logger.info(f"📨 Portfolio analysis request from: {sender}")
    ctx.logger.info(f"💼 Wallet: {msg.wallet_address}")
    ctx.logger.info(f"🔗 Chains: {msg.chains}")
    ctx.logger.info(f"❓ Query: {msg.query}")
    
    try:
        # Fetch portfolio data
        portfolio_data = await fetch_portfolio_data(msg.wallet_address, msg.chains)
        ctx.logger.info(f"💰 Portfolio value: ${portfolio_data['total_value_usd']:,.2f}")
        
        # Generate analysis
        analysis = get_investment_analysis(msg.query, portfolio_data)
        
        # Example: decide to bridge USDC → WETH across chains
        query = RouteQuery(
            src_chain="eth", src_token="USDC",
            dst_chain="base", dst_token="WETH",
            top_k=3
        )
        await ctx.send(ROUTER_AGENT, query)
        ctx.logger.info("📤 Sent RouteQuery to router agent")

        # Send immediate analysis response
        recommendations = [
            "Bridge 30% USDC to Polygon for higher yields",
            "Consider GMX GLP staking on Arbitrum (15.3% APY)", 
            "Diversify across Aave, Compound, and QuickSwap",
            "Monitor gas costs vs yield returns",
            "Set up automated rebalancing alerts"
        ]
        
        response = MarketAnalysis(
            analysis=analysis,
            confidence=0.85,
            timestamp=datetime.now().isoformat(),
            portfolio_value=portfolio_data['total_value_usd'],
            recommendations=recommendations
        )
        
        await ctx.send(sender, response)
        ctx.logger.info(f"✅ Analysis sent to {sender}")
        
    except Exception as e:
        ctx.logger.error(f"❌ Error processing request: {e}")
        
        error_response = MarketAnalysis(
            analysis=f"Error processing portfolio analysis: {str(e)}",
            confidence=0.0,
            timestamp=datetime.now().isoformat(),
            portfolio_value=0.0,
            recommendations=["Retry request", "Check wallet address", "Verify chain names"]
        )
        await ctx.send(sender, error_response)



@agent.on_message(model=PortfolioQuery)
async def handle_portfolio_analysis(ctx: Context, sender: str, msg: PortfolioQuery):
    """
    Main handler for portfolio analysis requests
    """
    ctx.logger.info(f"📨 Portfolio analysis request from: {sender}")
    ctx.logger.info(f"💼 Wallet: {msg.wallet_address}")
    ctx.logger.info(f"🔗 Chains: {msg.chains}")
    ctx.logger.info(f"❓ Query: {msg.query}")
    
    try:
        # Fetch portfolio data
        portfolio_data = await fetch_portfolio_data(msg.wallet_address, msg.chains)
        ctx.logger.info(f"💰 Portfolio value: ${portfolio_data['total_value_usd']:,.2f}")
        
        # Generate analysis
        analysis = get_investment_analysis(msg.query, portfolio_data)
        
        # Extract recommendations for structured response
        recommendations = [
            "Bridge 30% USDC to Polygon for higher yields",
            "Consider GMX GLP staking on Arbitrum (15.3% APY)", 
            "Diversify across Aave, Compound, and QuickSwap",
            "Monitor gas costs vs yield returns",
            "Set up automated rebalancing alerts"
        ]
        
        # Send comprehensive response
        response = MarketAnalysis(
            analysis=analysis,
            confidence=0.85,
            timestamp=datetime.now().isoformat(),
            portfolio_value=portfolio_data['total_value_usd'],
            recommendations=recommendations
        )
        
        await ctx.send(sender, response)
        ctx.logger.info(f"✅ Analysis sent to {sender}")
        
    except Exception as e:
        ctx.logger.error(f"❌ Error processing request: {e}")
        
        # Send error response
        error_response = MarketAnalysis(
            analysis=f"Error processing portfolio analysis: {str(e)}. Please try again.",
            confidence=0.0,
            timestamp=datetime.now().isoformat(),
            portfolio_value=0.0,
            recommendations=["Retry request", "Check wallet address", "Verify chain names"]
        )
        
        await ctx.send(sender, error_response)

# Optional: Add interval-based market updates
@agent.on_interval(period=3600.0)  # Every hour
async def market_update(ctx: Context):
    """
    Periodic market updates and notifications
    """
    ctx.logger.info("📊 Performing hourly market analysis update")
    ctx.logger.info("🔍 Monitoring yield changes across protocols")
    # Could add alerts for significant yield changes, new opportunities, etc.



# ======================
# Router Response Handler
# ======================

@agent.on_message(model=RouteResult)
async def handle_routes(ctx: Context, sender: str, msg: RouteResult):
    ctx.logger.info(f"📬 Received routes from router agent: {sender}")
    ctx.logger.info(f"🛤️ Note: {msg.note}")

    # Retrieve original sender
    user = ctx.storage.get("last_request_sender")

    if user:
        # You can format a new message back to user
        await ctx.send(user, MarketAnalysis(
            analysis="📦 Routing complete: Best routes have been received.",
            confidence=0.75,
            timestamp=datetime.now().isoformat(),
            portfolio_value=0.0,  # Optional: reuse old value
            recommendations=[
                f"Use route via {msg.routes[0]['hops']} with cost {msg.routes[0]['total_cost']:.4f}",
                "Use LI.FI or Socket bridge to execute it",
                "Monitor gas cost and slippage"
            ]
        ))
        ctx.logger.info(f"📤 Route summary sent to original user: {user}")
    else:
        ctx.logger.warning("❗ Original sender not found in storage")



if __name__ == "__main__":
    agent.run()