"""Step 0: bitcoind(regtest)とJSON-RPCで会話してみる。

やること:
  1. ウォレットを作る(既にあればロード)
  2. 101ブロック掘って、採掘報酬を使える状態にする
     (coinbaseの報酬は100ブロック経たないと使えない = マスタリングビットコインの「成熟」の話)
  3. 新しいアドレスへ何回か送金して、1ブロック掘って確定させる
  4. 最新ブロックの中身を覗いてみる

実行: python scripts/hello_rpc.py
"""

import json
import os
import random
import pandas as pd

import requests
from dotenv import load_dotenv

load_dotenv()

RPC_URL = os.environ["BTC_RPC_URL"]
AUTH = (os.environ["BTC_RPC_USER"], os.environ["BTC_RPC_PASSWORD"])
WALLET = "kei"


def rpc(method: str, *params, wallet: str | None = None):
    """bitcoindのJSON-RPCを1回叩く最小クライアント。"""
    url = f"{RPC_URL}/wallet/{wallet}" if wallet else RPC_URL
    payload = {"jsonrpc": "1.0", "id": method, "method": method, "params": list(params)}
    r = requests.post(url, json=payload, auth=AUTH, timeout=30)
    body = r.json()
    if body.get("error"):
        raise RuntimeError(f"{method}: {body['error']}")
    return body["result"]


def ensure_wallet():
    if WALLET in rpc("listwallets"):
        return
    try:
        rpc("loadwallet", WALLET)
    except RuntimeError:
        rpc("createwallet", WALLET)


def main():
    info = rpc("getblockchaininfo")
    print(f"chain={info['chain']} blocks={info['blocks']}")

    ensure_wallet()
    miner = rpc("getnewaddress", wallet=WALLET)

    if info["blocks"] < 101:
        rpc("generatetoaddress", 101 - info["blocks"], miner)
    print("balance:", rpc("getbalance", wallet=WALLET), "BTC")

    # 適当な宛先に何回か送金(あとで取引グラフにするための種データ)
    for _ in range(5):
        to = rpc("getnewaddress", wallet=WALLET)
        amount = round(random.uniform(0.1, 2.0), 8)
        txid = rpc("sendtoaddress", to, amount, wallet=WALLET)
        print(f"sent {amount} BTC -> {to[:12]}...  txid={txid[:16]}...")

    rpc("generatetoaddress", 1, miner)  # mempoolの取引をブロックに入れる

    tip = rpc("getbestblockhash")
    block = rpc("getblock", tip, 2)  # verbosity=2: 取引の中身まで展開
    print(f"\nlatest block height={block['height']} txs={len(block['tx'])}")
    print("1件目以外(=coinbase以外)の取引を1つ表示:")
    print(json.dumps(block["tx"][1], indent=2)[:1500])
    rows = []
    for tx in block['tx']:
        vals = [out["values"] for out in tx["vout"]]
        rows.append({"txid"      : tx["txid"][:12],
                     "vin"       : len(tx["vin"]),
                     "vout"      : len(tx["vout"]),
                     "val"       : vals,
                     "val_amount": sum(val)
                     })
    tr_df = pd.DataFrame(rows)
    print(tr_df.to_string(index=False))


if __name__ == "__main__":
    main()
