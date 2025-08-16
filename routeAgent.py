"""
Ultimate Debug Router - This WILL show us the exact error
"""

import os
import json
import heapq
import traceback
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from uagents import Agent, Context, Model, Field

# =========================
# Config
# =========================

@dataclass
class EdgeCostConfig:
    alpha_liquidity: float = 1.0
    beta_tvl: float = 0.3
    gamma_gas_per_swap: float = 0.0008
    bridge_penalty: float = 0.008
    slippage_bias: float = 0.002
    min_liquidity: float = 1e6
    min_tvl: float = 5e6
    max_hops: int = 6

CFG = EdgeCostConfig()

SAMPLE_JSON_DATA = """{
    "directed": false,
    "multigraph": false,
    "graph": {},
    "nodes": [
        {
            "type": "central_token",
            "chain": "eth",
            "id": "eth_CENTRAL"
        },
        {
            "type": "token",
            "name": "USD Coin",
            "chain": "eth",
            "id": "eth_0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
        },
        {
            "type": "token",
            "name": "Wrapped Ether",
            "chain": "eth",
            "id": "eth_0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
        },
        {
            "type": "token",
            "name": "Wrapped BTC",
            "chain": "eth",
            "id": "eth_0x2260fac5e5542a773aa44fbcfedf7c193bc2c599"
        },
        {
            "type": "token",
            "name": "Tether USD",
            "chain": "eth",
            "id": "eth_0xdac17f958d2ee523a2206206994597c13d831ec7"
        },
        {
            "type": "pool",
            "totalValueLockedUSD": "347058837.4395270847993059147313177",
            "volumeUSD": "32574023025.8564861950144811237988",
            "liquidity": "88193802263256331",
            "token0": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",
            "token1": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
            "token0Name": "Wrapped BTC",
            "token1Name": "Wrapped Ether",
            "chain": "eth",
            "id": "eth_0xcbcdf9626bc03e24f779434178a73a0b4bad62ed"
        },
        {
            "type": "pool",
            "totalValueLockedUSD": "99834192.97886039249301349618739188",
            "volumeUSD": "125900541458.6047418850824937505131",
            "liquidity": "632554851517845863",
            "token0": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
            "token1": "0xdac17f958d2ee523a2206206994597c13d831ec7",
            "token0Name": "Wrapped Ether",
            "token1Name": "Tether USD",
            "chain": "eth",
            "id": "eth_0x11b815efb8f581194ae79006d24e0d814b7697f6"
        },
        {
            "type": "pool",
            "totalValueLockedUSD": "1034818.465034897344750580073025524",
            "volumeUSD": "76261361.0857994869394929891053551",
            "liquidity": "11110143120",
            "token0": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",
            "token1": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
            "token0Name": "Wrapped BTC",
            "token1Name": "USD Coin",
            "chain": "eth",
            "id": "eth_0xcbfb0745b8489973bf7b334d54fdbd573df7ef3c"
        }
    ],
    "links": [
        {
            "source": "eth_0xcbcdf9626bc03e24f779434178a73a0b4bad62ed",
            "target": "eth_0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",
            "type": "belongs_to_pool"
        },
        {
            "source": "eth_0xcbcdf9626bc03e24f779434178a73a0b4bad62ed", 
            "target": "eth_0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
            "type": "belongs_to_pool"
        },
        {
            "source": "eth_0x11b815efb8f581194ae79006d24e0d814b7697f6",
            "target": "eth_0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", 
            "type": "belongs_to_pool"
        },
        {
            "source": "eth_0x11b815efb8f581194ae79006d24e0d814b7697f6",
            "target": "eth_0xdac17f958d2ee523a2206206994597c13d831ec7",
            "type": "belongs_to_pool"
        },
        {
            "source": "eth_0xcbfb0745b8489973bf7b334d54fdbd573df7ef3c",
            "target": "eth_0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",
            "type": "belongs_to_pool"
        },
        {
            "source": "eth_0xcbfb0745b8489973bf7b334d54fdbd573df7ef3c",
            "target": "eth_0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
            "type": "belongs_to_pool"
        }
    ]
}"""

# =========================
# Message Models
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
    debug_info: Optional[Dict] = None

# =========================
# Minimal Router for Testing
# =========================

def _f(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default

def _norm(sym: str) -> str:
    return (sym or "").strip().upper()

class SimpleDiGraph:
    def __init__(self):
        self.adj: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
        self.nodes: Dict[str, Dict[str, Any]] = {}

    def add_node(self, n: str, **attrs):
        if n not in self.nodes:
            self.nodes[n] = {}
        self.nodes[n].update(attrs)
        self.adj.setdefault(n, [])

    def has_node(self, n: str) -> bool:
        return n in self.nodes

    def add_edge(self, u: str, v: str, **attrs):
        self.adj.setdefault(u, [])
        self.adj[u].append((v, attrs))

    def neighbors(self, u: str) -> List[Tuple[str, Dict[str, Any]]]:
        return self.adj.get(u, [])

class UltimateDebugRouter:
    def __init__(self, node_link_graph: Dict[str, Any], cfg: EdgeCostConfig, ctx: Context):
        """
        Ultra-defensive initialization with step-by-step error checking
        """
        self.ctx = ctx
        self.cfg = cfg
        
        # Initialize all attributes first
        self.raw = None
        self.G_nodes = {}
        self.G_adj_undirected = {}
        self.R = SimpleDiGraph()
        self.token_index_by_symbol = {}
        self.hubs = {}
        self.debug_info = {
            "total_nodes": 0,
            "total_edges": 0,
            "token_nodes": [],
            "pool_nodes": [],
            "bridge_edges": [],
            "hub_nodes": {},
            "token_symbols": {},
            "routing_edges": 0,
            "initialization_steps": []
        }
        
        try:
            ctx.logger.info("🟢 STEP 1: Validating input data...")
            self._validate_input(node_link_graph)
            self.debug_info["initialization_steps"].append("✅ Input validation")
            
            ctx.logger.info("🟢 STEP 2: Storing raw data...")
            self.raw = node_link_graph
            self.debug_info["initialization_steps"].append("✅ Raw data stored")
            
            ctx.logger.info("🟢 STEP 3: Loading nodes and links...")
            self._safe_load_node_link()
            self.debug_info["initialization_steps"].append("✅ Node-link loading")
            
            ctx.logger.info("🟢 STEP 4: Indexing nodes...")
            self._safe_index_nodes()
            self.debug_info["initialization_steps"].append("✅ Node indexing")
            
            ctx.logger.info("🟢 STEP 5: Building router...")
            self._safe_build_router()
            self.debug_info["initialization_steps"].append("✅ Router building")
            
            ctx.logger.info("🟢 STEP 6: Final diagnostics...")
            self._safe_log_diagnostics()
            self.debug_info["initialization_steps"].append("✅ Diagnostics")
            
            ctx.logger.info("🎉 ALL STEPS COMPLETED SUCCESSFULLY!")
            
        except Exception as e:
            error_msg = f"Initialization failed at step: {str(e)}"
            ctx.logger.error(f"🔴 {error_msg}")
            ctx.logger.error(f"🔴 Traceback: {traceback.format_exc()}")
            self.debug_info["initialization_error"] = error_msg
            self.debug_info["initialization_traceback"] = traceback.format_exc()
            raise RuntimeError(error_msg) from e

    def _validate_input(self, data):
        """Step 1: Validate input data structure"""
        self.ctx.logger.info("   Validating data type...")
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data)}")
        
        self.ctx.logger.info("   Checking for 'nodes' key...")
        if "nodes" not in data:
            raise ValueError("Missing 'nodes' key in data")
        
        self.ctx.logger.info("   Checking for 'links' key...")
        if "links" not in data:
            raise ValueError("Missing 'links' key in data")
        
        self.ctx.logger.info("   Validating nodes structure...")
        nodes = data["nodes"]
        if not isinstance(nodes, list):
            raise ValueError(f"Expected nodes to be list, got {type(nodes)}")
        
        self.ctx.logger.info("   Validating links structure...")
        links = data["links"]
        if not isinstance(links, list):
            raise ValueError(f"Expected links to be list, got {type(links)}")
        
        self.ctx.logger.info(f"   ✅ Valid structure: {len(nodes)} nodes, {len(links)} links")

    def _safe_load_node_link(self):
        """Step 2: Safely load nodes and links"""
        try:
            nodes = self.raw["nodes"]
            links = self.raw["links"]
            
            self.debug_info["total_nodes"] = len(nodes)
            self.debug_info["total_edges"] = len(links)
            
            # Process nodes
            self.ctx.logger.info(f"   Processing {len(nodes)} nodes...")
            for i, n in enumerate(nodes):
                if not isinstance(n, dict):
                    self.ctx.logger.warning(f"   Skipping non-dict node {i}: {n}")
                    continue
                
                nid = n.get("id") or n.get("name")
                if not nid:
                    self.ctx.logger.warning(f"   Skipping node {i} without id/name: {n}")
                    continue
                
                self.G_nodes[nid] = {k: v for k, v in n.items() if k != "id"}
                self.G_adj_undirected.setdefault(nid, [])
                
                node_type = n.get("type", "unknown")
                if node_type == "token":
                    self.debug_info["token_nodes"].append(nid)
                elif node_type == "pool":
                    self.debug_info["pool_nodes"].append(nid)
            
            self.ctx.logger.info(f"   ✅ Processed {len(self.G_nodes)} nodes")
            
            # Process links
            self.ctx.logger.info(f"   Processing {len(links)} links...")
            links_processed = 0
            for i, e in enumerate(links):
                if not isinstance(e, dict):
                    self.ctx.logger.warning(f"   Skipping non-dict link {i}: {e}")
                    continue
                
                u = e.get("source")
                v = e.get("target")
                
                if not u or not v:
                    self.ctx.logger.warning(f"   Skipping link {i} without source/target: {e}")
                    continue
                
                if u not in self.G_nodes or v not in self.G_nodes:
                    self.ctx.logger.warning(f"   Skipping link {i} with unknown nodes: {u} -> {v}")
                    continue
                
                attrs = {k: v2 for k, v2 in e.items() if k not in ("source", "target")}
                self.G_adj_undirected[u].append((v, attrs))
                self.G_adj_undirected[v].append((u, attrs))
                links_processed += 1
            
            self.ctx.logger.info(f"   ✅ Processed {links_processed} links")
            
        except Exception as e:
            raise RuntimeError(f"Node-link loading failed: {str(e)}") from e

    def _safe_index_nodes(self):
        """Step 3: Safely index nodes"""
        try:
            tokens_indexed = 0
            hubs_found = 0
            
            for nid, data in self.G_nodes.items():
                ntype = data.get("type")
                chain = (data.get("chain") or "").lower()
                
                if ntype == "central_token" and chain:
                    self.hubs[chain] = nid
                    self.debug_info["hub_nodes"][chain] = nid
                    hubs_found += 1
                    self.ctx.logger.info(f"   🎯 Hub: {chain} -> {nid}")
                    
                elif ntype == "token" and chain:
                    symbol = data.get("name") or data.get("symbol")
                    if symbol:
                        normalized_symbol = _norm(symbol)
                        self.token_index_by_symbol[(chain, normalized_symbol)] = nid
                        
                        if chain not in self.debug_info["token_symbols"]:
                            self.debug_info["token_symbols"][chain] = []
                        self.debug_info["token_symbols"][chain].append(symbol)
                        
                        tokens_indexed += 1
                        self.ctx.logger.info(f"   🏷️  Token: {chain}:{symbol} -> {nid}")
            
            self.ctx.logger.info(f"   ✅ Indexed {tokens_indexed} tokens, {hubs_found} hubs")
            
        except Exception as e:
            raise RuntimeError(f"Node indexing failed: {str(e)}") from e

    def _safe_build_router(self):
        """Step 4: Safely build routing graph"""
        try:
            # Add all nodes
            for nid, attrs in self.G_nodes.items():
                self.R.add_node(nid, **attrs)
            
            routing_edges = 0
            
            # Process pools and create swap edges
            valid_pools = 0
            for nid, attrs in self.G_nodes.items():
                if attrs.get("type") != "pool":
                    continue
                
                # Check pool validity
                liq = _f(attrs.get("liquidity"))
                tvl = _f(attrs.get("totalValueLockedUSD"))
                
                if liq < self.cfg.min_liquidity or tvl < self.cfg.min_tvl:
                    self.ctx.logger.info(f"   🚫 Pool {nid} filtered: liq={liq:.0f}, tvl={tvl:.0f}")
                    continue
                
                valid_pools += 1
                
                # Calculate cost
                inv_liq = 1.0 / max(liq, 1.0)
                inv_tvl = 1.0 / max(tvl, 1.0)
                cost = (
                    self.cfg.alpha_liquidity * inv_liq
                    + self.cfg.beta_tvl * inv_tvl
                    + self.cfg.gamma_gas_per_swap
                    + self.cfg.slippage_bias
                )
                
                # Find tokens for this pool
                chain = (attrs.get("chain") or "").lower()
                tokens = []
                
                # Method 1: From belongs_to_pool edges
                for nbr, edata in self.G_adj_undirected.get(nid, []):
                    if edata.get("type") == "belongs_to_pool":
                        if self.G_nodes.get(nbr, {}).get("type") == "token":
                            tokens.append(nbr)
                
                # Method 2: From token0/token1 fields
                if len(tokens) < 2:
                    t0_addr = attrs.get("token0")
                    t1_addr = attrs.get("token1")
                    if t0_addr and t1_addr:
                        t0_id = f"{chain}_{t0_addr}"
                        t1_id = f"{chain}_{t1_addr}"
                        if self.R.has_node(t0_id) and self.R.has_node(t1_id):
                            tokens = [t0_id, t1_id]
                
                # Create swap edges
                if len(tokens) >= 2:
                    t0, t1 = tokens[0], tokens[1]
                    self.R.add_edge(t0, t1, kind="swap", pool=nid, chain=chain, weight=cost)
                    self.R.add_edge(t1, t0, kind="swap", pool=nid, chain=chain, weight=cost)
                    routing_edges += 2
                    self.ctx.logger.info(f"   ✅ Swap: {t0} <-> {t1} (cost: {cost:.6f})")
                else:
                    self.ctx.logger.warning(f"   ⚠️ Pool {nid} has insufficient tokens: {tokens}")
            
            self.debug_info["routing_edges"] = routing_edges
            self.ctx.logger.info(f"   ✅ Created {routing_edges} routing edges from {valid_pools} pools")
            
        except Exception as e:
            raise RuntimeError(f"Router building failed: {str(e)}") from e

    def _safe_log_diagnostics(self):
        """Step 5: Safely log diagnostics"""
        try:
            self.ctx.logger.info("🔍 FINAL DIAGNOSTICS:")
            self.ctx.logger.info(f"   Nodes: {len(self.G_nodes)}")
            self.ctx.logger.info(f"   Tokens: {len(self.debug_info['token_nodes'])}")
            self.ctx.logger.info(f"   Pools: {len(self.debug_info['pool_nodes'])}")
            self.ctx.logger.info(f"   Hubs: {self.debug_info['hub_nodes']}")
            self.ctx.logger.info(f"   Routing edges: {self.debug_info['routing_edges']}")
            
            for chain, symbols in self.debug_info["token_symbols"].items():
                self.ctx.logger.info(f"   {chain} tokens: {symbols}")
                
        except Exception as e:
            raise RuntimeError(f"Diagnostics logging failed: {str(e)}") from e

    def best_paths(self, src_chain: str, src_token: str, dst_chain: str, dst_token: str, 
                   *, top_k: int = 3, max_hops: Optional[int] = None) -> Tuple[List[Dict[str, Any]], Dict]:
        """Simple pathfinding for testing"""
        debug_info = {
            "initialization_steps": self.debug_info["initialization_steps"],
            "graph_stats": self.debug_info
        }
        
        # For now, just return empty to test initialization
        return [], debug_info

# Global variables
_router: Optional[UltimateDebugRouter] = None
_initialization_error: Optional[str] = None
_initialization_traceback: Optional[str] = None

# =========================
# Agent
# =========================

agent = Agent(name="ultimate_debug_router", seed="ultimate_debug_seed_2025")

@agent.on_event("startup")
async def _startup(ctx: Context):
    global _router, _initialization_error, _initialization_traceback
    
    ctx.logger.info("🚀 ULTIMATE DEBUG ROUTER STARTING...")
    
    try:
        ctx.logger.info("🟢 PARSING JSON...")
        graph_json = json.loads(SAMPLE_JSON_DATA)
        ctx.logger.info(f"✅ JSON parsed: {len(graph_json.get('nodes', []))} nodes")
        
        ctx.logger.info("🟢 CREATING ROUTER...")
        _router = UltimateDebugRouter(graph_json, CFG, ctx)
        
        ctx.logger.info("🎉 ROUTER CREATION SUCCESSFUL!")
        
    except json.JSONDecodeError as e:
        _initialization_error = f"JSON parsing failed: {str(e)}"
        _initialization_traceback = traceback.format_exc()
        ctx.logger.error(f"🔴 JSON ERROR: {_initialization_error}")
        
    except Exception as e:
        _initialization_error = str(e)
        _initialization_traceback = traceback.format_exc()
        ctx.logger.error(f"🔴 ROUTER CREATION FAILED: {_initialization_error}")
        ctx.logger.error(f"🔴 FULL TRACEBACK: {_initialization_traceback}")

@agent.on_message(model=RouteQuery, replies=RouteResult)
async def _on_route_query(ctx: Context, sender: str, msg: RouteQuery):
    ctx.logger.info(f"📨 Query: {msg.src_chain}:{msg.src_token} -> {msg.dst_chain}:{msg.dst_token}")
    
    if _router is None:
        error_info = {
            "error": "router_not_initialized",
            "initialization_error": _initialization_error,
            "initialization_traceback": _initialization_traceback
        }
        
        await ctx.send(sender, RouteResult(
            routes=[], 
            note=f"Router failed to initialize. Error: {_initialization_error or 'Unknown error'}",
            debug_info=error_info
        ))
        return

    # Router is initialized, try pathfinding
    try:
        routes, debug_info = _router.best_paths(
            src_chain=msg.src_chain,
            src_token=msg.src_token,
            dst_chain=msg.dst_chain,
            dst_token=msg.dst_token,
            top_k=msg.top_k,
            max_hops=msg.max_hops,
        )
        
        await ctx.send(sender, RouteResult(
            routes=[], 
            note="Router initialized successfully! (Pathfinding not implemented yet)",
            debug_info=debug_info
        ))
        
    except Exception as e:
        await ctx.send(sender, RouteResult(
            routes=[], 
            note=f"Pathfinding error: {e}",
            debug_info={"error": str(e)}
        ))

if __name__ == "__main__":
    agent.run()