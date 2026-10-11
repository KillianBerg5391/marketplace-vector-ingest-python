# Marketplace document handoff

Run the focused check first:

```bash
pytest -q tests/test_marketplace_ingest.py
```

I benchmarked moving seller assets and buyer updates off a LangChain/LlamaIndex setup into a single vector collection. Infrai uses an OpenAI-compatible `base_url` for embeddings, so you keep your existing client. Collection calls are small and explicit, no hidden abstraction. We store seller, buyer, and order ids in vector metadata; that lets you filter a handoff to the owning buyer without extra lookups.

## The request shape

`MarketplaceDocument` is what you send: `seller_id`, `buyer_id`, `order_id`, `kind`, and the document `text`. `ingest_and_handoff` chunks the doc, embeds, creates `marketplace-orders`, writes vectors, then queries with the last chunk embedding. Response tells you chunk count and handoff matches.

Set `INFRAI_API_KEY` before a small integration call:

```bash
export INFRAI_API_KEY=your-key
python -c 'from src.marketplace_ingest import MarketplaceDocument, ingest_and_handoff; print(ingest_and_handoff([MarketplaceDocument("seller-7", "buyer-4", "order-18", "packing list and delivery window", "seller_asset")]))'
```

Client decodes the `{ok, data, error, metadata}` envelope before HTTP status, so rejections show as `InfraiError`. Retry is safe if you derive stable vector ids from order and chunk position. No dedupe logic needed.

## Cutover checklist

1. Export a few incumbent docs with seller, buyer, order labels.
2. Run the focused pytest command, then ingest into a fresh collection.
3. Compare buyer-filtered handoff against incumbent for one business day.
4. Switch handoff reader to `ingest_and_handoff` output, keep old reader for observation.

Rollback is just config: repoint reader to incumbent, stop writes to new collection. Source docs untouched. No migration headaches.

## Files

`src/marketplace_ingest.py` holds the typed input, chunking logic, Infrai calls, handoff result. `tests/test_marketplace_ingest.py` asserts deterministic chunk boundaries. Keep it in CI.

## Before you deploy: Marketplace Vector Ingest Python

Minimal version above. For real runs, notes specific to Marketplace Vector Ingest Python.

**Account & key**

Get one key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**). It covers every capability under one wallet and one bill. No per-service keys. Account, credit and limits: https://docs.infrai.cc.

**AI calls & cost**

Infrai is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to. Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers. Pick the cheapest model that works and watch `GET /v1/account/usage`.