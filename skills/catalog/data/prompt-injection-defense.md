---
name: prompt-injection-defense
description: Prevent user-supplied content from hijacking LLM instructions in tool-use and agentic applications.
discipline: data
tags: [ai, security, prompt-injection, llm, defense]
---

# Prompt Injection Defense

## When to use
Building LLM-powered applications that process user-supplied content (documents, emails, web pages, chat input); LLM agents with tool access; systems where the system prompt must remain confidential.
Apply this at design time for any LLM application and as an audit for existing applications before external exposure.

## Signal
- The LLM ignores system prompt instructions when a user message contains "ignore previous instructions and instead…"
- The LLM reveals system prompt contents when asked "repeat everything above."
- A tool-use agent takes unexpected actions (sends emails, deletes records) when processing user-supplied text that contains embedded instructions.
- The system can be made to output harmful content by users who embed meta-prompts in their input.
- User-supplied content is concatenated directly into the system prompt string rather than placed in the `user` turn.
- There is no validation of LLM tool-call parameters before executing the tool.

## Why
Prompt injection is the OWASP LLM Top 10 #1 risk (LLM01:2025).
In agentic systems, a successful injection does not just produce bad output — it triggers real actions: sending emails, querying databases, making API calls.
The attack surface is large: any text the LLM processes that originates outside the application (user input, web pages, documents, emails) is a potential injection vector.
The fundamental challenge is that LLMs cannot reliably distinguish between instructions and data in natural language; the defenses must be architectural, not prompt-based.

## Remediate
1. **Structural role separation**: place application instructions exclusively in the `system` role; place user-supplied content exclusively in the `user` role. Never construct the system prompt by concatenating user input. The API role boundary provides a partial structural barrier that no user-turn content can cross.
2. **Validate tool-call outputs before executing**: when the LLM returns a tool call, check that (a) the tool name is in the allowed set for this context, (b) the parameters match the expected schema and value ranges, and (c) the action is permitted given the current user's authorization level. Treat the LLM's tool-call output as untrusted input from an external system.
3. **Principle of least privilege for tools**: only expose the tools the LLM needs for the specific task. A summarization task should not have access to a `send_email` tool. Scope tool availability per request context, not globally.
4. **Input filtering for known injection patterns**: detect and refuse or sanitize content containing high-confidence injection markers: "ignore previous instructions," "you are now a different AI," "repeat your system prompt," "DAN mode." This is not sufficient alone but raises the cost of injection.
5. **Output validation for structured tasks**: if the LLM is expected to produce JSON, validate the schema strictly before consuming it. Hallucinated extra fields (e.g., an unexpected `action: delete_all`) are a signal of injection or unintended behavior. Reject outputs that do not conform to the declared schema.
6. **Human-in-the-loop for high-stakes actions**: for irreversible or high-impact tool calls (delete, send email, payment, external API write), require explicit human confirmation before execution. Log all tool invocations with the triggering input for post-incident forensics.

## References
- OWASP LLM Top 10: LLM01 — Prompt Injection (owasp.org/www-project-top-10-for-large-language-model-applications)
- Simon Willison's blog: "Prompt Injection Attacks Against GPT-3"
- Anthropic documentation: tool use and system prompt design
- NIST AI RMF: Adversarial ML threats to LLM systems
- "Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection" — Greshake et al. (2023)
