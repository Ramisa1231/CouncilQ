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

The deterministic harness reports:

- Routing accuracy.
- Policy-decision accuracy where a policy outcome is labelled.
- Citation-validity rate against CouncilQ's trusted-domain and PDF-page rules.
- Required-content coverage.
- Forbidden-content avoidance.

These are contract metrics, not semantic faithfulness or hallucination scores. CouncilQ
does not claim LLM-as-a-judge results until a reviewed answer dataset and judge rubric
are checked in.

## Safety Evals

Safety evals live in `evals/policy_cases.json` and run through:

```powershell
python -m evals.policy_harness
```

The labelled fixture must include:

- Prompt-injection positives and benign negatives.
- Mixed safe-intent requests that must be sanitized rather than blocked.
- Email, Australian mobile number, and Adelaide-address redaction positives.
- Benign text that must not be redacted.

The harness reports confusion matrices, precision, recall, and false-positive rates for
prompt-injection detection and PII detection. Metrics describe only the checked-in
deterministic fixture; they are not production-traffic estimates.

## Telemetry

Runtime retrieval telemetry must include:

- A generated trace ID.
- Policy decision.
- Retrieval outcome and trusted-source count.
- End-to-end pipeline latency.

Telemetry must record sanitized input rather than the original request and must not log
model prompts, credentials, or full retrieved document text.

## Acceptance Criteria

- All JSON eval files are valid.
- Deterministic tests pass.
- Answer evals pass.
- Safety evals pass at their checked-in expected decisions.
- Retrieval benchmark passes at the configured threshold.
