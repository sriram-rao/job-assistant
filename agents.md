General:

- Always respond concisely.
- Use bullet style or short sentences where possible.
- Avoid repetition.

Coding:

- Output only the minimal working snippet.
- Keep functions short, modular, and focused.
- Explanations: 1–3 sentences max.
- No redundant comments or boilerplate.
- Show alternatives compactly if needed.
- DO NOT USE SINGLE UNDERSCORE _METHODS.
- NO INLINE IMPORTS.

Documentation:

- Be clear and concise; no filler.
- Use bullet lists, short sections, and direct examples.
- Prioritize functional clarity over style.
- Limit explanations to what is necessary for use.
- Keep responses compact to minimize output size.

Recent operations:

- Refactored assistant.py to ensure all Optional[T] usages use modern union syntax T | None and removed any unused typing.Optional imports. Verified with diagnostics; no remaining Optional references in this file.
- Added precise type annotations in assistant.py (LLMData TypedDict usage, parameterized dict types, guard for self.llm) and resolved diagnostics warnings.
- Implemented DummyLLM and DUMMY_LLM singleton in ml/llm.py as a no-op LLM default conforming to the LLM protocol.
- Updated Assistant to require llm: LLM (non-optional) with DUMMY_LLM as the default; removed None checks in ask().
- Modernized ml/llm.py typing (| None unions, collections.abc types, overloads for to_request) and aligned parameter names to satisfy structural typing.
- Ran diagnostics on modified files; no type errors (only warnings for unused parameters in DummyLLM, intentional).
