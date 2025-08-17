import networkx as nx
import json
import re

class MeTTaGraphAnalyzer:
    """
    Analyzes a cross-chain liquidity graph using MeTTa-style symbolic reasoning.
    Enforces that all cross-chain bridges must be routed through USDC.
    """
    def __init__(self, graph: nx.Graph):
        self.graph = graph
        # The specific asset required for bridging
        self.bridge_asset_name = "usd coin"
        self.knowledge_base = self._build_knowledge_base()
        print(f"🧠 Knowledge base built with {len(self.knowledge_base)} facts.")
        print(f"🌉 Bridge asset enforced: {self.bridge_asset_name.upper()}")


    def _build_knowledge_base(self) -> set:
        kb = set()
        for node, data in self.graph.nodes(data=True):
            if data.get('type') == 'token':
                kb.add(f'(token "{data["name"]}" {data["chain"]})')
            elif data.get('type') == 'pool':
                tvl = float(data.get('totalValueLockedUSD', 0))
                volume = float(data.get('volumeUSD', 0))
                kb.add(f'(pool {node} {data["chain"]} "{data["token0Name"]}" "{data["token1Name"]}" {tvl:.2f} {volume:.2f})')
        
        kb.add("(bridge eth base)")
        kb.add("(bridge base eth)")
        return kb
    
    def _parse_fact(self, fact_string: str) -> list:
        return re.findall(r'"[^"]*"|\S+', fact_string.strip("()"))

    def reason(self, query: str) -> dict:
        print(f"\n🔎 Reasoning for query: '{query}'")
        if "swap" in query.lower():
            return self._resolve_swap_intent(query)
        elif "find best pool" in query.lower():
            return self._resolve_best_pool_intent(query)
        else:
            return {"error": "Could not understand the intent."}

    def _resolve_swap_intent(self, query: str) -> dict:
        try:
            parts = query.lower().replace("swap ", "").split(" to ")
            from_part = parts[0].split(" on ")
            to_part = parts[1].split(" on ")
            
            from_token_name = from_part[0].strip()
            from_chain = from_part[1].strip()
            
            to_token_name = to_part[0].strip()
            to_chain = to_part[1].strip()
            
            print(f"   - Intent: SWAP")
            print(f"   - From: {from_token_name.upper()} on {from_chain.upper()}")
            print(f"   - To: {to_token_name.upper()} on {to_chain.upper()}")

            path = self._find_swap_path(from_token_name, from_chain, to_token_name, to_chain)

            if not path:
                return {"error": "No valid swap path found. Either a direct pool is missing or a required bridge path via USDC is unavailable."}

            return {
                "intent": "execute_swap",
                "parameters": {
                    "from_token": from_token_name, "from_chain": from_chain,
                    "to_token": to_token_name, "to_chain": to_chain,
                    "path": path
                }
            }
        except IndexError:
            return {"error": "Invalid swap query format. Use 'swap [TOKEN] on [CHAIN] to [TOKEN] on [CHAIN]'."}

    def _find_intra_chain_path(self, from_token: str, to_token: str, chain: str) -> list:
        """
        Finds a direct, single-step swap path between two tokens on the same chain.
        Returns a list with the swap step if found, otherwise an empty list.
        """
        # Handle the trivial case where the tokens are the same
        if from_token == to_token:
            return [{"action": "none", "chain": chain, "details": "Tokens are the same, no swap needed."}]

        for fact in self.knowledge_base:
            if fact.startswith(f"(pool") and f" {chain} " in fact:
                parts = self._parse_fact(fact)
                token0_in_fact = parts[3].strip('"').lower()
                token1_in_fact = parts[4].strip('"').lower()

                if (from_token == token0_in_fact and to_token == token1_in_fact) or \
                   (from_token == token1_in_fact and to_token == token0_in_fact):
                    return [{"action": "swap", "chain": chain, "pool_id": parts[1], "details": f"Swap {from_token} for {to_token}"}]
        return []

    def _find_swap_path(self, from_token: str, from_chain: str, to_token: str, to_chain: str) -> list:
        """
        Finds a valid swap path. If cross-chain, enforces bridging via USDC.
        """
        if from_chain == to_chain:
            # Simple case: find a path on the same chain
            return self._find_intra_chain_path(from_token, to_token, from_chain)
        else:
            # Cross-chain case: must go through the designated bridge asset
            path = []

            # 1. Find path from source token to USDC on the source chain
            path_to_bridge_asset = self._find_intra_chain_path(from_token, self.bridge_asset_name, from_chain)
            if not path_to_bridge_asset:
                print(f"   - Path failed: No swap path from {from_token.upper()} to {self.bridge_asset_name.upper()} on {from_chain}.")
                return []
            
            # 2. Check if a bridge exists between the chains
            if f"(bridge {from_chain} {to_chain})" not in self.knowledge_base:
                print(f"   - Path failed: No bridge from {from_chain.upper()} to {to_chain.upper()}.")
                return []
            
            # 3. Find path from USDC to destination token on the destination chain
            path_from_bridge_asset = self._find_intra_chain_path(self.bridge_asset_name, to_token, to_chain)
            if not path_from_bridge_asset:
                print(f"   - Path failed: No swap path from {self.bridge_asset_name.upper()} to {to_token.upper()} on {to_chain}.")
                return []

            # If all steps are successful, construct the full path
            path.extend(path_to_bridge_asset)
            path.append({"action": "bridge", "from_chain": from_chain, "to_chain": to_chain, "asset": self.bridge_asset_name, "details": f"Bridge {self.bridge_asset_name} from {from_chain} to {to_chain}"})
            path.extend(path_from_bridge_asset)
            
            # Filter out any "no-op" steps
            return [step for step in path if step.get("action") != "none"]

    def _resolve_best_pool_intent(self, query: str) -> dict:
        # This method remains unchanged
        try:
            parts = query.lower().split(" on ")
            chain = parts[1].split(" by ")[0].strip()
            metric = parts[1].split(" by ")[1].strip()

            print(f"   - Intent: FIND_BEST_POOL")
            print(f"   - On Chain: {chain.upper()}")
            print(f"   - By Metric: {metric.upper()}")

            if metric not in ["volume", "liquidity"]: return {"error": "Metric must be 'volume' or 'liquidity'."}
            
            best_pool = None
            max_metric = -1

            for fact in self.knowledge_base:
                if fact.startswith(f"(pool") and f" {chain} " in fact:
                    p = self._parse_fact(fact)
                    tvl, vol = float(p[5]), float(p[6])
                    current_metric_val = vol if metric == "volume" else tvl
                    
                    if current_metric_val > max_metric:
                        max_metric = current_metric_val
                        best_pool = {
                            "pool_id": p[1], "chain": chain,
                            "tokens": [p[3].strip('"'), p[4].strip('"')],
                            "liquidity_usd": tvl, "volume_usd_24h": vol
                        }
            
            if not best_pool: return {"error": f"No pools found on chain {chain}."}

            return { "intent": "find_best_pool", "parameters": best_pool }
        except IndexError:
            return {"error": "Invalid query format. Use 'find best pool on [CHAIN] by [METRIC]'."}


# --- Example Usage ---
if __name__ == "__main__":
    try:
        with open('cross_chain_graph.json', 'r') as f:
            graph_data = json.load(f)
        G = nx.node_link_graph(graph_data)
        print("✅ Graph loaded successfully.")
    except FileNotFoundError:
        print("❌ Error: cross_chain_graph.json not found. Run the graph generation script first.")
        exit()

    analyzer = MeTTaGraphAnalyzer(G)

    # --- Test Queries ---
    
    # 1. Valid cross-chain swap query that must now route through USDC
    # Assuming pools for (WETH <-> USDC on eth) and (USDC <-> WETH on base) exist.
    query1 = "swap wrapped ether on eth to wrapped ether on base"
    intent1 = analyzer.reason(query1)
    print("✅ Resolved Intent 1 (Cross-Chain via USDC):")
    print(json.dumps(intent1, indent=2))
    
    # 2. Intra-chain swap query (unaffected by the bridge rule)
    query2 = "swap wrapped ether on eth to usd coin on eth"
    intent2 = analyzer.reason(query2)
    print("\n✅ Resolved Intent 2 (Intra-Chain):")
    print(json.dumps(intent2, indent=2))

    # 3. Invalid cross-chain swap (if a path to/from USDC doesn't exist)
    # This will likely fail if a direct "SOME Token" <-> "USDC" pool is missing.
    query3 = "swap some token on eth to wrapped ether on base"
    intent3 = analyzer.reason(query3)
    print("\n✅ Resolved Intent 3 (Invalid Cross-Chain):")
    print(json.dumps(intent3, indent=2))