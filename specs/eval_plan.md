# Evaluation Plan

## Evaluation Principles

- Write evals before implementation.
- Treat evals as the functional contract for retrieval and answer behavior.
- Use pytest for deterministic code behavior, not natural-language response quality.
- Keep retrieval benchmarks offline and reproducible.

## Retrieval Evals

Retrieval evals live in `evals/retrieval_cases.json` and run through:

```powershell
python -m scripts.eval_retrieval
```

They must cover:

- Required source URLs in top-k.
- Required PDF page or chunk IDs when applicable.
- Forbidden sources never appearing.
- `Recall@k`, `MRR@k`, and binary `nDCG@k`.

## Answer Evals

Answer evals live in `evals/answer_cases.json` and run through:

```powershell
python -m evals.harness
```

They must cover:

- Supported waste question with enough context.
- Missing-address or missing-location clarification.
- Missed-bin report guidance without automatic submission.
- Hard-waste guidance with source citation.
- Which-bin source use.
- Prompt injection embedded in user text.
- Unsupported council or non-Adelaide request.

## Acceptance Criteria

- All JSON eval files are valid.
- Deterministic tests pass.
- Answer evals pass.
- Retrieval benchmark passes at the configured threshold.
