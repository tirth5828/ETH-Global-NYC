"""
Investment Portfolio Client - Sends queries to market agent
"""

from uagents import Agent, Context, Model
from typing import List

# Models must match market agent
class PortfolioQuery(Model):
    wallet_address: str
    chains: List[str]
    query: str
    sender_address: str


# =========================
# Message Models
# =========================

class RouteQuery(Model):
    src_chain: str = Field(description="Source chain key (e.g., 'eth', 'base')")
    src_token: str = Field(description="Source token symbol or node id")
    dst_chain: str = Field(description="Destination chain key (e.g., 'eth', 'base')")
    dst_token: str = Field(description="Destination token symbol or node id")
    top_k: int = Field(description="Number of routes to return", default=3)
    # optional overrides
    max_hops: Optional[int] = Field(default=None)
    min_liquidity: Optional[float] = Field(default=None)
    min_tvl: Optional[float] = Field(default=None)

# =========================
# Message Models
# =========================

class RouteQuery(Model):
    src_chain: str = Field(description="Source chain key (e.g., 'eth', 'base')")
    src_token: str = Field(description="Source token symbol or node id")
    dst_chain: str = Field(description="Destination chain key (e.g., 'eth', 'base')")
    dst_token: str = Field(description="Destination token symbol or node id")
    top_k: int = Field(description="Number of routes to return", default=3)
    # optional overrides
    max_hops: Optional[int] = Field(default=None)
    min_liquidity: Optional[float] = Field(default=None)
    min_tvl: Optional[float] = Field(default=None)

class RouteStep(Model):
    kind: str
    from_node: str
    to_node: str
    chain: Optional[str] = ""
    pool: Optional[str] = ""
    weight: float


class RouteCandidate(Model):
    total_cost: float
    hops: int
    steps: List[RouteStep]

class RouteResult(Model):
    routes: List[RouteCandidate]
    note: str
    debug_info: Optional[Dict] = None  # Added for debugging



class MarketAnalysis(Model):
    analysis: str
    confidence: float
    timestamp: str
    portfolio_value: float
    recommendations: List[str]

agent = Agent(
    name="investment_portfolio_client",
    seed="client_seed_2025"
)

# UPDATE THIS with your market agent address!
MARKET_AGENT_ADDRESS = "agent1qg329zhupuudh4m7z5g2wp37ckl5w5vz6fs53se3lej06rl6uj9xya8qygf"
ROUTING_AGENT_ADDRESS = "agent1qdyxx3zeumxz8fm6zwyxxcgm9kn02rn4jzxe6yk6j9rdz8yzj9h3wctesq6"
@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info("🚀 Portfolio Client Started!")
    ctx.logger.info(f"📍 My Address: {ctx.agent.address}")
    ctx.logger.info(f"🎯 Target Agent: {MARKET_AGENT_ADDRESS}")
    
    # Send demo query immediately
    await send_demo_query(ctx)

async def send_demo_query(ctx: Context):
    """Send a demo portfolio query"""
    
    query = PortfolioQuery(
        wallet_address="0xf71657318e9b5a5b5173d16327e34e4675ec5d56",
        chains=["ethereum", "polygon", "arbitrum"],
        query="Analyze my cross-chain portfolio and suggest optimal yield strategies",
        sender_address=ctx.agent.address
    )
    
    try:
        ctx.logger.info("📤 Sending portfolio query...")
        await ctx.send(MARKET_AGENT_ADDRESS, query)
        ctx.logger.info("✅ Query sent successfully!")
    except Exception as e:
        ctx.logger.error(f"❌ Error: {e}")
    
    ctx.logger.info("📊 Performing hourly market update")
    query = RouteQuery(
        src_chain="eth",
    src_token="Wrapped BTC",
    dst_chain="eth", 
    dst_token="Wrapped Ether",
    top_k=2,
    max_hops=2,
    min_liquidity=50e6,  # Pool has $347M TVL
    min_tvl=100e6
    )

    try:
        ctx.logger.info("📤 Sending RouteQuery to routing agent...")
        await ctx.send(ROUTING_AGENT_ADDRESS, query)
    except Exception as e:
        ctx.logger.error(f"❌  Routing Error: {e}")


@agent.on_message(model=RouteResult)
async def handle_route_result(ctx: Context, sender: str, msg: RouteResult):
    ctx.logger.info(f"✅ Received RouteResult from routing agent. with Len: {len(msg.routes)}")
    ctx.logger.info(f"📝 Note from agent: {msg.debug_info}")
    for i, route in enumerate(msg.routes):
        ctx.logger.info(f"🔹 Route {i+1}: Total Cost = {route.total_cost:.6f}, Hops = {route.hops}")
        for step in route.steps:
            ctx.logger.info(f"   → {step.kind.upper()} | {step.from_node} ➝ {step.to_node} on {step.chain}")

    # Store best route
    if msg.routes:
        best_route = msg.routes[0]
        await ctx.storage.set("last_best_route", best_route.dict())
        ctx.logger.info("💾 Stored best route.")


@agent.on_message(model=MarketAnalysis)
async def handle_market_analysis(ctx: Context, sender: str, msg: MarketAnalysis):
    ctx.logger.info("🎉 ANALYSIS RECEIVED!")
    ctx.logger.info(f"💰 Portfolio Value: ${msg.portfolio_value:,.2f}")
    ctx.logger.info(f"🎯 Confidence: {msg.confidence * 100:.1f}%")
    ctx.logger.info("📊 Analysis:")

    for line in msg.analysis.split('\n')[:10]:
        if line.strip():
            ctx.logger.info(line.strip())

    ctx.logger.info("🎯 Recommendations:")
    for i, rec in enumerate(msg.recommendations, 1):
        ctx.logger.info(f"{i}. {rec}")
if __name__ == "__main__":
    agent.run()