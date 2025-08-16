import requests
import networkx as nx
import json

# Replace with your actual API keys
API_KEY = '29f73f54c315b37b41ba48a315dd1234'

SUBGRAPHS = {
    "eth": f"https://gateway.thegraph.com/api/{API_KEY}/subgraphs/id/5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV",
    "base": f"https://gateway.thegraph.com/api/{API_KEY}/subgraphs/id/HMuAwufqZ1YCRmzL2SfHTVkzZovC9VL2UAKhjvRqKiR1"
}

QUERY_TEMPLATE = """
{
  
  pools(first: 100, skip: SKIP, where: { liquidity_gt: 10000000, volumeUSD_gt: 5000000 }) {
    id
    totalValueLockedUSD
    volumeUSD
    liquidity
    token0 { name id }
    token0Price
    token1 { name id }
    token1Price
  }


}
"""

G = nx.Graph()

def fetch_data(url, skip=0):
    """Fetch paginated data from a subgraph"""
    query = QUERY_TEMPLATE.replace("SKIP", str(skip))
    response = requests.post(url, json={'query': query})
    response.raise_for_status()
    return response.json()

def add_chain_data(chain_name, url):
    """Fetch all pools from a chain and add them to the graph"""
    skip = 0
    central_token_id = f"{chain_name}_CENTRAL"
    G.add_node(central_token_id, type='central_token', chain=chain_name)

    while True:
        data = fetch_data(url, skip)
        pools = data['data']['pools']

        print(f"Fetched {len(pools)} pools from {chain_name} (skip={skip})")
        

        if not pools:
            break

        for pool in pools:
            pool_id = f"{chain_name}_{pool['id']}"
            # Add pool node
            G.add_node(pool_id,
                       type='pool',
                       totalValueLockedUSD=pool['totalValueLockedUSD'],
                       volumeUSD=pool['volumeUSD'],
                       liquidity=pool['liquidity'],
                       token0=pool['token0']['id'],
                       token1=pool['token1']['id'],
                       token0Name=pool['token0']['name'],
                       token1Name=pool['token1']['name'],
                       token0Price=pool['token0Price'],
                       token1Price=pool['token1Price'],
                       chain=chain_name)
            
            # Add token nodes and connect to pool
            for token in [pool['token0'], pool['token1']]:
                token_id = f"{chain_name}_{token['id']}"
                if not G.has_node(token_id):
                    G.add_node(token_id, type='token', name=token['name'], chain=chain_name)
                # Connect token to pool
                G.add_edge(pool_id, token_id, type='belongs_to_pool')
                # Connect token to central token
                G.add_edge(token_id, central_token_id, type='swap_hub')

        skip += len(pools)

    return central_token_id

def main():
    # Add data for each chain
    central_tokens = {}
    for chain, url in SUBGRAPHS.items():
        central_tokens[chain] = add_chain_data(chain, url)

    # Connect central tokens across chains with a "bridge" edge
    G.add_edge(central_tokens['eth'], central_tokens['base'], type='bridge')

    # Save the final graph
    with open('cross_chain_graph.json', 'w') as f:
        json.dump(nx.node_link_data(G), f, indent=2)

if __name__ == "__main__":
    main()
