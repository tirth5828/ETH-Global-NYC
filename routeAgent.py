"""
Ultimate Debug Router - Lazy + Stateless (no globals, no startup race)
"""

import json
import traceback
from dataclasses import dataclass
from functools import lru_cache
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
        "type": "pool",
        "totalValueLockedUSD": "1934395.533646959389339055640759194",
        "volumeUSD": "123021744.1058764026794343143017229",
        "liquidity": "19512670432495431123490",
        "token0": "0x5afe3855358e112b5647b952709e6165e1c1eeee",
        "token1": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        "token0Name": "Safe Token",
        "token1Name": "Wrapped Ether",
        "token0Price": "10369.12531861313683969263416711182",
        "token1Price": "0.00009644014989431618626275291454531651",
        "chain": "eth",
        "id": "eth_0x000ba527862e5b82cff0f7c66b646af023274aa1"
      },
      {
        "type": "token",
        "name": "Safe Token",
        "chain": "eth",
        "id": "eth_0x5afe3855358e112b5647b952709e6165e1c1eeee"
      },
      {
        "type": "token",
        "name": "Wrapped Ether",
        "chain": "eth",
        "id": "eth_0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
      },
      {
        "type": "pool",
        "totalValueLockedUSD": "1009342.889083899346127260973412077",
        "volumeUSD": "53224786.582363",
        "liquidity": "1048342005588196546",
        "token0": "0x0f81001ef0a83ecce5ccebf63eb302c70a39a654",
        "token1": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        "token0Name": "Dolomite",
        "token1Name": "USD Coin",
        "token0Price": "4.868187814095274104822074329304139",
        "token1Price": "0.2054152465327273928938413570301803",
        "chain": "eth",
        "id": "eth_0x003896387666c5c11458eeb3f927b72a11b19783"
      },
      {
        "type": "token",
        "name": "Dolomite",
        "chain": "eth",
        "id": "eth_0x0f81001ef0a83ecce5ccebf63eb302c70a39a654"
      },
      {
        "type": "token",
        "name": "USD Coin",
        "chain": "eth",
        "id": "eth_0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
      },
      {
        "type": "pool",
        "totalValueLockedUSD": "190471.185913",
        "volumeUSD": "97825752.49077033529963891603516567",
        "liquidity": "65049166137103870513",
        "token0": "0x35d8949372d46b7a3d5a56006ae77b215fc69bc0",
        "token1": "0xdac17f958d2ee523a2206206994597c13d831ec7",
        "token0Name": "USD0 Liquid Bond",
        "token1Name": "Tether USD",
        "token0Price": "1.083482588769305361862822935010395",
        "token1Price": "0.9229497643666515456201368801115485",
        "chain": "eth",
        "id": "eth_0x00cc0523b7a2b97f1d52bea1b7a0c50027e0a706"
      },
      {
        "type": "token",
        "name": "USD0 Liquid Bond",
        "chain": "eth",
        "id": "eth_0x35d8949372d46b7a3d5a56006ae77b215fc69bc0"
      },
      {
        "type": "token",
        "name": "Tether USD",
        "chain": "eth",
        "id": "eth_0xdac17f958d2ee523a2206206994597c13d831ec7"
      },
      {
        "type": "pool",
        "totalValueLockedUSD": "136342.576672",
        "volumeUSD": "535338525.7874007145920522387135823",
        "liquidity": "1844954839259335068",
        "token0": "0x4fabb145d64652a948d72533023f6e7a623c7c53",
        "token1": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        "token0Name": "Binance USD",
        "token1Name": "USD Coin",
        "token0Price": "1.000417104324802691905373560679575",
        "token1Price": "0.9995830695786791828159394226992678",
        "chain": "eth",
        "id": "eth_0x00cef0386ed94d738c8f8a74e8bfd0376926d24c"
      },
      {
        "type": "token",
        "name": "Binance USD",
        "chain": "eth",
        "id": "eth_0x4fabb145d64652a948d72533023f6e7a623c7c53"
      },
      {
        "type": "pool",
        "totalValueLockedUSD": "3928.721416187039112039924450467326",
        "volumeUSD": "7692797.024233115815161045944194435",
        "liquidity": "108694061862",
        "token0": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",
        "token1": "0xa469b7ee9ee773642b3e93e842e5d9b5baa10067",
        "token0Name": "Wrapped BTC",
        "token1Name": "USDz",
        "token0Price": "0.000007356569704567297083058739504211001",
        "token1Price": "135932.9198470251660486577759958703",
        "chain": "eth",
        "id": "eth_0x00da578acb3381f48f187374cda78d6824676f27"
      },
      {
        "type": "token",
        "name": "Wrapped BTC",
        "chain": "eth",
        "id": "eth_0x2260fac5e5542a773aa44fbcfedf7c193bc2c599"
      },
      {
        "type": "token",
        "name": "USDz",
        "chain": "eth",
        "id": "eth_0xa469b7ee9ee773642b3e93e842e5d9b5baa10067"
      },
      {
        "type": "pool",
        "totalValueLockedUSD": "18402511.81899301908347077067906001",
        "volumeUSD": "29828238.10825640096855669195478399",
        "liquidity": "7746865271654",
        "token0": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        "token1": "0xe0f63a424a4439cbe457d80e4f4b51ad25b2c56c",
        "token0Name": "Wrapped Ether",
        "token1Name": "SPX6900",
        "token0Price": "0.0003333413589818874133880784888116863",
        "token1Price": "2999.927770902069345616282687641596",
        "chain": "eth",
        "id": "eth_0x00ed26e794b949e18b142f9108429b74ce08ac99"
      },
      {
        "type": "token",
        "name": "SPX6900",
        "chain": "eth",
        "id": "eth_0xe0f63a424a4439cbe457d80e4f4b51ad25b2c56c"
      },
      {
        "type": "pool",
        "totalValueLockedUSD": "116628.119371790808651626668498067",
        "volumeUSD": "14948994.95335833715527805936567591",
        "liquidity": "11765132931858718023",
        "token0": "0x15b543e986b8c34074dfc9901136d9355a537e7e",
        "token1": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        "token0Name": "Student Coin",
        "token1Name": "Wrapped Ether",
        "token0Price": "2559168.039861718808933809098677314",
        "token1Price": "0.0000003907519883118084150328945078942769",
        "chain": "eth",
        "id": "eth_0x00f59b15dc1fe2e16cde0678d2164fd5ff10e424"
      },
      {
        "type": "token",
        "name": "Student Coin",
        "chain": "eth",
        "id": "eth_0x15b543e986b8c34074dfc9901136d9355a537e7e"
      },
      {
        "type": "pool",
        "totalValueLockedUSD": "81144.45075742265601308248623178946",
        "volumeUSD": "8325470.11327094854854635557647941",
        "liquidity": "374467427117118765",
        "token0": "0xa93d86af16fe83f064e3c0e2f3d129f7b7b002b0",
        "token1": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        "token0Name": "COCORO",
        "token1Name": "Wrapped Ether",
        "token0Price": "186892537.2984642905059076060848208",
        "token1Price": "0.000000005350668434679211090762356258737675",
        "chain": "eth",
        "id": "eth_0x0105b9b95f63e54650f70125402588ad329d5b00"
      }
      ],
    "links": [
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x5afe3855358e112b5647b952709e6165e1c1eeee"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x0f81001ef0a83ecce5ccebf63eb302c70a39a654"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x35d8949372d46b7a3d5a56006ae77b215fc69bc0"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xdac17f958d2ee523a2206206994597c13d831ec7"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x4fabb145d64652a948d72533023f6e7a623c7c53"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x2260fac5e5542a773aa44fbcfedf7c193bc2c599"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa469b7ee9ee773642b3e93e842e5d9b5baa10067"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xe0f63a424a4439cbe457d80e4f4b51ad25b2c56c"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x15b543e986b8c34074dfc9901136d9355a537e7e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa93d86af16fe83f064e3c0e2f3d129f7b7b002b0"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x926ff6584b5905cc793cfb19bfc0ad6443671f47"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x491604c0fdf08347dd1fa4ee062a822a5dd06b5d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x102c776ddb30c754ded4fdcc77a19230a60d4e4f"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x36e66fbbce51e4cd5bd3c62b637eb411b18949d4"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc011a73ee8576fb46f5e1c5751ca3b9fe0af2a6f"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xdccf3968b667e515c9fc952aa6bf834eb9d8476c"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb0b195aefa3650a6908f15cdac7d92f8a5791b0b"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8a854288a5976036a725879164ca3e91d30c6a1b"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xfa14fa6958401314851a17d6c5360ca29f74b57b"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x054c9d4c6f4ea4e14391addd1812106c97d05690"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6715515f5aa98e8bd3624922e1ba91e6f5fc4402"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x9e78b8274e1d6a76a0dbbf90418894df27cbceb5"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x04c154b66cb340f3ae24111cc767e0184ed00cc6"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x2c5bc2ba3614fd27fcc7022ea71d9172e2632c16"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xaf5191b0de278c7286d6c7cc6ab6bb8a73ba2cd6"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb3e41d6e0ea14b43bc5de3c314a408af171b03dd"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x774eaf7a53471628768dc679da945847d34b9a55"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x86ed939b500e121c0c5f493f399084db596dad20"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xd5f7838f5c461feff7fe49ea5ebaf7728bb0adfa"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x0bc529c00c6401aef6d220be8c6ea1667f6ad93e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xf1ca9cb74685755965c7458528a36934df52a3ef"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x656c00e1bcd96f256f224ad9112ff426ef053733"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xcdb37a4fbc2da5b78aa4e41a432792f9533e85cc"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xbcd4d5ac29e06e4973a1ddcd782cd035d04bc0b7"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x519c1001d550c0a1dae7d1fc220f7d14c2a521bb"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x243cacb4d5ff6814ad668c3e225246efa886ad5a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc56c7a0eaa804f854b536a5f3d5f49d2ec4b12b8"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x0d438f3b5175bebc262bf23753c1e53d03432bde"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa1290d69c65a6fe4df752f95823fae25cb99e5a7"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x9e46a38f5daabe8683e10793b06749eef7d733d1"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x111111111117dc0aa78b770fa6a738034120c302"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x1f9840a85d5af5bf1d1762f925bdaddc4201f984"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x72e364f2abdc788b7e918bc238b21f109cd634d7"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xde30da39c46104798bb5aa3fe8b9e0e1f348163f"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xe60e9bd04ccc0a394f1fdf29874e35a773cb07f4"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xfe0c30065b384f05761f15d0cc899d4f9f9cc0eb"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xd7efb00d12c2c13131fd319336fdf952525da2af"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xd2d8d78087d0e43bc4804b6f946674b2ee406b80"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x9abc68b33961268a3ea4116214d7039226de01e1"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xd533a949740bb3306d119cc777fa900ba034cd52"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xbbc2ae13b23d715c30720f079fcd9b4a74093505"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x744d70fdbe2ba4cf95131626614a1763df805b9e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xcb1592591996765ec0efc1f92599a19767ee5ffa"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x57e114b691db790c35207b2e685d4a43181e6061"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x0ab87046fbb341d058f17cbc4c1133f25a20a52f"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xaaa9214f675316182eaa21c85f0ca99160cc3aaa"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x340d2bde5eb28c1eed91b2f790723e3b160613b7"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa58a4f5c4bb043d2cc1e170613b74e767c94189b"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7b123f53421b1bf8533339bfbdc7c98aa94163db"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc18360217d8f7ab5e7c516566761ea12ce7f9d72"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xd47bdf574b4f76210ed503e0efe81b58aa061f3d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xe41724423566304437dc17dbb0de27ea8ec44cf6"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x9d65ff81a3c488d585bbfb0bfe3c7707c7917f54"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6b0b3a982b4634ac68dd83a4dbf02311ce324181"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xd9016a907dc0ecfa3ca425ab20b6b785b42f2373"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x1c9922314ed1415c95b9fd453c3818fd41867d0b"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x1a4b46696b2bb4794eb3d4c26f1c55f9170fa4c5"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x857ffc55b1aa61a7ff847c82072790cae73cd883"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8236a87084f8b84306f72007f36f2618a5634494"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x9be89d2a4cd102d8fecc6bf9da793be995c22541"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xdc9cb148ecb70876db0abeb92f515a5e1dc9f580"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6b175474e89094c44da98b954eedeac495271d0f"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xedb171c18ce90b633db442f2a6f72874093b49ef"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x72e4f9f808c49a2a61de9c5896298920dc4eeea9"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xdd69db25f6d620a7bad3023c5d32761d353d3de9"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xcc8fa225d80b9c7d42f96e9570156c65d6caaa25"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8eef5a82e6aa222a60f009ac18c24ee12dbf4b41"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa5b947687163fe88c3e6af5b17ae69896f4abccf"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x61fac5f038515572d6f42d4bcb6b581642753d50"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8a60e489004ca22d775c5f2c657598278d17d9c2"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x4274cd7277c7bb0806bd5fe84b9adae466a8da0a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x03ab458634910aad20ef5f1c8ee96f1d6ac54919"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xf34960d9d60be18cc1d5afc1a6f012a723a28811"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa197e8cbbdfb22e9c8ddf310e663f5c113f7085d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc944e90c64b2c07662a292be6244bdf05cda44a7"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x761d38e5ddf6ccf6cf7c55759d5210750b5d60f3"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3e5a19c91266ad8ce2477b91585d1856b84062df"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x40a7df3df8b56147b781353d379cb960120211d7"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x95ccffae3eb8767d4a941ec43280961dde89f4de"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7ae0d42f23c33338de15bfa89c7405c068d9dc0a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x186ef81fd8e77eec8bffc3039e7ec41d5fc0b457"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x620aa20875ec1144126ea47fb27ecfe6e10d0c56"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x004e9c3ef86bc1ca1f0bb5c7662861ee93350568"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x9c4a4204b79dd291d6b6571c5be8bbcd0622f050"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x5b52bfb8062ce664d74bbcd4cd6dc7df53fd7233"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6982508145454ce325ddbe47a25d4ec3d2311933"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xcb86c6a22cb56b6cf40cafedb06ba0df188a416e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x1ceb5cb57c4d4e2b2433641b95dd330a33185a44"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8ccd897ca6160ed76755383b201c1948394328c7"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x594daad7d77592a2b97b725a7ad59d7e188b5bfa"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x4691937a7508860f876c9c0a2a617e7d9e945d4b"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xd31a59c85ae9d8edefec411d448f90841571b89c"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x2a8e1e676ec238d8a992307b495b45b3feaa5e86"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc9f00080d96cea3ef92d2e2e563d4cd41fb5bb36"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7f4c5447af6a96d8eeaee1d932338cfc57890dbd"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x00c83aecc790e8a4453e5dd3b0b4b3680501a7a7"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x418d75f65a02b3d53b2418fb8e1fe493759c7605"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6c3ea9036406852006290770bedfcaba0e23a0e8"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x899d774e0f8e14810d628db63e65dfacea682343"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x1495bc9e44af1f8bcb62278d2bec4540cf0c05ea"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8290333cef9e6d528dd5618fb97a76f268f3edd4"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc4441c2be5d8fa8126822b9929ca0b81ea0de38e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x12b6893ce26ea6341919fe289212ef77e51688c8"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x514910771af9ca656af840dff83e8264ecf986ca"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb60acd2057067dc9ed8c083f5aa227a244044fd6"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xe41d2489571d322189246dafa5ebde1f4699f498"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x26ebb8213fb8d66156f1af8908d43f7e3e367c1d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x69ebf265f86ccd67db5ce8c9fbe30243981b92ea"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xaa95f26e30001251fb905d264aa7b00ee9df6c18"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x812ba41e071c7b7fa4ebcfb62df5f45f6fa853ee"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x628a3b2e302c7e896acc432d2d0dd22b6cb9bc88"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xaa6e8127831c9de45ae56bb1b0d4d4da6e5665bd"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3f80b1c54ae920be41a77f8b902259d48cf24ccf"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x2d9d7c64f6c00e16c28595ec4ebe4065ef3a250b"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x04fa0d235c4abf4bcf4787af4cf447de572ef828"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x0f51bb10119727a7e5ea3538074fb341f56b09ad"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x111111517e4929d3dcbdfa7cce55d30d4b6bc4d6"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x68749665ff8d2d112fa859aa293f07a622782f38"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb23d80f5fefcddaa212212f028021b41ded428cf"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xed025a9fe4b30bcd68460bca42583090c2266468"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x41545f8b9472d758bb669ed8eaeeecd7a9c4ec29"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x320623b8e4ff03373931769a31fc52a4e78b5d70"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x5f98805a4e8be255a32880fdec7f6728c6568ba0"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xd2877702675e6ceb975b4a1dff9fb7baf4c91ea9"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x04f121600c8c47a754636fc9d75661a9525e05d5"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8d0d000ee44948fc98c9b98a4fa4921476f08b0d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xfcf8eda095e37a41e002e266daad7efc1579bc0a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc477d038d5420c6a9e0b031712f61c5120090de9"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8248270620aa532e4d64316017be5e873e37cc09"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x0001a500a6b18995b03f44bb040a5ffc28e45cb0"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x183015a9ba6ff60230fdeadc3f43b3d788b13e21"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xfb7b4564402e5500db5bb6d63ae671302777c75a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x1ffe8a8177d3c261600a8bd8080d424d64b7fbc2"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xec213f83defb583af3a000b1c0ada660b1902a0f"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x49642110b712c1fd7261bc074105e9e44676c68f"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x4da27a545c0c5b758a6ba100e3a049001de870f5"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x2d94aa3e47d9d5024503ca8491fce9a2fb4da198"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x04c17b9d3b29a78f7bd062a57cf44fc633e71f85"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8dd09822e83313adca54c75696ae80c5429697ff"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6524b87960c2d573ae514fd4181777e7842435d4"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x960692640ac4986ffce41620b7e3aa03cf1a0e8f"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb17548c7b510427baac4e267bea62e800b247173"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x4b1d0b9f081468d780ca1d5d79132b64301085d1"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x57b96d4af698605563a4653d882635da59bf11af"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x9e32b13ce7f2e80a01932b42553652e053d6ed8e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x9ce84f6a69986a83d92c324df10bc8e64771030f"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3bbbb6a231d0a1a12c6b79ba5bc2ed6358db5160"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x32462ba310e447ef34ff0d15bce8613aa8c4a244"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x0bb217e40f8a5cb79adf04e1aab60e5abd0dfc1e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x9e9fbde7c7a83c43913bddc8779158f1368f0413"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6440f144b7e50d6a8439336510312d2f54beb01d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xe39f5c9b6a9c225a50e1bb3b83649ae85bdf0591"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xd9a24485e71b9148e0fd51f0162072099df0db67"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x69af81e73a73b40adf4f3d4223cd9b1ece623074"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x956f47f50a910163d8bf957cf5846d573e7f87ca"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xcd5fe23c85820f7b72d0926fc9b05b43e359b7ee"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x2f42b7d686ca3effc69778b6ed8493a7787b4d6e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xe6bfd33f52d82ccb5b37e16d3dd81f9ffdabb195"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8afe4055ebc86bd2afb3940c0095c9aca511d852"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x824e35f7a75324f99300afac75ecf7354e17ea26"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xea36af87df952fd4c9a05cd792d370909bbda8db"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x090185f2135308bad17527004364ebcc2d37e5f6"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x2be056e595110b30ddd5eaf674bdac54615307d9"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x58132486f5c8756860209d01c584c0af92f163a2"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x4c44a8b7823b80161eb5e6d80c014024752607f2"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8e4f1ce473b292d56934c36976356e3e22c35585"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xe9689028ede16c2fdfe3d11855d28f8e3fc452a3"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x1ea48b9965bb5086f3b468e50ed93888a661fc17"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xeb57bf569ad976974c1f861a5923a59f40222451"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x4b19c70da4c6fa4baa0660825e889d2f7eabc279"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x046eee2cc3188071c02bfc1745a6b17c656e3f3d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x92d5942f468447f1f21c2092580f15544923b434"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x2a92525fda8d3ab481f8e2a913b64b64bd1c9fdd"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x064797ac7f833d01faeeae0e69f3af5a52a91fc8"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xf6718b2701d4a6498ef77d7c152b2137ab28b8a3"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc8388e437031b09b2c61fc4277469091382a1b13"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x28c6ce090bf0d534815c59440a197e92b4cf718f"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x982b50e55394641ca975a0eec630b120b671391a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6b4c7a5e3f0b99fcd83e9c089bddd6c7fce5c611"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x4a220e6096b25eadb88358cb44068a3248254675"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x2ecba91da63c29ea80fbe7b52632ca2d1f8e5be0"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x42bbfa2e77757c645eeaad1655e0911a7553efbc"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb9f69c75a3b67425474f8bcab9a3626d8b8249e1"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x58d97b57bb95320f9a05dc918aef65434969c2b2"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x347a96a5bd06d2e15199b032f46fb724d6c73047"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x946fb08103b400d1c79e07acccdef5cfd26cd374"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3010ccb5419f1ef26d40a7cd3f0d707a0fa127dc"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xfd418e42783382e86ae91e445406600ba144d162"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xbef26bd568e421d6708cca55ad6e35f8bfa0c406"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x44ff8620b8ca30902395a7bd3f2407e1a091bf73"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x881ba05de1e78f549cc63a8f6cabb1d4ad32250d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x643c4e15d7d62ad0abec4a9bd4b001aa3ef52d66"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x39fbbabf11738317a448031930706cd3e612e1b9"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x55af5865807b196bd0197e0902746f31fbccfa58"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xe76c6c83af64e4c60245d8c7de953df673a7a33d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x967da4048cd07ab37855c090aaf366e4ce1b9f48"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x4104b135dbc9609fc1a9490e61369036497660c8"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xe957ea0b072910f508dd2009f4acb7238c308e29"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7690202e2c2297bcd03664e31116d1dffe7e3b73"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6dea81c8171d0ba574754ef6f8b412f2ed88c54d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8f08b70456eb22f6109f57b8fafe862ed28e6040"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x155788dd4b3ccd955a5b2d461c7d6504f83f71fa"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x77e06c9eccf2e797fd462a92b6d7642ef85b0a44"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x99d8a9c45b2eca8864373a26d1459e3dff1e17f3"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xcccd1ba9f7acd6117834e0d28f25645decb1736a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x626e8036deb333b408be468f951bdb42433cbf18"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb35ed5c39f371f2cd4bc2edab1f8da314168186a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x582d872a1b094fc48f5de31d3b73f2d9be47def1"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xade6fdaba1643e4d1eef68da7170f234470938c6"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xdab396ccf3d84cf2d07c4454e10c8a6f5b008d2b"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x9f8f72aa9304c8b593d555f12ef6589cc3a579a2"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8e729198d1c59b82bd6bba579310c40d740a11c2"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x06450dee7fd2fb8e39061434babcfc05599a6fb8"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x1d4214081985ad20aa3ca93a2206ae792635cbec"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x48c3399719b582dd63eb5aadf12a40b4c3f52fa2"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x2c0687215aca7f5e2792d956e170325e92a02aca"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x37fe0f067fa808ffbdd12891c0858532cfe7361d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3d658390460295fb963f54dc0899cfb1c30776df"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x28d38df637db75533bd3f71426f3410a82041544"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x68bbed6a47194eff1cf514b50ea91895597fc91e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x0c10bf8fcb7bf5412187a595ab97a3609160b5c6"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x23d17de53aae4a767499a9d8b8c33b5b1c3ebdb0"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xae3359ed3c567482fb0102c584c23daa2693eacf"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x2ee543b8866f46cc3dc93224c6742a8911a59750"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x2de509bf0014ddf697b220be628213034d320ece"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xbbbbbbb5aa847a2003fbc6b5c16df0bd1e725f61"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x15b7c0c907e4c6b9adaaaabc300c08991d6cea05"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x0f2d719407fdbeff09d87557abb7232601fd9f29"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x408e41876cccdc0f92210600ef50372656052a38"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa36fdbbae3c9d55a1d67ee5821d53b50b63a1ab9"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb10cc888cb2cce7036f4c7ecad8a57da16161338"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x4e3fbd56cd56c3e72c1403e103b45db9da5b9d2b"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xca7af58da871736994ce360f51ec6cd28351a3df"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xf65b5c5104c4fafd4b709d9d60a185eae063276c"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x5ac34c53a04b9aaa0bf047e7291fb4e8a48f2a18"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x01ba67aac7f75f647d94220cc98fb30fcc5105bf"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xbb0e17ef65f82ab018d8edd776e8dd940327b28b"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xe3944ab788a60ca266f1eec3c26925b95f6370ad"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xf951e335afb289353dc249e82926178eac7ded78"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x557b933a7c2c45672b610f8954a3deb39a51a8ca"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xcaf06cd34acfa9664fa68982d8f17740711e0988"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb794ad95317f75c44090f64955954c3849315ffe"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x62d0a8458ed7719fdaf978fe5929c6d342b0bfce"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x427a03fb96d9a94a6727fbcfbba143444090dd64"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x64bc2ca1be492be7185faa2c8835d9b824c8a194"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x52263e871674fb1c71f4a4b3575c0cc43d027dd7"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3506424f91fd33084466f402d5d97f05f8e3b4af"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc3291556a19295ce524fad70054152cf581d8889"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x954b890704693af242613edef1b603825afcd708"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb9f599ce614feb2e1bbe58f180f370d05b39344e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xbb76a956ef664c942bc2e952b172e553118a463c"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xbd31ea8212119f94a611fa969881cba3ea06fa3d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xdefac16715671b7b6aeefe012125f1e19ee4b7d7"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x39af68d946ecdef73bbc1a29e10e8f2ce7ae6475"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x4955f6641bf9c8c163604c321f4b36e988698f75"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xba3335588d9403515223f109edc4eb7269a9ab5d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3e9c3dc19efe4271d1a65facfca55906045f7b08"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xd478161c952357f05f0292b56012cd8457f1cfbf"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa0084063ea01d5f09e56ef3ff6232a9e18b0bacd"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x57ab1ec28d129707052df4df418d58a2d46d5f51"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x853d955acef822db058eb8505911ed77f175b99e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x5cd2fac9702d68dde5a94b1af95962bcfb80fc7d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x329c6e459ffa7475718838145e5e85802db2a303"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x1f573d6fb3f13d689ff844b4ce37794d79a7ff1c"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x0a6e7ba5042b38349e437ec6db6214aec7b35676"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x4ec1b60b96193a64acae44778e51f7bff2007831"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6985884c4392d348587b19cb9eaaf157f13271cd"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8e0e57dcb1ce8d9091df38ec1bfc3b224529754a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x62b9c7356a2dc64a1969e19c23e4f579f9810aa7"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8cf8e9e63c3f39eb97a1e8020397bda93cc07196"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7420b4b9a0110cdc71fb720908340c03f9bc03ec"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6e5970dbd6fc7eb1f29c6d2edf2bc4c36124c0c1"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa6422e3e219ee6d4c1b18895275fe43556fd50ed"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x455e53cbb86018ac2b8092fdcd39d8444affc3f6"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x0000000000085d4780b73119b644ae5ecd22b376"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3432b6a60d23ca0dfca7761b7ab56459d9c964d0"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xfaba6f8e4a5e8ab82f62fe7c39859fa577269be3"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xfc4913214444af5c715cc9f7b52655e788a569ed"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x0cba60ca5ef4d42f92a5070a8fedd13be93e2861"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xfbe44cae91d7df8382208fcdc1fe80e40fbc7e9a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x4fadc7a98f2dc96510e42dd1a74141eeae0c1543"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3832d2f059e55934220881f831be501d180671a7"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x4e15361fd6b4bb609fa63c81a2be19d873717870"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xccccb68e1a848cbdb5b60a974e07aae143ed40c3"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x10633216e7e8281e33c86f02bf8e565a635d9770"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x85f138bfee4ef8e540890cfb48f620571d67eda3"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x9813037ee2218799597d83d4a5b6f3b6778218d9"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x97a9a15168c22b3c137e6381037e1499c8ad0978"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xbdab72602e9ad40fc6a6852caf43258113b8f7a5"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6ce5b005894b08edec9f338f005e79729f528807"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6710c63432a2de02954fc0f851db07146a6c0312"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xeb4c2781e4eba804ce9a9803c67d0893436bb27d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xe53ec727dbdeb9e2d5456c3be40cff031ab40a55"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x87d73e916d7057945c9bcd8cdd94e42a6f47f776"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa0335820dc549dbfae5b8d691331cadfca7026e0"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x23894dc9da6c94ecb439911caf7d337746575a72"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x2602278ee1882889b946eb11dc0e810075650983"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc55126051b22ebb829d00368f4b12bde432de5da"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3a856d4effa670c54585a5d523e96513e148e95d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x9ad37205d608b8b219e6a2573f922094cec5c200"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xadd39272e83895e7d3f244f696b7a25635f34234"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x4d224452801aced8b2f0aebe155379bb5d594381"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x64d91f12ece7362f91a6f8e7940cd55f05060b92"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x9f52c8ecbee10e00d9faaac5ee9ba0ff6550f511"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6bea7cfef803d1e3d5f7c0103f7ded065644e197"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x1151cb3d861920e07a38e03eead12c32178567f6"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x32e7c8a6e920a3cf224b678112ac78fdc0fb09d1"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x614da3b37b6f66f7ce69b4bbbcf9a55ce6168707"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xe6fd75ff38adca4b97fbcd938c86b98772431867"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6619078bdd8324e01e9a8d4b3d761b050e5ecf06"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xf816507e690f5aa4e29d164885eb5fa7a5627860"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa6c0c097741d55ecd9a3a7def3a8253fd022ceb9"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3007083eaa95497cd6b2b809fb97b6a30bdf53d3"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x4c9edd5852cd905f086c759e8383e09bff1e68b3"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3b50805453023a91a8bf641e279401a0b23fa6f9"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8143182a775c54578c8b7b3ef77982498866945d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa735a3af76cc30791c61c10d585833829d36cbe0"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8a6d4c8735371ebaf8874fbd518b56edd66024eb"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x22514ffb0d7232a56f0c24090e7b68f179faa940"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x464ebe77c293e473b48cfe96ddcf88fcf7bfdac0"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x9b3a8159e119eb09822115ae08ee1526849e1116"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x02f92800f57bcd74066f5709f1daa1a4302df875"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x419c4db4b9e25d6db2ad9691ccb832c8d9fda05e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x2a3bff78b79a009976eea096a51a948a3dc00e34"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa1faa113cbe53436df28ff0aee54275c13b40975"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6de037ef9ad2725eb40118bb1702ebb27e4aeb24"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb5d730d442e1d5b119fb4e5c843c48a64202ef92"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xd1d2eb1b1e90b638588728b4130137d262c87cae"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x5faa989af96af85384b8a938c2ede4a7378d9875"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xcc4304a31d09258b0029ea7fe63d032f52e44efe"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x61b34a012646cd7357f58ee9c0160c6d0021fa41"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb4272071ecadd69d933adcd19ca99fe80664fc08"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3abf2a4f8452ccc2cf7b4c1e4663147600646f66"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6fb3e0a217407efff7ca062d46c26e5d60a14d69"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x772358ef6ed3e18bde1263f7d229601c5fa81875"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x0b38210ea11411557c13457d4da7dc6ea731b88a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7b4328c127b85369d9f82ca0503b000d09cf9180"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x4c11249814f11b9346808179cf06e71ac328c1b5"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x14fee680690900ba0cccfc76ad70fd1b95d10e16"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xbbaec992fc2d637151daf40451f160bf85f3c8c1"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa882606494d86804b5514e07e6bd2d6a6ee6d68a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x83f5b9c25cc8fce0a7d4a1bda904bf13cfcdd9da"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x5f7ba84c7984aa5ef329b66e313498f0aed6d23a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x1776e1f26f98b1a5df9cd347953a26dd3cb46671"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xaa9806c938836627ed1a41ae871c7e1889ae02ca"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xf4d2888d29d722226fafa5d9b24f9164c092421e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa3b3beaf9c0a6160a8e47f000c094d34121f1a57"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x993864e43caa7f7f12953ad6feb1d1ca635b875f"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc0c293ce456ff0ed870add98a0828dd4d2903dbf"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc581b735a1688071a1746c968e0798d642ede491"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xebb82c932759b515b2efc1cfbb6bf2f6dbace404"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb62132e35a6c13ee1ee0f84dc5d40bad8d815206"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xf8c76dbea329ec4fa987afc514f805b21b249d79"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x5fa487bca6158c64046b2813623e20755091da0b"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xe2ad0bf751834f2fbdc62a41014f84d67ca1de2a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa0246c9032bc3a600820415ae600c6388619a14d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x9d39a5de30e57443bff2a8307a4256c8797a3497"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x33333333fede34409fb7f67c6585047e1f653333"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xff20817765cb7f73d4bde2e66e067e58d11095c2"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x73a15fed60bf67631dc6cd7bc5b6e8da8190acf5"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x0000000000ca73a6df4c58b84c5b4b847fe8ff39"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc7283b66eb1eb5fb86327f08e1b5816b0720212b"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7a569bff9f87b526b39331ca870516c1d93c0fda"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xbddf903f43dc7d9801f3f0034ba306169074ef8e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xf576e1f09e2eb4992d5ffdf68bec4ea489fa417d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb2089a7069861c8d90c8da3aacab8e9188c0c531"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xca1207647ff814039530d7d35df0e1dd2e91fa84"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa80f2c8f61c56546001f5fc2eb8d6e4e72c45d4c"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xaaef88cea01475125522e117bfe45cf32044e238"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa6610ed604047e7b76c1da288172d15bcda57596"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x44108f0223a3c3028f5fe7aec7f9bb2e66bef82f"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x808507121b80c02388fad14726482e061b8da827"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x686f2404e77ab0d9070a46cdfb0b7fecdd2318b0"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x2e7b0d4f9b2eaf782ed3d160e3a0a4b1a7930ada"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x31429d1856ad1377a8a0079410b297e1a9e214c2"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xdae0fafd65385e7775cf75b1398735155ef6acd2"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa95c5ebb86e0de73b4fb8c47a45b792cfea28c23"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xfe8526a77a2c3590e5973ba81308b90bea21fbff"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x50b275a15e4f5004aa96f972a30e6a9c718b203f"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xd8c0b13b551718b808fc97ead59499d5ef862775"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x856c4efb76c1d1ae02e20ceb03a2a6a08b0b8dc3"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x0c9c7712c83b3c70e7c5e11100d33d9401bdf9dd"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xfe3e6a25e6b192a42a44ecddcd13796471735acf"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xda67b4284609d2d48e5d10cfac411572727dc1ed"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x43d7e65b8ff49698d9550a7f315c87e67344fb59"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x9f6f91078a5072a8b54695dafa2374ab3ccd603b"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7dd9c5cba05e151c895fde1cf355c9a1d5da6429"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xf94b5c5651c888d928439ab6514b93944eee6f48"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x88800092ff476844f74dc2fc427974bbee2794ae"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x5d3a536e4d6dbd6114cc1ead35777bab948e3643"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x45e02bc2875a2914c4f585bbf92a6f28bc07cb70"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x944824290cc12f31ae18ef51216a223ba4063092"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x9aab071b4129b083b01cb5a0cb513ce7eca26fa5"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x64b78325d7495d6d4be92f234fa3f3b8d8964b8b"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x011e128ec62840186f4a07e85e3ace28858c5606"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8fe815417913a93ea99049fc0718ee1647a2a07c"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xae78736cd615f374d3085123a210448e74fc6393"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x28561b8a2360f463011c16b6cc0b0cbef8dbbcad"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x67f9e469b44c471d3cd945122a28547e76b79820"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc00e94cb662c3520282e6f5717214004a7f26888"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xd7c9f0e536dc865ae858b0c0453fe76d13c3beac"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb7109df1a93f8fe2b8162c6207c9b846c1c68090"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x90685e300a4c4532efcefe91202dfe1dfd572f47"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x62f03b52c377fea3eb71d451a95ad86c818755d1"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xcab254f1a32343f11ab41fbde90ecb410cde348a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x19062190b1925b5b6689d7073fdfc8c2976ef8cb"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x607f4c5bb672230e8672085532f7e901544a7375"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xdb792b1d8869a7cfc34916d6c845ff05a7c9b789"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7a56e1c57c7475ccf742a1832b028f0456652f97"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x0b010000b7624eb9b3dfbc279673c76e9d29d5f7"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x64aa3364f17a4d01c6f1751fd97c2bd3d7e7f1d5"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3845badade8e6dff049820680d1f14bd3903a5d0"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb62e45c3df611dce236a6ddc7a493d79f9dfadef"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xe8a3bf796ca5a13283ec6b1c5b645b91d7cfef5d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb50721bcf8d664c30412cfbc6cf7a15145234ad1"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x00282fd551d03dc033256c4bf119532e8c735d8a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7f89f674b7d264944027e78e5f58eb2bbbb7cfa3"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x948c70dc6169bfb10028fdbe96cbc72e9562b2ac"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3aada3e213abf8529606924d8d1c55cbdc70bf74"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x05be1d4c307c19450a6fd7ce7307ce72a3829a60"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x15d4c048f83bd7e37d49ea4c83a07267ec4203da"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xda987c655ebc38c801db64a8608bc1aa56cd9a31"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x056fd409e1d7a124bd7017459dfea2f387b6d5cd"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x037a54aab062628c9bbae1fdb1583c195585fe41"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7c8155909cd385f120a56ef90728dd50f9ccbe52"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xfd36fa88bb3fea8d1264fc89d70723b6a2b56958"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x45804880de22913dafe09f4980848ece6ecbaf78"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x58cb30368ceb2d194740b144eab4c2da8a917dcb"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x4d4574f50dd8b9dbe623cf329dcc78d76935e610"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xf21661d0d1d76d3ecb8e1b9f1c923dbfffae4097"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa00453052a36d43a99ac1ca145dfe4a952ca33b8"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x40d16fc0246ad3160ccc09b8d0d3a2cd28ae6c2f"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xd0d56273290d339aaf1417d9bfa1bb8cfe8a0933"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x720cd16b011b987da3518fbf38c3071d4f0d1495"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7ce89243cc0d9e746609c57845eccbd9bb4b7315"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x32353a6c91143bfd6c7d363b546e62a9a2489a20"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7a58c0be72be218b41c608b7fe7c5bb630736c71"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8c1bed5b9a0928467c9b1341da1d7bd5e10b6549"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xbc544207ff1c5b2bc47a35f745010b603b97e99e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x15f74458ae0bfdaa1a96ca1aa779d715cc1eefe4"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xdc98c5543f3004debfaad8966ec403093d0aa4a8"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3b991130eae3cca364406d718da22fa1c3e7c256"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x0e9cc0f7e550bd43bd2af2214563c47699f96479"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x644192291cc835a93d6330b24ea5f5fedd0eef9e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xd084944d3c05cd115c09d072b9f44ba3e0e45921"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x30f7c830e0c2f4bec871df809d73e27ef19eb151"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc98d64da73a6616c42117b582e832812e7b8d57f"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6c3f90f043a72fa612cbac8115ee7e52bde6e490"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa974c709cfb4566686553a20790685a47aceaa33"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x243c9be13faba09f945ccc565547293337da0ad7"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x9138c8779a0ac8a84d69617d5715bd8afa23c650"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xcafe001067cdef266afb7eb5a286dcfd277f3de5"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xe66b3aa360bb78468c00bebe163630269db3324f"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x1121acc14c63f3c872bfca497d10926a6098aac5"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xdf90124b8a10d52a5df27d3f61f94f44ade09f12"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc221b7e65ffc80de234bbb6667abdd46593d34f0"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8290d7a64f25e6b5002d98367e8367c1b532b534"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x5dd57da40e6866c9fcc34f4b6ddc89f1ba740dfe"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x761a3557184cbc07b7493da0661c41177b2f97fa"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x758b4684be769e92eefea93f60dda0181ea303ec"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa21af1050f7b26e0cff45ee51548254c41ed6b5c"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x70e8de73ce538da2beed35d14187f6959a8eca96"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc5fb36dd2fb59d3b98deff88425a3f425ee469ed"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x24c19f7101c1731b85f1127eaa0407732e36ecdd"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb528edbef013aff855ac3c50b381f253af13b997"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb4efd85c19999d84251304bda99e90b92300bd93"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x00869e8e2e0343edd11314e6ccb0d78d51547ee5"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xae7ab96520de3a18e5e111b5eaab095312d7fe84"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x95af4af910c28e8ece4512bfe46f1f33687424ce"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x413530a7beb9ff6c44e9e6c9001c93b785420c32"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc669928185dbce49d2230cc9b0979be6dc797957"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xd6c67b93a7b248df608a653d82a100556144c5da"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb0ac2b5a73da0e67a8e5489ba922b3f8d582e058"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x09395a2a58db45db0da254c7eaa5ac469d8bdc85"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6bc08509b36a98e829dffad49fde5e412645d0a3"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6368e1e18c4c419ddfc608a0bed1ccb87b9250fc"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8390a1da07e376ef7add4be859ba74fb83aa02d5"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x96a5399d07896f757bd4c6ef56461f58db951862"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb98d4c97425d9908e66e53a6fdf673acca0be986"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x903bef1736cddf2a537176cf3c64579c3867a881"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x35a532d376ffd9a705d0bb319532837337a398e7"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x18e5f92103d1b34623738ee79214b1659f2ee109"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xf1a7000000950c7ad8aff13118bb7ab561a448ee"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3446dd70b2d52a6bf4a5a192d9b0a161295ab7f9"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xbbbbca6a901c926f240b89eacb641d8aec7aeafd"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x112b08621e27e10773ec95d250604a041f36c582"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xcf3c8be2e2c42331da80ef210e9b1b307c03d36a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x67466be17df832165f8c80a5a120ccc652bd7e69"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xecbee2fae67709f718426ddc3bf770b26b95ed20"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x2b591e99afe9f32eaa6214f7b7629768c40eeb39"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x23fa3aa82858e7ad1f0f04352f4bb7f5e1bbfb68"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7da2641000cbb407c329310c461b2cb9c70c3046"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xdbdd6f355a37b94e6c7d32fef548e98a280b8df5"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x24fcfc492c1393274b6bcd568ac9e225bec93584"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x2dff88a56767223a5529ea5960da7a3f5f766406"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3af33bef05c2dcb3c7288b77fe1c8d2aeba4d789"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x88acdd2a6425c3faae4bc9650fd7e27e0bebb7ab"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xed35af169af46a02ee13b9d79eb57d6d68c1749e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc0db17bc219c5ca8746c29ee47862ee3ad742f4a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xbe1a001fe942f96eea22ba08783140b9dcc09d28"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x5f64ab1544d28732f0a24f4713c2c8ec0da089f0"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xe28b3b32b6c345a34ff64674606124dd5aceca30"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x82a605d6d9114f4ad6d5ee461027477eeed31e34"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x955d5c14c8d4944da1ea7836bd44d54a8ec35ba1"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x03aa6298f1370642642415edc0db8b957783e8d6"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x38e68a37e401f7271568cecaac63c6b1e19130b4"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7a420044c02e1a55dc75901ac1587627f840799c"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x9b2517d91203c8496f5d50262cf9f0f07af365f5"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xddbcdd8637d5cedd15eeee398108fca05a71b32b"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xa0afaa285ce85974c3c881256cb7f225e3a1178a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x97ad75064b20fb2b2447fed4fa953bf7f007a706"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7659ce147d0e714454073a5dd7003544234b6aa0"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8802269d1283cdb2a5a329649e5cb4cdcee91ab6"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x20d4db1946859e2adb0e5acc2eac58047ad41395"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc9b53ab2679f573e480d01e0f49e2b5cfb7a3eab"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x16ae2fb0374fdd9c413a45c69f954b54a3cb0116"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x5283d291dbcf85356a21ba090e6db59121208b44"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xe636f94a71ec52cc61ef21787ae351ad832347b7"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x95392f142af1c12f6e39897ff9b09c599666b50c"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x76bc677d444f1e9d57daf5187ee2b7dc852745ae"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x08c32b0726c5684024ea6e141c50ade9690bbdcc"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x8207c1ffc5b6804f6024322ccf34f29c3541ae26"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb131f4a55907b10d1f0a50d8ab8fa09ec342cd74"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xade00c28244d5ce17d72e40330b1c318cd12b7c3"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xddf73eacb2218377fc38679ad14dfce51b651dd1"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6df0e641fc9847c0c6fde39be6253045440c14d3"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x580e933d90091b9ce380740e3a4a39c67eb85b4c"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xf190dbd849e372ff824e631a1fdf199f38358bcf"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3ba925fdeae6b46d0bb4d424d829982cb2f7309e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xb6ee9668771a79be7967ee29a63d4184f8097143"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc76d53f988820fe70e01eccb0248b312c2f1c7ca"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x5026f006b85729a8b14553fae6af249ad16c9aab"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x1a7e4e63778b4f12a199c062f3efdd288afcbce8"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xfe2e637202056d30016725477c5da089ab0a043a"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xf091867ec603a6628ed83d274e835539d82e9cc8"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x18084fba666a33d37592fa2633fd49a74dd93a88"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x6b3595068778dd592e39a122f4f5a5cf09c90fe2"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x35e78b3982e87ecfd5b3f3265b601c046cdbe232"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xf939e0a03fb07f59a73314e73794be0e57ac1b4e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x3472a5a71965499acd81997a54bba8d852c6e53d"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xaea46a60368a7bd060eec7df8cba43b7ef41ad85"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x77777feddddffc19ff86db637967013e6c6a116c"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x7de91b204c1c737bcee6f000aaa6569cf7061cb7"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xbe042e9d09cb588331ff911c2b46fd833a3e5bd6"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x382ea807a61a418479318efd96f1efbc5c1f2c21"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x375abb85c329753b1ba849a601438ae77eec9893"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xfa3e941d1f6b7b10ed84a0c211bfa8aee907965e"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x56072c95faa701256059aa122697b133aded9279"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xc20059e0317de91738d13af027dfc4a50781b066"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x623cd3a3edf080057892aaf8d773bbb7a5c9b6e9"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xdd974d5c2e2928dea5f71b9825b8b646686bd200"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0xba5bde662c17e2adff1075610382b9b691296350"
      },
      {
        "type": "swap_hub",
        "source": "eth_CENTRAL",
        "target": "eth_0x106b39a28a3bd5bb88c69b813c463f163704773e"
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
# Tiny DiGraph helper
# =========================

class SimpleDiGraph:
    def __init__(self):
        self.adj: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
        self.nodes: Dict[str, Dict[str, Any]] = {}
    def add_node(self, n: str, **attrs):
        if n not in self.nodes:
            self.nodes[n] = {}
        self.nodes[n].update(attrs)
        self.adj.setdefault(n, [])
    def add_edge(self, u: str, v: str, **attrs):
        self.adj.setdefault(u, [])
        self.adj[u].append((v, attrs))
    def neighbors(self, u: str) -> List[Tuple[str, Dict[str, Any]]]:
        return self.adj.get(u, [])

# =========================
# UltimateDebugRouter
# =========================

class UltimateDebugRouter:
    def __init__(self, node_link_graph: Dict[str, Any], cfg: EdgeCostConfig, ctx: Context):
        self.ctx = ctx
        self.cfg = cfg

        self.raw: Optional[Dict[str, Any]] = None
        self.G_nodes: Dict[str, Dict[str, Any]] = {}
        self.G_adj_undirected: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
        self.R = SimpleDiGraph()
        self.token_index_by_symbol: Dict[Tuple[str, str], str] = {}
        self.token_index_by_addr: Dict[Tuple[str, str], str] = {}
        self.hubs: Dict[str, str] = {}
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
            self._validate_input(node_link_graph)
            self.debug_info["initialization_steps"].append("✅ Input validation")

            self.raw = node_link_graph
            self.debug_info["initialization_steps"].append("✅ Raw data stored")

            self._safe_load_node_link()
            self.debug_info["initialization_steps"].append("✅ Node-link loading")

            self._safe_index_nodes()
            self.debug_info["initialization_steps"].append("✅ Node indexing")

            self._safe_build_router()
            self.debug_info["initialization_steps"].append("✅ Router building")

            self._safe_log_diagnostics()
            self.debug_info["initialization_steps"].append("✅ Diagnostics")
        except Exception as e:
            err = f"Initialization failed at step: {e}"
            try:
                self.ctx.logger.error(err)
                self.ctx.logger.error(traceback.format_exc())
            except Exception:
                pass
            self.debug_info["initialization_error"] = err
            self.debug_info["initialization_traceback"] = traceback.format_exc()
            raise RuntimeError(err) from e

    # ---- utils
    def _f(self, x: Any, default: float = 0.0) -> float:
        try: return float(x)
        except Exception: return default
    def _norm(self, s: Optional[str]) -> str:
        return (s or "").strip().upper()
    def _low(self, s: Optional[str]) -> str:
        return (s or "").strip().lower()

    # ---- STEP 1
    def _validate_input(self, data: Dict[str, Any]):
        if not isinstance(data, dict): raise ValueError(f"Expected dict, got {type(data)}")
        if "nodes" not in data: raise ValueError("Missing 'nodes' key in data")
        if "links" not in data: raise ValueError("Missing 'links' key in data")
        nodes, links = data["nodes"], data["links"]
        if not isinstance(nodes, list): raise ValueError(f"Expected nodes list, got {type(nodes)}")
        if not isinstance(links, list): raise ValueError(f"Expected links list, got {type(links)}")

    # ---- STEP 2
    def _safe_load_node_link(self):
        nodes = self.raw.get("nodes", [])
        links = self.raw.get("links", [])
        self.debug_info["total_nodes"] = len(nodes)
        self.debug_info["total_edges"] = len(links)
        for n in nodes:
            if not isinstance(n, dict): continue
            nid = n.get("id") or n.get("name")
            if not nid: continue
            self.G_nodes[nid] = {k: v for k, v in n.items() if k != "id"}
            self.G_adj_undirected.setdefault(nid, [])
            ntype = n.get("type", "unknown")
            if ntype == "token": self.debug_info["token_nodes"].append(nid)
            elif ntype == "pool": self.debug_info["pool_nodes"].append(nid)
        for e in links:
            if not isinstance(e, dict): continue
            u, v = e.get("source"), e.get("target")
            if not u or not v or u not in self.G_nodes or v not in self.G_nodes: continue
            attrs = {k: v2 for k, v2 in e.items() if k not in ("source", "target")}
            self.G_adj_undirected[u].append((v, attrs))
            self.G_adj_undirected[v].append((u, attrs))

    # ---- STEP 3
    def _safe_index_nodes(self):
        for nid, data in self.G_nodes.items():
            ntype = data.get("type")
            chain = self._low(data.get("chain"))
            if ntype == "central_token" and chain:
                self.hubs[chain] = nid
                self.debug_info["hub_nodes"][chain] = nid
            elif ntype == "token" and chain:
                symbol = data.get("name") or data.get("symbol")
                if symbol:
                    self.token_index_by_symbol[(chain, self._norm(symbol))] = nid
                    self.debug_info["token_symbols"].setdefault(chain, []).append(symbol)
                # index by address
                addr = None
                if "_" in nid:
                    tail = nid.split("_", 1)[1]
                    if self._low(tail).startswith("0x"): addr = self._low(tail)
                meta_addr = self._low(data.get("address"))
                if meta_addr and meta_addr.startswith("0x"): addr = meta_addr
                if addr:
                    self.token_index_by_addr[(chain, addr)] = nid

    # ---- STEP 4
    def _edge_cost_for_pool(self, pool_id: str) -> float:
        meta = self.G_nodes.get(pool_id, {})
        liq = self._f(meta.get("liquidity"))
        tvl = self._f(meta.get("totalValueLockedUSD"))
        if liq < self.cfg.min_liquidity or tvl < self.cfg.min_tvl:
            return float("inf")
        inv_liq = 1.0 / max(liq, 1.0)
        inv_tvl = 1.0 / max(tvl, 1.0)
        return (self.cfg.alpha_liquidity * inv_liq
                + self.cfg.beta_tvl * inv_tvl
                + self.cfg.gamma_gas_per_swap
                + self.cfg.slippage_bias)

    def _pool_tokens_for(self, pool_id: str) -> Optional[Tuple[str, str, str]]:
        pmeta = self.G_nodes.get(pool_id, {})
        if pmeta.get("type") != "pool": return None
        chain = self._low(pmeta.get("chain"))

        # via links
        tokens = []
        for nbr, edata in self.G_adj_undirected.get(pool_id, []):
            if edata.get("type") == "belongs_to_pool" and self.G_nodes.get(nbr, {}).get("type") == "token":
                tokens.append(nbr)
        if len(tokens) >= 2:
            return (chain, tokens[0], tokens[1])

        # fallback via addresses
        t0 = self._low(pmeta.get("token0"))
        t1 = self._low(pmeta.get("token1"))
        if chain and t0 and t1 and t0.startswith("0x") and t1.startswith("0x"):
            a = self.token_index_by_addr.get((chain, t0))
            b = self.token_index_by_addr.get((chain, t1))
            if a and b: return (chain, a, b)
        return None

    def _safe_build_router(self):
        for nid, attrs in self.G_nodes.items():
            self.R.add_node(nid, **attrs)

        edges = 0; valid = 0
        for nid, attrs in self.G_nodes.items():
            if attrs.get("type") != "pool": continue
            pt = self._pool_tokens_for(nid)
            if not pt: continue
            cost = self._edge_cost_for_pool(nid)
            if cost == float("inf"): continue
            chain, t0, t1 = pt
            self.R.add_edge(t0, t1, kind="swap", pool=nid, chain=chain, weight=cost)
            self.R.add_edge(t1, t0, kind="swap", pool=nid, chain=chain, weight=cost)
            edges += 2; valid += 1
        self.debug_info["routing_edges"] = edges

    # ---- STEP 5
    def _safe_log_diagnostics(self):
        try:
            self.ctx.logger.info(f"Routing edges: {self.debug_info['routing_edges']}")
        except Exception:
            pass

    # ---- token resolving
    def _resolve_token_node(self, chain: str, token: str) -> Optional[str]:
        if token in self.G_nodes: return token
        ch = self._low(chain)
        by_sym = self.token_index_by_symbol.get((ch, self._norm(token)))
        if by_sym: return by_sym
        tl = self._low(token)
        if tl.startswith("0x"):
            by_addr = self.token_index_by_addr.get((ch, tl))
            if by_addr: return by_addr
        for nid, meta in self.G_nodes.items():
            if meta.get("type") != "token": continue
            if self._low(meta.get("chain")) != ch: continue
            name = meta.get("name") or meta.get("symbol")
            if name and self._norm(name) == self._norm(token): return nid
        return None

    # ---- pathfinding
    def best_paths(
        self, src_chain: str, src_token: str, dst_chain: str, dst_token: str,
        *, top_k: int = 3, max_hops: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], Dict]:
        max_hops = max_hops or self.cfg.max_hops
        src_id = self._resolve_token_node(src_chain, src_token)
        dst_id = self._resolve_token_node(dst_chain, dst_token)
        debug = {"resolved": {"src": src_id, "dst": dst_id}, "top_k": top_k, "max_hops": max_hops}
        if not src_id or not dst_id: return [], debug
        if src_id == dst_id:
            rc = RouteCandidate(total_cost=0.0, hops=0, steps=[
                RouteStep(kind="noop", from_node=src_id, to_node=dst_id, chain=src_chain, pool="", weight=0.0)
            ]).dict()
            return [rc], debug

        import heapq
        h: List[Tuple[float, int, str, List[Dict[str, Any]]]] = []
        heapq.heappush(h, (0.0, 0, src_id, []))
        best_costs: Dict[str, List[float]] = {src_id: [0.0]}
        found: List[List[Dict[str, Any]]] = []

        while h and len(found) < top_k:
            cost, hops, node, steps = heapq.heappop(h)
            if hops > max_hops: continue
            if node == dst_id:
                found.append(steps); continue
            for nbr, edata in self.R.neighbors(node):
                if edata.get("kind") not in ("swap", "bridge"): continue
                w = float(edata.get("weight", 1.0))
                if w == float("inf"): continue
                nh = hops + 1
                if nh > max_hops: continue
                nc = cost + w
                lst = best_costs.setdefault(nbr, [])
                if len(lst) < top_k or nc < max(lst):
                    lst.append(nc); lst.sort()
                    if len(lst) > top_k: lst.pop()
                    new_steps = steps + [{
                        "kind": edata.get("kind", "swap"),
                        "from": node, "to": nbr,
                        "chain": edata.get("chain", ""), "pool": edata.get("pool", ""),
                        "weight": w,
                    }]
                    heapq.heappush(h, (nc, nh, nbr, new_steps))

        routes: List[Dict[str, Any]] = []
        for s in found:
            total = sum(step["weight"] for step in s) if s else 0.0
            steps = [RouteStep(kind=t["kind"], from_node=t["from"], to_node=t["to"],
                               chain=t.get("chain",""), pool=t.get("pool",""), weight=float(t["weight"]))
                     for t in s]
            routes.append(RouteCandidate(total_cost=total, hops=len(s), steps=steps).dict())
        return routes, debug

# =========================
# Agent (define BEFORE decorators)
# =========================

agent = Agent(name="ultimate_debug_router", seed="ultimate_debug_seed_2025")

# =========================
# Lazy factory + stateless handler (no globals)
# =========================

@lru_cache(maxsize=1)
def _get_router_cached(graph_blob: str) -> UltimateDebugRouter:
    data = json.loads(graph_blob)
    # Minimal ctx for router logs
    class _NullLogger:
        def info(self, *a, **k): pass
        def warning(self, *a, **k): pass
        def error(self, *a, **k): pass
    class _NullCtx:
        logger = _NullLogger()
    return UltimateDebugRouter(data, CFG, _NullCtx())

def _build_router_or_error(ctx: Context) -> Tuple[Optional[UltimateDebugRouter], Optional[Dict[str, Any]]]:
    try:
        return _get_router_cached(SAMPLE_JSON_DATA), None
    except Exception as e:
        err = {"error": "router_init_failed", "message": f"{type(e).__name__}: {e}", "traceback": traceback.format_exc()}
        ctx.logger.error(f"🔴 Router init failed: {err['message']}")
        return None, err

@agent.on_message(model=RouteQuery, replies=RouteResult)
async def _on_route_query(ctx: Context, sender: str, msg: RouteQuery):
    router, init_err = _build_router_or_error(ctx)
    if router is None:
        await ctx.send(sender, RouteResult(routes=[], note="router_init_failed", debug_info=init_err))
        return

    # Per-request cfg overrides
    max_hops = msg.max_hops if msg.max_hops is not None else CFG.max_hops
    tmp_cfg = EdgeCostConfig(**{**CFG.__dict__})
    if msg.min_liquidity is not None: tmp_cfg.min_liquidity = float(msg.min_liquidity)
    if msg.min_tvl is not None: tmp_cfg.min_tvl = float(msg.min_tvl)
    router.cfg = tmp_cfg

    try:
        routes, debug = router.best_paths(
            src_chain=msg.src_chain, src_token=msg.src_token,
            dst_chain=msg.dst_chain, dst_token=msg.dst_token,
            top_k=msg.top_k or 3, max_hops=max_hops
        )
        await ctx.send(sender, RouteResult(
            routes=[RouteCandidate(**r) for r in routes],
            note=("ok" if routes else "no_route_found"),
            debug_info=debug
        ))
    except Exception as e:
        await ctx.send(sender, RouteResult(
            routes=[], note="pathfinding_error",
            debug_info={"message": f"{type(e).__name__}: {e}", "traceback": traceback.format_exc()}
        ))

if __name__ == "__main__":
    agent.run()
