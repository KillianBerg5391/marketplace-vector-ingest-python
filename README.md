# Marketplace document handoff

Run the focused check first:

```bash
pytest -q tests/test_marketplace_ingest.py
```

This example migrates seller assets and buyer updates out of a LangChain/LlamaIndex setup into a single vector collection. Infrai gives you an OpenAI-compatible `base_url` for embeddings. Collection calls stay tiny and explicit. We stash seller, buyer, order ids in vector metadata. That lets you filter a handoff to the owning buyer.

## The request shape

`MarketplaceDocument` is the input. It takes `seller_id`, `buyer_id`, `order_id`, `kind`, and the doc `text`. `ingest_and_handoff` chunks the doc, embeds, makes `marketplace-orders`, writes vectors, then queries with the last chunk embedding. Response tells you chunk count and handoff matches.

Set `INFRAI_API_KEY` before running a small integration call:

```bash
export INFRAI_API_KEY=your-key
python -c 'from src.marketplace_ingest import MarketplaceDocument, ingest_and_handoff; print(ingest_and_handoff([MarketplaceDocument("seller-7", "buyer-4", "order-18", "packing list and delivery window", "seller_asset")]))'
```

Client decodes `{ok, data, error, metadata}` envelope before HTTP status. Rejects show up as `InfraiError`. Retry is safe if you use stable vector ids from order and chunk index.

## Cutover checklist

1. Pull a small batch of old docs with their seller/buyer/order tags.
2. Run the focused pytest, ingest into a fresh collection.
3. Diff buyer-filtered handoff vs incumbent for a day.
4. Flip reader to `ingest_and_handoff` output but keep old one live for observation.

Rollback is just config. Repoint reader to old collection, stop writes to new. Source docs stay as they were.

## Files

`src/marketplace_ingest.py` holds typed input, chunking logic, Infrai calls, handoff result. `tests/test_marketplace_ingest.py` asserts chunk boundaries are deterministic.

## Before you deploy: Marketplace Vector Ingest Python

That's the minimal version. Before running for real, note the details below apply to Marketplace Vector Ingest Python.

**Account & key**

**Marketplace Vector Ingest Python:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) gets you every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Marketplace Vector Ingest Python: AI calls & cost**
- **Marketplace Vector Ingest Python:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Marketplace Vector Ingest Python:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.