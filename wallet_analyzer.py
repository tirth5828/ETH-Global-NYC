import asyncio
import os
import requests
from cdp import CdpClient
from openai import OpenAI
from time import sleep

# Set your API keys
os.environ["CDP_API_KEY_ID"] = ""
os.environ["CDP_API_KEY_SECRET"] = ""
# os.environ["OPENAI_API_KEY"] = ""   

client = OpenAI(
    api_key = ""
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


async def get_wallet_balances(wallet_address):

    async with CdpClient() as cdp:
        # Base balances
        base_balances_price = await fetch_balances(cdp, wallet_address, "base")
        sleep(2)

        # Ethereum balances
        eth_balances_price = await fetch_balances(cdp, wallet_address, "ethereum")

        # Merge all balances
        all_balances = {**base_balances_price, **eth_balances_price}

        print("\n📊 Combined balances with prices:\n", all_balances)

        # Pass balances through LLM for classification
        response = client.responses.create(
            model="gpt-4o-mini",
            input=f"""
            Classify the following tokens into three categories: 
            wallet tokens, DeFi tokens, and miscellaneous tokens.
            
            Provide JSON output with keys:
            - wallet_tokens: list of {{'symbol': str, 'balance': float, 'price': float, 'value_usd': float, 'chain': str}}
            - defi_tokens: list of {{'protocol': str, 'pool': str, 'balance': float, 'value_usd': float, 'apy': float, 'chain': str}}
            - miscellaneous_tokens: list of {{'symbol': str, 'balance': float, 'price': float, 'value_usd': float, 'chain': str}}
            
            Tokens:\n{all_balances}
            """,
            temperature=0.3,
        )

        print("\n🤖 Classification Result:\n", response.output_text)



if __name__ == "__main__":
    
    async def main():
        # Example usage:
        example_wallet = "0xf71657318e9b5a5b5173d16327e34e4675ec5d56"
        await get_wallet_balances(example_wallet)

    asyncio.run(main())
