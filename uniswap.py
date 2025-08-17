import time
from web3 import Web3
from eth_account import Account

UNISWAP_ROUTER = {
    "ETH": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
    "BASE": "0xE592427A0AEce92De3Edee1F18E0157C05861564"
}

NONFUNGIBLE_POSITION_MANAGER = {
    "ETH": "0xC36442b4a4522E871399CD717aBDD847Ab11FE88",
    "BASE": "0xC36442b4a4522E871399CD717aBDD847Ab11FE88"
}

ERC20_ABI = [
    {"constant": False, "inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"},
    {"constant": True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
    {"constant": True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}
]

POSITION_MANAGER_ABI = [
    # mint liquidity
    {"inputs":[
        {"components":[
            {"internalType":"address","name":"token0","type":"address"},
            {"internalType":"address","name":"token1","type":"address"},
            {"internalType":"uint24","name":"fee","type":"uint24"},
            {"internalType":"int24","name":"tickLower","type":"int24"},
            {"internalType":"int24","name":"tickUpper","type":"int24"},
            {"internalType":"uint256","name":"amount0Desired","type":"uint256"},
            {"internalType":"uint256","name":"amount1Desired","type":"uint256"},
            {"internalType":"uint256","name":"amount0Min","type":"uint256"},
            {"internalType":"uint256","name":"amount1Min","type":"uint256"},
            {"internalType":"address","name":"recipient","type":"address"},
            {"internalType":"uint256","name":"deadline","type":"uint256"}
        ],"internalType":"struct INonfungiblePositionManager.MintParams","name":"params","type":"tuple"}],
        "name":"mint","outputs":[{"internalType":"uint256","name":"tokenId","type":"uint256"},{"internalType":"uint128","name":"liquidity","type":"uint128"},{"internalType":"uint256","name":"amount0","type":"uint256"},{"internalType":"uint256","name":"amount1","type":"uint256"}],
        "stateMutability":"payable","type":"function"
    },
    # decrease liquidity
    {"inputs":[
        {"components":[
            {"internalType":"uint256","name":"tokenId","type":"uint256"},
            {"internalType":"uint128","name":"liquidity","type":"uint128"},
            {"internalType":"uint256","name":"amount0Min","type":"uint256"},
            {"internalType":"uint256","name":"amount1Min","type":"uint256"},
            {"internalType":"uint256","name":"deadline","type":"uint256"}
        ],"internalType":"struct INonfungiblePositionManager.DecreaseLiquidityParams","name":"params","type":"tuple"}],
        "name":"decreaseLiquidity","outputs":[{"internalType":"uint256","name":"amount0","type":"uint256"},{"internalType":"uint256","name":"amount1","type":"uint256"}],
        "stateMutability":"nonpayable","type":"function"
    },
    # collect fees
    {"inputs":[
        {"components":[
            {"internalType":"uint256","name":"tokenId","type":"uint256"},
            {"internalType":"address","name":"recipient","type":"address"},
            {"internalType":"uint128","name":"amount0Max","type":"uint128"},
            {"internalType":"uint128","name":"amount1Max","type":"uint128"}
        ],"internalType":"struct INonfungiblePositionManager.CollectParams","name":"params","type":"tuple"}],
        "name":"collect","outputs":[{"internalType":"uint256","name":"amount0","type":"uint256"},{"internalType":"uint256","name":"amount1","type":"uint256"}],
        "stateMutability":"nonpayable","type":"function"
    }
]

UNISWAP_ROUTER_ABI = [
    {
        "inputs":[
            {
                "components":[
                    {"internalType":"bytes","name":"path","type":"bytes"},
                    {"internalType":"address","name":"recipient","type":"address"},
                    {"internalType":"uint256","name":"amountIn","type":"uint256"},
                    {"internalType":"uint256","name":"amountOutMinimum","type":"uint256"}
                ],
                "internalType":"struct IV3SwapRouter.ExactInputParams",
                "name":"params",
                "type":"tuple"
            }
        ],
        "name":"exactInput",
        "outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],
        "stateMutability":"payable",
        "type":"function"
    },
    {
        "inputs":[
            {
                "components":[
                    {"internalType":"address","name":"tokenIn","type":"address"},
                    {"internalType":"address","name":"tokenOut","type":"address"},
                    {"internalType":"uint24","name":"fee","type":"uint24"},
                    {"internalType":"address","name":"recipient","type":"address"},
                    {"internalType":"uint256","name":"amountIn","type":"uint256"},
                    {"internalType":"uint256","name":"amountOutMinimum","type":"uint256"},
                    {"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}
                ],
                "internalType":"struct IV3SwapRouter.ExactInputSingleParams",
                "name":"params",
                "type":"tuple"
            }
        ],
        "name":"exactInputSingle",
        "outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],
        "stateMutability":"payable",
        "type":"function"
    },
    {
        "inputs":[
            {
                "components":[
                    {"internalType":"bytes","name":"path","type":"bytes"},
                    {"internalType":"address","name":"recipient","type":"address"},
                    {"internalType":"uint256","name":"amountOut","type":"uint256"},
                    {"internalType":"uint256","name":"amountInMaximum","type":"uint256"}
                ],
                "internalType":"struct IV3SwapRouter.ExactOutputParams",
                "name":"params",
                "type":"tuple"
            }
        ],
        "name":"exactOutput",
        "outputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"}],
        "stateMutability":"payable",
        "type":"function"
    },
    {
        "inputs":[
            {
                "components":[
                    {"internalType":"address","name":"tokenIn","type":"address"},
                    {"internalType":"address","name":"tokenOut","type":"address"},
                    {"internalType":"uint24","name":"fee","type":"uint24"},
                    {"internalType":"address","name":"recipient","type":"address"},
                    {"internalType":"uint256","name":"amountOut","type":"uint256"},
                    {"internalType":"uint256","name":"amountInMaximum","type":"uint256"},
                    {"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}
                ],
                "internalType":"struct IV3SwapRouter.ExactOutputSingleParams",
                "name":"params",
                "type":"tuple"
            }
        ],
        "name":"exactOutputSingle",
        "outputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"}],
        "stateMutability":"payable",
        "type":"function"
    },
    {
        "inputs":[{"internalType":"bytes[]","name":"data","type":"bytes[]"}],
        "name":"multicall",
        "outputs":[{"internalType":"bytes[]","name":"results","type":"bytes[]"}],
        "stateMutability":"payable",
        "type":"function"
    },
    {
        "inputs":[{"internalType":"bytes[]","name":"data","type":"bytes[]"},{"internalType":"uint256","name":"deadline","type":"uint256"}],
        "name":"multicall",
        "outputs":[{"internalType":"bytes[]","name":"results","type":"bytes[]"}],
        "stateMutability":"payable",
        "type":"function"
    },
    {
        "inputs":[{"internalType":"uint256","name":"amountMinimum","type":"uint256"}],
        "name":"unwrapWETH9",
        "outputs":[],
        "stateMutability":"payable",
        "type":"function"
    },
    {
        "inputs":[{"internalType":"uint256","name":"amountMinimum","type":"uint256"},{"internalType":"address","name":"recipient","type":"address"}],
        "name":"unwrapWETH9",
        "outputs":[],
        "stateMutability":"payable",
        "type":"function"
    },
    {
        "inputs":[{"internalType":"uint256","name":"amountMinimum","type":"uint256"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"feeBips","type":"uint256"},{"internalType":"address","name":"feeRecipient","type":"address"}],
        "name":"unwrapWETH9WithFee",
        "outputs":[],
        "stateMutability":"payable",
        "type":"function"
    },
    {
        "inputs":[{"internalType":"uint256","name":"amountMinimum","type":"uint256"},{"internalType":"uint256","name":"feeBips","type":"uint256"},{"internalType":"address","name":"feeRecipient","type":"address"}],
        "name":"unwrapWETH9WithFee",
        "outputs":[],
        "stateMutability":"payable",
        "type":"function"
    },
    {
        "inputs":[{"internalType":"uint256","name":"value","type":"uint256"}],
        "name":"wrapETH",
        "outputs":[],
        "stateMutability":"payable",
        "type":"function"
    },
    {
        "inputs":[{"internalType":"uint256","name":"amountMinimum","type":"uint256"},{"internalType":"address","name":"recipient","type":"address"}],
        "name":"refundETH",
        "outputs":[],
        "stateMutability":"payable",
        "type":"function"
    },
    {
        "inputs":[
            {"internalType":"address","name":"token","type":"address"},
            {"internalType":"uint256","name":"value","type":"uint256"}
        ],
        "name":"selfPermit",
        "outputs":[],
        "stateMutability":"payable",
        "type":"function"
    },
    {
        "inputs":[
            {"internalType":"address","name":"token","type":"address"},
            {"internalType":"uint256","name":"nonce","type":"uint256"},
            {"internalType":"uint256","name":"expiry","type":"uint256"},
            {"internalType":"uint8","name":"v","type":"uint8"},
            {"internalType":"bytes32","name":"r","type":"bytes32"},
            {"internalType":"bytes32","name":"s","type":"bytes32"}
        ],
        "name":"selfPermitAllowed",
        "outputs":[],
        "stateMutability":"payable",
        "type":"function"
    },
    {
        "inputs":[
            {"internalType":"address","name":"token","type":"address"},
            {"internalType":"uint256","name":"nonce","type":"uint256"},
            {"internalType":"uint256","name":"expiry","type":"uint256"},
            {"internalType":"uint8","name":"v","type":"uint8"},
            {"internalType":"bytes32","name":"r","type":"bytes32"},
            {"internalType":"bytes32","name":"s","type":"bytes32"}
        ],
        "name":"selfPermitAllowedIfNecessary",
        "outputs":[],
        "stateMutability":"payable",
        "type":"function"
    },
    {
        "inputs":[
            {"internalType":"address","name":"token","type":"address"},
            {"internalType":"uint256","name":"value","type":"uint256"},
            {"internalType":"uint256","name":"deadline","type":"uint256"},
            {"internalType":"uint8","name":"v","type":"uint8"},
            {"internalType":"bytes32","name":"r","type":"bytes32"},
            {"internalType":"bytes32","name":"s","type":"bytes32"}
        ],
        "name":"selfPermitIfNecessary",
        "outputs":[],
        "stateMutability":"payable",
        "type":"function"
    }
]


class UniswapV3Helper:
    def __init__(self, private_key: str, rpc_urls: dict):
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        self.w3 = {chain: Web3(Web3.HTTPProvider(url)) for chain, url in rpc_urls.items()}
        self.router = {chain: self.w3[chain].eth.contract(address=UNISWAP_ROUTER[chain], abi=UNISWAP_ROUTER_ABI) for chain in rpc_urls}
        self.position_manager = {chain: self.w3[chain].eth.contract(address=NONFUNGIBLE_POSITION_MANAGER[chain], abi=POSITION_MANAGER_ABI) for chain in rpc_urls}

    def _build_and_send_tx(self, chain, tx):
        w3 = self.w3[chain]

        # Estimate gas if not provided
        if "gas" not in tx:
            tx["gas"] = tx.get("gas", w3.eth.estimate_gas(tx))

        # Estimate max fee
        fee_data = w3.eth.fee_history(1, "latest", reward_percentiles=[50])
        max_priority_fee = w3.to_wei(2, "gwei")
        base_fee = fee_data["baseFeePerGas"][-1] if fee_data["baseFeePerGas"] else w3.to_wei(1, "gwei")
        max_fee = base_fee + max_priority_fee
        tx.setdefault("maxFeePerGas", max_fee)
        tx.setdefault("maxPriorityFeePerGas", max_priority_fee)

        # Check balance
        estimated_cost = tx["gas"] * tx["maxFeePerGas"]
        balance = w3.eth.get_balance(self.address)
        if balance < estimated_cost:
            raise Exception(f"Insufficient ETH for gas. Balance: {balance}, Estimated cost: {estimated_cost}")

        signed = self.account.sign_transaction(tx)
        return w3.eth.send_raw_transaction(signed.raw_transaction).hex()

    def approve_token(self, chain: str, token_address: str, amount: int):
        token = self.w3[chain].eth.contract(address=token_address, abi=ERC20_ABI)
        tx = token.functions.approve(NONFUNGIBLE_POSITION_MANAGER[chain], amount).build_transaction({
            "from": self.address,
            "nonce": self.w3[chain].eth.get_transaction_count(self.address)
        })
        return self._build_and_send_tx(chain, tx)

    def add_liquidity(self, chain: str, token0: str, token1: str, fee: int, tick_lower: int, tick_upper: int, amount0: int, amount1: int):
        deadline = int(time.time()) + 300

        w3 = self.w3[chain]
    
        params = (
            Web3.to_checksum_address(token0),
            Web3.to_checksum_address(token1),
            fee,
            tick_lower,
            tick_upper,
            int(amount0),          # amount0Desired
            int(amount1),          # amount1Desired
            0,                # amount0Min
            0,                # amount1Min
            self.address,     # recipient
            int(time.time()) + 600  # deadline (10 min)
        )

        contract = self.position_manager[chain].functions.mint(params)


        # ⛽ estimate gas safely
        estimated_gas = contract.estimate_gas({"from": self.address})
        max_fee = self.w3[chain].eth.max_priority_fee + self.w3[chain].eth.gas_price
        priority_fee = self.w3[chain].eth.max_priority_fee

        tx = self.position_manager[chain].functions.mint(params).build_transaction({
            "from": self.address,
            "nonce": w3.eth.get_transaction_count(self.address),
            "gas": estimated_gas,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": priority_fee
        })

        return self._build_and_send_tx(chain, tx)

    def remove_liquidity(self, chain: str, token_id: int, liquidity: int):
        deadline = int(time.time()) + 300
        params = {
            "tokenId": token_id,
            "liquidity": liquidity,
            "amount0Min": 0,
            "amount1Min": 0,
            "deadline": deadline
        }
        tx = self.position_manager[chain].functions.decreaseLiquidity(params).build_transaction({
            "from": self.address,
            "nonce": self.w3[chain].eth.get_transaction_count(self.address)
        })
        return self._build_and_send_tx(chain, tx)

    def collect_fees(self, chain: str, token_id: int):
        params = {
            "tokenId": token_id,
            "recipient": self.address,
            "amount0Max": 2**128 - 1,
            "amount1Max": 2**128 - 1
        }
        tx = self.position_manager[chain].functions.collect(params).build_transaction({
            "from": self.address,
            "nonce": self.w3[chain].eth.get_transaction_count(self.address)
        })
        return self._build_and_send_tx(chain, tx)

    def swap_exact_input_single(self, chain: str, token_in: str, token_out: str, fee: int, amount_in: int, amount_out_min: int, recipient: str):
        w3 = self.w3[chain]
        router = self.router[chain]
        deadline = int(time.time()) + 300
        tx = router.functions.exactInputSingle(
            token_in, token_out, fee, recipient, deadline, amount_in, amount_out_min, 0
        ).build_transaction({
            "from": self.address,
            "nonce": w3.eth.get_transaction_count(self.address)
        })
        return self._build_and_send_tx(chain, tx)
