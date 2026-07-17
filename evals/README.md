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

## LlamaIndex-Style Judge Evals

`judge_cases.json` validates a second response-evaluation layer inspired by the LlamaIndex evaluation dimensions:

- faithfulness: the answer should not introduce unsupported or forbidden claims
- context relevancy: returned sources should match the expected council context
- answer relevancy: the answer should contain required response content for the query
- guideline adherence: the answer should follow CouncilQ rules such as official citations, address clarification, prompt-injection sanitization, and City of Adelaide scope

The default judge implementation is deterministic and offline; it does not require a live LLM judge.

Run:

```powershell
python -m evals.judge
```

## Trajectory Evals

`tests/test_trajectory_evals.py` contains deterministic LangChain AgentEvals-style trajectory checks for the ADK workflow. These follow the trajectory-match approach from the LangChain docs: compare the actual workflow sequence with a reference trajectory when expected ordering is known.

- policy blocks unsafe requests before retrieval runs
- out-of-scope council questions ask for clarification before source retrieval
- missing-address bin collection questions route to clarification with the official checker source

Run:

```powershell
pytest tests/test_trajectory_evals.py
```
