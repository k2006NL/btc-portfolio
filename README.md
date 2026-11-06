# btc-portfolio

Bitcoinのregtestノードから取引データを取り込み、DBに入れてAPIで提供し、不正検知までやるポートフォリオ。
**バックエンド × データエンジニアリング × データサイエンス** を1本で通す。

```
bitcoind (regtest) ──RPC──▶ ingest (Python) ──▶ PostgreSQL ──▶ FastAPI
                                                     │
                                                     └──▶ 分析 / GNN不正検知 (Elliptic)
```

## セットアップ

```bash
docker compose up -d
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/hello_rpc.py   # Step 0
```

困ったら: `docker compose logs bitcoind`、`docker compose exec bitcoind bitcoin-cli -regtest -rpcuser=... -rpcpassword=... getblockchaininfo`

---

## ロードマップ

各ステップに「完成条件」がある。満たしたらコミットして次へ。
マスタリングビットコイン(MB)とDDIAの対応章も書いておく。

### Step 0: ノードと会話する(半日)
- `hello_rpc.py` を動かして、ブロックと取引のJSONを眺める
- `vin` / `vout` / `scriptPubKey` / `value` が何を意味するか説明できるようにする
- 📖 MB: 鍵とアドレス、トランザクションの章
- ✅ 完成条件: 「UTXOとは何か」「coinbase取引はなぜ100ブロック使えないか」を自分の言葉でREADMEに書ける

### Step 1: 取引を自分で作る(1日)
- 送金パターンを作るスクリプト `scripts/simulate.py` を書く
  - 普通のユーザー(少額をたまに送る)、取引所っぽいアドレス(集約して大量に出す)、
    「不審」なパターン(細かく分割→別アドレス群→再集約 = ピーリングチェーン/スマーフィング)
- 不審パターンを出したアドレスを `labels.csv` に記録しておく(=自前の正解ラベル)
- ✅ 完成条件: 数百ブロック・数千取引のデータが溜まっている

### Step 2: DB設計と取り込み(2〜3日) ← DEの核
- テーブル設計を自分で考える。最低限:
  `blocks`, `transactions`, `tx_inputs`, `tx_outputs`(+ 使われたかどうか)
- `ingest/` を作って、ブロック高さ順にRPC → INSERT
- 考えるポイント:
  - **冪等性**: 同じブロックを2回取り込んでも壊れないか(`ON CONFLICT`)
  - **差分取り込み**: 前回どこまで入れたかをどう覚えるか
  - **リオーグ**: ブロックが巻き戻ったらどうするか(regtestの `invalidateblock` で再現できる)
  - **インデックス**: アドレスで引くクエリが速いか(`EXPLAIN ANALYZE`)
- ✅ 完成条件: 取り込みを途中で止めて再開しても、DBの残高とノードの `getbalance` が一致する

### Step 3: API(2日) ← バックエンドの核
- FastAPIで作る:
  - `GET /blocks/{height}`
  - `GET /tx/{txid}`
  - `GET /address/{addr}/balance`、`/address/{addr}/txs`(ページネーション付き)
  - `GET /address/{addr}/graph?depth=2`(取引グラフをJSONで返す)
- テストを書く(pytest + テスト用DB)
- ✅ 完成条件: `docker compose up` だけでAPIまで立ち上がり、`/docs` から全部叩ける

### Step 4: 分析(2日)
- アドレス × アドレスの取引グラフを作る(networkx)
- 特徴量: 入出力数、金額分布、次数、到達可能性、時間間隔 など
- Step 1の自前ラベルで、まずはロジスティック回帰 / LightGBM
- ✅ 完成条件: 不審パターンをどのくらい当てられるか、ノートブックにまとまっている

### Step 5: Elliptic Data SetでGNN(3日〜)
- Kaggleの Elliptic Data Set(実際のBitcoin取引グラフ、illicit/licitラベル付き)
- ベースライン(LightGBM)→ GCN / GraphSAGE(PyTorch Geometric)で比較
- 時系列で train/test を切る(未来のデータでリークしない)
- ✅ 完成条件: 結果と考察をREADMEかブログにまとめる

### おまけ(余裕があれば)
- GitHub ActionsでCI
- 取り込みをAirflow / Dagsterでスケジュール化
- 「トークン化預金が広がったらAML分析はどう変わるか」を1ページで書く(面接用)

---

## 進捗ログ

- [ ] Step 0
- [ ] Step 1
- [ ] Step 2
- [ ] Step 3
- [ ] Step 4
- [ ] Step 5
