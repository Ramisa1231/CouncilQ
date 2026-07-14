# Evals

CouncilQ uses evals for the single advanced RAG pipeline.

## Answer Evals

`answer_cases.json` validates route decisions, source citations, policy decisions, and forbidden content.

Run:

```powershell
python -m evals.harness
```

## Retrieval Evals

`retrieval_cases.json` validates retrieval quality with `Recall@k`, `MRR@k`, and binary `nDCG@k`.

Run:

```powershell
python -m scripts.eval_retrieval
```
