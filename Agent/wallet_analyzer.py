import asyncio
import os
import requests
from cdp import CdpClient
from openai import OpenAI
from time import sleep

# Set your API keys
os.environ["CDP_API_KEY_ID"] = "bd69e334-6557-4eeb-938f-66fa9048b413"
os.environ["CDP_API_KEY_SECRET"] = "60+8NEZplaBKdzaOMDQ8GoEXzc+zd5m8Gd3IVAnJ+2ODqLK+GMSqxsEROiSmSbxSWK3ihIvC0bEdI/7RgLpY7g=="
os.environ["OPENAI_API_KEY"] = "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"   # <-- replace with your key

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"] 
)


def get_token_price(token_address, chain):
    token_address_string = ",".join(token_address) if isinstance(token_address, list) else token_address
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address_string}"
    headers = {"Accept": "application/json"}

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    pairs = response.json().get("pairs", [])


    return {
        pair["baseToken"]["address"]: float(pair.get("priceUsd", 0.0))
        for pair in pairs
        if "priceUsd" in pair
    }


async def fetch_balances(cdp, address, chain):
    balances = await cdp.evm.list_token_balances(address, chain, page_size=100)
    balances_price = {}

    # Collect basic balance info
    for balance in balances.balances:
        balances_price[balance.token.contract_address] = {
            "symbol": balance.token.symbol,
            "balance": float(balance.amount.amount),
            "chain": chain,
        }

    # Batch fetch prices (10 at a time)
    all_balances_price = {}
    for i in range(0, len(balances.balances), 10):
        batch = balances.balances[i : i + 10]
        addresses = [balance.token.contract_address for balance in batch]
        batch_prices = get_token_price(addresses, chain)
        all_balances_price.update(batch_prices)

    # Merge prices into balances
    for balance in balances.balances:
        addr = balance.token.contract_address
        price = all_balances_price.get(addr, 0.0)
        balances_price[addr]["price"] = price
        balances_price[addr]["value_usd"] = balances_price[addr]["balance"] * price

    return balances_price



def categorize_tokens(tokens):
    wallet_tokens = []
    defi_tokens = []
    miscellaneous_tokens = []

    for t, data in tokens.items():
        name = data["symbol"].lower()
        symbol = data["symbol"].lower()

        # Heuristic rules for DeFi/farm/airdrop tokens
        if (
            "moo" in name
            or "farm" in name
            or "stake" in name
            or "lp" in symbol
            or "stk" in symbol
            or "moo" in symbol
            or "cake" in symbol 
            or "mw" in symbol
        ):
            data['protocol'] = "DeFi"
            defi_tokens.append(data)
        elif (
             "airdrop" in name
            or "reward" in name
        ):
            miscellaneous_tokens.append(data)
        else:
            wallet_tokens.append(data)

    return wallet_tokens, defi_tokens, miscellaneous_tokens




async def get_wallet_balances(wallet_address):

    async with CdpClient() as cdp:
        # Base balances
        base_balances_price = await fetch_balances(cdp, wallet_address, "base")

        # Ethereum balances
        eth_balances_price = await fetch_balances(cdp, wallet_address, "ethereum")

        # Merge all balances
        all_balances = {**base_balances_price, **eth_balances_price}


        wallet_tokens, defi_tokens, miscellaneous_tokens = categorize_tokens(all_balances)

        classified_tokens = {
            "wallet_tokens": wallet_tokens,
            "defi_tokens": defi_tokens,
            "miscellaneous_tokens": miscellaneous_tokens
        }

        return classified_tokens



if __name__ == "__main__":
    
    async def main():
        # Example usage:
        example_wallet = "0xf71657318e9b5a5b5173d16327e34e4675ec5d56"
        await get_wallet_balances(example_wallet)

    asyncio.run(main())