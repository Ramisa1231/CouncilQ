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

## Trajectory Evals

`tests/test_trajectory_evals.py` contains deterministic LangChain-style trajectory checks for the ADK workflow:

- policy blocks unsafe requests before retrieval runs
- out-of-scope council questions ask for clarification before source retrieval
- missing-address bin collection questions route to clarification with the official checker source

Run:

```powershell
pytest tests/test_trajectory_evals.py
```
