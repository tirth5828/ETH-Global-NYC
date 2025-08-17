import json
import networkx as nx

def load_graph(filename='cross_chain_graph.json'):
    """
    Loads the graph data from a JSON file.

    Args:
        filename (str): The name of the JSON file containing the graph data.

    Returns:
        networkx.Graph: The loaded graph object, or None if the file is not found.
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        return nx.node_link_graph(data)
    except FileNotFoundError:
        print(f"Error: The file '{filename}' was not found. Please generate it first.")
        return None

def find_path(graph, start_token_name, end_token_name, chain=None):
    """
    Finds the shortest path between two tokens in the graph.

    Args:
        graph (networkx.Graph): The graph to search within.
        start_token_name (str): The name (symbol) of the starting token.
        end_token_name (str): The name (symbol) of the ending token.
        chain (str, optional): The specific chain ('eth' or 'base') to search within. 
                               If None, searches across both chains.

    Returns:
        list: A list of nodes representing the shortest path, or None if no path is found.
    """
    start_node = None
    end_node = None

    # Find the node IDs for the given token names
    for node, data in graph.nodes(data=True):
        if data.get('type') == 'token':
            if data.get('name', '').lower() == start_token_name.lower():
                if chain is None or data.get('chain') == chain:
                    start_node = node
            if data.get('name', '').lower() == end_token_name.lower():
                if chain is None or data.get('chain') == chain:
                    end_node = node
    
    if not start_node:
        print(f"Start token '{start_token_name}' not found.")
        return None
    if not end_node:
        print(f"End token '{end_token_name}' not found.")
        return None

    try:
        path = nx.shortest_path(graph, source=start_node, target=end_node)

        for node in path:
            # change central token to bridge and remove the next central token
            if graph.nodes[node].get('type') == 'central_token':
                graph.nodes[node]['type'] = 'bridge'
                next_node = path[path.index(node) + 1] if path.index(node) + 1 < len(path) else None
                if next_node and graph.nodes[next_node].get('type') == 'central_token':
                    graph.nodes[next_node]['type'] = 'removed'

        # Provide a more readable output
        readable_path = []
        for node_id in path:
            node_data = graph.nodes[node_id]
            node_type = node_data.get('type')
            if node_type == 'token':
                readable_path.append(f"Token: {node_data.get('name')} (Chain: {node_data.get('chain')})")
            elif node_type == 'pool':
                 readable_path.append(f"Pool: {node_data.get('token0Name')}/{node_data.get('token1Name')} (Chain: {node_data.get('chain')})")
            elif node_type == 'central_token':
                readable_path.append(f"Hub: {node_data.get('chain').upper()} Central Hub")
            elif node_data.get('type') == 'bridge':
                readable_path.append("First swap to USDC then Bridge through CCTP using USDC then swap to the next desired token")

        return readable_path
    except nx.NetworkXNoPath:
        print(f"No path found between '{start_token_name}' and '{end_token_name}'.")
        return None

def find_pools(graph, min_liquidity=0, min_volume=0, has_token=None, chain=None):
    """
    Finds pools that match specified criteria.

    Args:
        graph (networkx.Graph): The graph to search within.
        min_liquidity (float): Minimum total value locked (USD).
        min_volume (float): Minimum 24-hour volume (USD).
        has_token (str, optional): A token symbol that must be in the pool.
        chain (str, optional): The specific chain ('eth' or 'base') to search.

    Returns:
        list: A list of dictionaries, where each dictionary represents a matching pool.
    """

    print("Searching for pools...")

    print(f"Minimum Liquidity: ${min_liquidity:,.2f}")
    print(f"Minimum Volume: ${min_volume:,.2f}")
    if has_token:
        print(f"Has Token: {has_token}")
    if chain:
        print(f"Chain: {chain}")
        chain = chain.lower()

    matching_pools = []
    for node, data in graph.nodes(data=True):
        if data.get('type') == 'pool':
            # Chain filter
            if chain and data.get('chain') != chain:
                continue

            # Liquidity and Volume filters
            tvl = float(data.get('totalValueLockedUSD', 0))
            volume = float(data.get('volumeUSD', 0))
            
            if tvl >= min_liquidity and volume >= min_volume:
                # Token filter
                if has_token:
                    token0_name = data.get('token0Name', '').lower()
                    token1_name = data.get('token1Name', '').lower()
                    if has_token.lower() in [token0_name, token1_name]:
                        matching_pools.append(data)
                else:
                    matching_pools.append(data)
                    
    return matching_pools

if __name__ == '__main__':
    # Load the graph from the file
    G = load_graph()

    if G:
        print("Graph loaded successfully.")
        
        # --- Example Usage for Pathfinder ---
        print("\n---  Pathfinder Tool ---")
        # Example 1: Find a path on the same chain
        path1 = find_path(G, "Wrapped Ether", "USD Coin")
        if path1:
            print("\nPath found between WETH and USDC:")
            print(" -> ".join(path1))

        # Example 2: Find a cross-chain path
        # Note: This depends on the tokens existing on both chains in your graph data
        path2 = find_path(G, "Wrapped Ether", "USD Coin", chain='base')
        if path2:
            print("\nPath found between WETH and USDC on Base:")
            print(" -> ".join(path2))

        # --- Example Usage for Pool Finder ---
        print("\n--- Pool Finder Tool ---")
        # Example 1: Find high-liquidity pools on Ethereum
        high_liquidity_eth_pools = find_pools(G, min_liquidity=50000000, chain='eth')
        print(f"\nFound {len(high_liquidity_eth_pools)} pools on Ethereum with >$50M liquidity.")
        for pool in high_liquidity_eth_pools[:3]: # Print first 3
            print(f"  - {pool['token0Name']}/{pool['token1Name']}, TVL: ${float(pool['totalValueLockedUSD']):,.2f}")

        # Example 2: Find all pools on Base containing the token "WETH"
        weth_base_pools = find_pools(G, has_token="Wrapped Ether", chain='base')
        print(f"\nFound {len(weth_base_pools)} pools on Base containing WETH.")
        for pool in weth_base_pools[:3]: # Print first 3
            print(f"  - {pool['token0Name']}/{pool['token1Name']}, Volume: ${float(pool['volumeUSD']):,.2f}")

