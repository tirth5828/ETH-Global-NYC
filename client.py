"""
Fixed Investment Portfolio Client - Works with bulletproof router
"""

from uagents import Agent, Context, Model, Field
from typing import List, Optional, Dict

# =========================
# Models for Market Agent
# =========================

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

# =========================
# Models for Routing Agent (MUST MATCH EXACTLY)
# =========================

class RouteQuery(Model):
    src_chain: str = Field(description="Source chain key (e.g., 'eth', 'base')")
    src_token: str = Field(description="Source token symbol or node id")
    dst_chain: str = Field(description="Destination chain key (e.g., 'eth', 'base')")
    dst_token: str = Field(description="Destination token symbol or node id")
    top_k: int = Field(description="Number of routes to return", default=3)
    max_hops: Optional[int] = Field(default=None)
    min_liquidity: Optional[float] = Field(default=None)
    min_tvl: Optional[float] = Field(default=None)

class RouteStep(Model):
    kind: str
    from_node: str
    to_node: str
    chain: Optional[str] = ""     # <-- include this
    pool: Optional[str] = ""      # keep Optional for matching
    weight: float

class RouteCandidate(Model):
    total_cost: float
    hops: int
    steps: List[RouteStep]

class RouteResult(Model):
    routes: List[RouteCandidate]
    note: str
    debug_info: Optional[Dict] = None

# =========================
# Client Agent
# =========================

agent = Agent(
    name="investment_portfolio_client",
    seed="client_seed_2025"
)

# UPDATE THESE with your actual agent addresses!
MARKET_AGENT_ADDRESS = "agent1qg329zhupuudh4m7z5g2wp37ckl5w5vz6fs53se3lej06rl6uj9xya8qygf"
ROUTING_AGENT_ADDRESS = "agent1qdyxx3zeumxz8fm6zwyxxcgm9kn02rn4jzxe6yk6j9rdz8yzj9h3wctesq6"  # UPDATE THIS

@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info("🚀 Portfolio Client Started!")
    ctx.logger.info(f"📍 My Address: {ctx.agent.address}")
    ctx.logger.info(f"🎯 Market Agent: {MARKET_AGENT_ADDRESS}")
    ctx.logger.info(f"🛣️  Routing Agent: {ROUTING_AGENT_ADDRESS}")
    
    # Send demo queries
    await send_demo_market_query(ctx)
    await send_demo_routing_query(ctx)

async def send_demo_market_query(ctx: Context):
    """Send a demo portfolio query to market agent"""
    
    query = PortfolioQuery(
        wallet_address="0xf71657318e9b5a5b5173d16327e34e4675ec5d56",
        chains=["ethereum", "polygon", "arbitrum"],
        query="Analyze my cross-chain portfolio and suggest optimal yield strategies",
        sender_address=ctx.agent.address
    )
    
    try:
        ctx.logger.info("📤 Sending portfolio query to market agent...")
        await ctx.send(MARKET_AGENT_ADDRESS, query)
        ctx.logger.info("✅ Market query sent successfully!")
    except Exception as e:
        ctx.logger.error(f"❌ Market query error: {e}")

async def send_demo_routing_query(ctx: Context):
    """Send a demo routing query to bulletproof router"""
    
    # Test Query 1: Direct path (should work)
    query_usdc = RouteQuery(
    src_chain="eth",
    src_token="Wrapped BTC",
    dst_chain="eth",
    dst_token="USD Coin",
    top_k=2,
    min_tvl=1_000_000  # 👈 allow the WBTC-USDC pool (TVL ~ $1.03M)
    )
    
    
    # Test Query 2: Multi-hop path (should work)
    query2 = RouteQuery(
        src_chain="eth",
        src_token="Wrapped BTC",    # BTC -> ETH -> USDT (2 hops)
        dst_chain="eth",
        dst_token="Tether USD",     # Available in bulletproof router
        top_k=3
    )
    
    # Test Query 3: Direct path
    query3 = RouteQuery(
        src_chain="eth",
        src_token="Wrapped Ether",  # Available in bulletproof router
        dst_chain="eth",
        dst_token="Tether USD",     # Available in bulletproof router  
        top_k=1
    )

    queries = [
        ("Direct BTC->USDC", query_usdc),
        ("Multi-hop BTC->USDT", query2), 
        ("Direct ETH->USDT", query3)
    ]

    for name, query in queries:
        try:
            ctx.logger.info(f"📤 Sending {name} query to routing agent...")
            await ctx.send(ROUTING_AGENT_ADDRESS, query)
            ctx.logger.info(f"✅ {name} query sent!")
            
            # Small delay between queries
            import asyncio
            await asyncio.sleep(1)
            
        except Exception as e:
            ctx.logger.error(f"❌ Routing query error ({name}): {e}")

@agent.on_message(model=RouteResult)
async def handle_route_result(ctx: Context, sender: str, msg: RouteResult):
    ctx.logger.info(f"🎉 ROUTE RESULT RECEIVED from {sender}")
    ctx.logger.info(f"📝 Note: {msg.note}")
    ctx.logger.info(f"🛣️  Found {len(msg.routes)} routes")
    
    if msg.debug_info:
        ctx.logger.info(f"🔍 Debug info: {msg.debug_info}")
    
    # Log each route
    for i, route in enumerate(msg.routes, 1):
        ctx.logger.info(f"🔹 Route {i}: Cost = {route.total_cost:.6f}, Hops = {route.hops}")
        
        for j, step in enumerate(route.steps, 1):
            ctx.logger.info(f"   Step {j}: {step.kind.upper()} | {step.from_node} ➝ {step.to_node}")
            if step.pool:
                ctx.logger.info(f"           via pool: {step.pool}")

    # Store best route
    if msg.routes:
        best_route = msg.routes[0]
        await ctx.storage.set("last_best_route", {
            "cost": best_route.total_cost,
            "hops": best_route.hops,
            "path": [step.from_node for step in best_route.steps] + [best_route.steps[-1].to_node] if best_route.steps else []
        })
        ctx.logger.info("💾 Stored best route in storage")

@agent.on_message(model=MarketAnalysis)  
async def handle_market_analysis(ctx: Context, sender: str, msg: MarketAnalysis):
    ctx.logger.info("🎉 MARKET ANALYSIS RECEIVED!")
    ctx.logger.info(f"💰 Portfolio Value: ${msg.portfolio_value:,.2f}")
    ctx.logger.info(f"🎯 Confidence: {msg.confidence * 100:.1f}%")
    ctx.logger.info(f"📅 Timestamp: {msg.timestamp}")
    
    ctx.logger.info("📊 Analysis:")
    for line in msg.analysis.split('\n')[:10]:
        if line.strip():
            ctx.logger.info(f"   {line.strip()}")

    ctx.logger.info("🎯 Recommendations:")
    for i, rec in enumerate(msg.recommendations, 1):
        ctx.logger.info(f"   {i}. {rec}")

# Optional: Add a periodic query function
@agent.on_interval(period=300.0)  # Every 5 minutes
async def periodic_routing_check(ctx: Context):
    """Send a periodic routing query for monitoring"""
    
    query = RouteQuery(
        src_chain="eth",
        src_token="Wrapped Ether",
        dst_chain="eth",
        dst_token="USD Coin", 
        top_k=1
    )
    
    try:
        ctx.logger.info("🔄 Periodic routing check...")
        await ctx.send(ROUTING_AGENT_ADDRESS, query)
    except Exception as e:
        ctx.logger.error(f"❌ Periodic routing error: {e}")

if __name__ == "__main__":
    agent.run()
'''
"""
Fixed Investment Portfolio Client - Works with bulletproof router
"""

# Optional: Add a periodic query function
@agent.on_interval(period=300.0)  # Every 5 minutes
async def periodic_routing_check(ctx: Context):
    """Send a periodic routing query for monitoring"""
    
    query = RouteQuery(
        src_chain="eth",
        src_token="Wrapped Ether",
        dst_chain="eth",
        dst_token="USD Coin", 
        top_k=1
    )
    
    try:
        ctx.logger.info("🔄 Periodic routing check...")
        await ctx.send(ROUTING_AGENT_ADDRESS, query)
    except Exception as e:
        ctx.logger.error(f"❌ Periodic routing error: {e}")

if __name__ == "__main__":
    agent.run()
'''