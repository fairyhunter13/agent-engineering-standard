---
name: rag-and-llm-evaluation
description: Measure retrieval quality and generation faithfulness in RAG systems to catch regressions before users do.
discipline: data
tags: [ai, rag, llm, evaluation, metrics]
---

# RAG and LLM Evaluation

## When to use
Building a Retrieval-Augmented Generation pipeline; evaluating whether a change to chunking, embedding model, or prompt improves output quality; measuring the effect of adding a reranker.
Apply this before any RAG system goes to production and as a regression gate in CI for any change to the retrieval or generation components.

## Signal
- Users report that the RAG system gives factually wrong answers or cites the wrong source.
- The system hallucinates facts not present in the retrieved context.
- There is no quantitative metric for retrieval quality — the only evaluation is qualitative spot-checking.
- A change to the chunking strategy or embedding model is deployed without any before/after comparison.
- Faithfulness (does the answer follow from the retrieved context?) is not measured at all.
- Retrieval recall is never tested — no one knows whether the right documents are being retrieved.

## Why
LLMs hallucinate even when given correct context; RAG reduces but does not eliminate hallucination.
RAG quality has two independent failure modes: retrieval failure (the right chunk is not returned) and generation failure (the model ignores or contradicts the returned chunk).
Without metrics, you cannot distinguish between these failure modes, cannot tell if a change helped, and cannot detect regressions when a dependency changes (embedding model update, prompt rewrite).
An evaluation set of golden examples is the only ground truth you have; without it you are flying blind.

## Remediate
1. **Retrieval metrics — build first**: for a set of golden (query, relevant_chunk_ids) pairs, measure:
   - **Recall@k**: fraction of relevant chunks appearing in the top-k retrieved results. Target Recall@5 ≥ 0.80 for a focused knowledge base.
   - **MRR (Mean Reciprocal Rank)**: average of 1/rank of the first relevant result. Captures how high in the list the answer appears.
   - **Precision@5**: fraction of top-5 results that are actually relevant. Use when false positives cause hallucination.
2. **Generation metrics — measure faithfulness separately from relevance**:
   - **Faithfulness**: does every claim in the answer appear in the retrieved context? Use RAGAS or an LLM-judge prompt: "Given context C, does answer A contain only information present in C?"
   - **Answer Relevance**: does the answer address the question asked? A faithful but off-topic answer is still a failure.
   - **Citation Coverage**: if the system cites sources, what fraction of citations are correct?
3. **Build a golden evaluation set**: assemble ≥50 (query, expected_answer, relevant_chunk_ids) triples. Include edge cases: queries at the boundary of the knowledge base, multi-hop questions, adversarial queries. Run this suite nightly; alert on metric regression.
4. **Reranker evaluation**: if adding a reranker (Cohere Rerank, cross-encoder), compare Recall@5 and NDCG before and after. A reranker should increase precision in the top positions; verify this on your specific domain, not on generic benchmarks.
5. **Alert on regression**: define thresholds (Faithfulness < 0.75, Recall@5 < 0.70) and block deploys that break them, treating them the same as a failing unit test. Log per-query evaluation results to a time-series store for trend analysis.

## References
- RAGAS: RAG Assessment framework (ragas.io)
- MTEB Benchmark: Massive Text Embedding Benchmark for embedding model comparison
- "Evaluating RAG Systems" — LlamaIndex documentation
- Anthropic documentation: building LLM-judges for evaluation
- BEIR Benchmark: retrieval evaluation across heterogeneous tasks
