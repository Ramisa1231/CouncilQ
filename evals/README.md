# Evals

CouncilQ uses evals for the single advanced RAG pipeline.

## Answer Evals

`answer_cases.json` validates route decisions, source citations, policy decisions, and forbidden content.

Run:

```powershell
python -m evals.harness
```

The harness reports deterministic contract metrics for routing accuracy, labelled
policy-decision accuracy, citation validity, required-content coverage, and
forbidden-content avoidance. These are not LLM faithfulness or hallucination metrics.

## Policy Evals

`policy_cases.json` contains labelled prompt-injection, benign-negative, and PII
redaction cases.

Run:

```powershell
python -m evals.policy_harness
```

The harness reports confusion matrices, precision, recall, and false-positive rates.
Results apply only to the checked-in fixture and must not be generalized to production
traffic.

## Retrieval Evals

`retrieval_cases.json` validates retrieval quality with `Recall@k`, `MRR@k`, and binary `nDCG@k`.

Run:

```powershell
python -m scripts.eval_retrieval
```

The checked-in retrieval cases currently exercise trusted-source seed routing. A
dense/lexical/hybrid ablation is intentionally not reported because the repository
does not contain a versioned production-like document corpus and labelled chunk-level
benchmark sufficient to support that comparison.

## Trajectory Evals

`tests/test_trajectory_evals.py` contains deterministic LangChain AgentEvals-style trajectory checks for the ADK workflow. These follow the trajectory-match approach from the LangChain docs: compare the actual workflow sequence with a reference trajectory when expected ordering is known.

- policy blocks unsafe requests before retrieval runs
- out-of-scope council questions ask for clarification before source retrieval
- missing-address bin collection questions route to clarification with the official checker source

Run:

```powershell
pytest tests/test_trajectory_evals.py
```
