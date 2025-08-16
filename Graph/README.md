### **Graph Structure**

1. **Nodes**

   * **Pool Nodes (`type=pool`)**

     * Each liquidity pool (e.g., Uniswap v3 pool) is represented as a node.
     * Attributes:

       * `id` (unique per chain, e.g., `eth_0xPoolAddress`)
       * `totalValueLockedUSD`
       * `volumeUSD`
       * `liquidity`
       * `token0`, `token1` (addresses)
       * `token0Name`, `token1Name`
       * `token0Price`, `token1Price`
       * `chain` (`eth` or `base`)

   * **Token Nodes (`type=token`)**

     * Each underlying ERC-20 token is represented as a node.
     * Attributes:

       * `id` (unique per chain, e.g., `eth_0xTokenAddress`)
       * `name`
       * `chain`

   * **Central Token Nodes (`type=central_token`)**

     * One per chain to act as a hub.
     * Attributes:

       * `id` (e.g., `eth_CENTRAL`, `base_CENTRAL`)
       * `chain`

---

2. **Edges**

   * **Pool ↔ Token (`type=belongs_to_pool`)**

     * Connects a pool to its underlying tokens.
     * Example: `eth_0xPool123 ↔ eth_0xTokenABC`

   * **Token ↔ Central Token (`type=swap_hub`)**

     * Each token connects to the central token node of its chain.
     * This represents that **any token in the chain can be swapped via the hub** (instead of creating edges between every token pair, which would explode combinatorially).

   * **Central Token ↔ Central Token (`type=bridge`)**

     * The central token of Ethereum is connected to the central token of Base.
     * This represents **cross-chain bridging**, enabling token flow between the two networks.

---

### **Graph Topology (Simplified View)**

```
          [eth_CENTRAL] ─────── bridge ─────── [base_CENTRAL]
               │                                  │
        ┌──────┼───────┐                  ┌───────┼───────┐
   [eth_TokenA] ... [eth_TokenZ]     [base_TokenA] ... [base_TokenZ]
        │                                  │
     (belongs_to_pool)                 (belongs_to_pool)
        │                                  │
   [eth_Pool1] ... [eth_PoolN]       [base_Pool1] ... [base_PoolM]
```

---

### ✅ Benefits of This Structure

* **Compact:** Avoids creating millions of token↔token edges by using a hub (`swap_hub`).
* **Cross-Chain Ready:** Central tokens act as anchor points for bridging.
* **Data-Rich:** Pools keep all liquidity/volume/tokens as attributes for filtering & analysis.
* **Extensible:** Can later add more chains by creating more `*_CENTRAL` nodes and linking them with `bridge` edges.
