import json
import re
from typing import Dict, Any, List, Optional

from backend.services.llm_service import ask_mistral

from agents.tools import (
    list_repository,
    search_code,
    read_file,
    inspect_symbol,
    find_callers,
    find_callees,
    find_dependencies
)


TOOL_DESCRIPTIONS = """
Available Tools:

1. `search_code`
   Search semantic vectors ONLY inside the target repository.

   Action Input:
   {
       "query": "search query string",
       "top_k": 5
   }

2. `read_file`
   Read source code ONLY from the target repository.
   Use this when exact source lines are required.

   Action Input:
   {
       "file_path": "path/to/file.py",
       "start_line": 1,
       "max_lines": 100
   }

3. `inspect_symbol`
   Find function or class definitions ONLY inside the target repository.

   Action Input:
   {
       "symbol_name": "function_or_class_name"
   }

4. `find_callers`
   Find functions that call a target function ONLY inside the target repository.

   Action Input:
   {
       "function_name": "target_function_name"
   }

5. `find_callees`
   Find functions called by a target function ONLY inside the target repository.

   Action Input:
   {
       "function_name": "target_function_name"
   }

6. `find_dependencies`
   Find import dependencies ONLY inside the target repository.

   Action Input:
   {
       "file_path": "optional/path/to/file.py"
   }

7. `list_repository`
   Get the structural overview of ONLY the target repository.

   Action Input:
   {}

8. `final_answer`
   Return the final evidence-backed explanation when enough evidence
   has been collected.

   Action Input:
   {
       "explanation": "Clear explanation citing exact file:line references.",
       "execution_flow": "Step1 -> Step2 -> Step3",
       "evidence_citations": [
           "file.py:10-45 (symbol_name)",
           "file2.py:50-80"
       ]
   }
"""


class RepositoryAgent:

    def __init__(
        self,
        repo_name: str,
        max_iterations: int = 6
    ):
        self.repo_name = repo_name
        self.max_iterations = max_iterations

        self.examined_files = set()
        self.examined_symbols = set()

        self.execution_trace = []
        self.structured_steps = []
        self.evidence_sources = []

    # =========================================================
    # Helpers
    # =========================================================

    def _normalize_string(
        self,
        value: Any
    ) -> Optional[str]:

        """
        Convert an LLM-generated value into a safe string.

        Mistral may occasionally return:

            "parse_python_file"

        or:

            ["parse_python_file"]

        This prevents lists from being inserted into sets or
        passed unexpectedly into repository tools.
        """

        if value is None:
            return None

        if isinstance(value, str):

            value = value.strip()

            return value if value else None

        if isinstance(value, list):

            if not value:
                return None

            for item in value:

                if isinstance(item, str) and item.strip():
                    return item.strip()

            return None

        return str(value).strip() or None

    def _normalize_file_path(
        self,
        value: Any
    ) -> Optional[str]:

        return self._normalize_string(value)

    def _tool_already_used(
        self,
        action: str
    ) -> bool:

        return action in self.execution_trace

    def _add_evidence(
        self,
        evidence: Dict[str, Any]
    ) -> None:

        if evidence not in self.evidence_sources:
            self.evidence_sources.append(evidence)

    # =========================================================
    # Tool Execution
    # =========================================================

    def _execute_tool(
        self,
        action: str,
        action_input: Dict[str, Any]
    ) -> Any:

        action_input = action_input or {}

        # -----------------------------------------------------
        # search_code
        # -----------------------------------------------------

        if action == "search_code":

            query = self._normalize_string(
                action_input.get("query")
            )

            if not query:
                return {
                    "error": "search_code requires a valid query."
                }

            try:

                top_k = int(
                    action_input.get("top_k", 5)
                )

            except (TypeError, ValueError):

                top_k = 5

            top_k = max(1, min(top_k, 10))

            res = search_code(
                self.repo_name,
                query,
                top_k
            )

            if isinstance(res, list):

                for item in res:

                    if not isinstance(item, dict):
                        continue

                    file_path = item.get("file")

                    if file_path:

                        self.examined_files.add(
                            file_path
                        )

                        self._add_evidence({
                            "type": "semantic_chunk",
                            "file": file_path,
                            "repo_name": self.repo_name,
                            "score": item.get("score")
                        })

            return res

        # -----------------------------------------------------
        # read_file
        # -----------------------------------------------------

        elif action == "read_file":

            file_path = self._normalize_file_path(
                action_input.get("file_path")
            )

            if not file_path:
                return {
                    "error": "read_file requires a valid file_path."
                }

            try:

                start_line = int(
                    action_input.get(
                        "start_line",
                        1
                    )
                )

            except (TypeError, ValueError):

                start_line = 1

            try:

                max_lines = int(
                    action_input.get(
                        "max_lines",
                        100
                    )
                )

            except (TypeError, ValueError):

                max_lines = 100

            start_line = max(
                start_line,
                1
            )

            max_lines = max(
                1,
                min(max_lines, 300)
            )

            res = read_file(
                self.repo_name,
                file_path,
                start_line,
                max_lines
            )

            if isinstance(res, dict):

                if "error" not in res:

                    self.examined_files.add(
                        file_path
                    )

                if "showing_start" in res:

                    self._add_evidence({
                        "type": "code_snippet",
                        "file": file_path,
                        "lines": (
                            f"{res['showing_start']}-"
                            f"{res['showing_end']}"
                        ),
                        "total_lines": res.get(
                            "total_lines"
                        )
                    })

            return res

        # -----------------------------------------------------
        # inspect_symbol
        # -----------------------------------------------------

        elif action == "inspect_symbol":

            symbol_name = self._normalize_string(
                action_input.get("symbol_name")
            )

            if not symbol_name:

                return {
                    "error": (
                        "inspect_symbol requires a valid "
                        "symbol_name."
                    )
                }

            self.examined_symbols.add(
                symbol_name
            )

            res = inspect_symbol(
                self.repo_name,
                symbol_name
            )

            if isinstance(res, dict):

                definitions = res.get(
                    "definitions",
                    []
                )

                for definition in definitions:

                    if not isinstance(
                        definition,
                        dict
                    ):
                        continue

                    file_path = definition.get(
                        "file"
                    )

                    if file_path:

                        self.examined_files.add(
                            file_path
                        )

                        self._add_evidence({
                            "type": "ast_declaration",
                            "symbol": symbol_name,
                            "kind": definition.get(
                                "type"
                            ),
                            "file": file_path
                        })

            return res

        # -----------------------------------------------------
        # find_callers
        # -----------------------------------------------------

        elif action == "find_callers":

            function_name = self._normalize_string(
                action_input.get("function_name")
            )

            if not function_name:

                return {
                    "error": (
                        "find_callers requires a valid "
                        "function_name."
                    )
                }

            self.examined_symbols.add(
                function_name
            )

            res = find_callers(
                self.repo_name,
                function_name
            )

            if isinstance(res, dict):

                callers = res.get(
                    "callers",
                    []
                )

                for caller in callers:

                    if not isinstance(
                        caller,
                        dict
                    ):
                        continue

                    file_path = caller.get(
                        "file"
                    )

                    caller_function = caller.get(
                        "caller_function"
                    )

                    if file_path:

                        self.examined_files.add(
                            file_path
                        )

                    if caller_function:

                        self.examined_symbols.add(
                            str(caller_function)
                        )

                    self._add_evidence({
                        "type": "call_chain",
                        "caller": caller_function,
                        "target": function_name,
                        "file": file_path
                    })

            return res

        # -----------------------------------------------------
        # find_callees
        # -----------------------------------------------------

        elif action == "find_callees":

            function_name = self._normalize_string(
                action_input.get("function_name")
            )

            if not function_name:

                return {
                    "error": (
                        "find_callees requires a valid "
                        "function_name."
                    )
                }

            self.examined_symbols.add(
                function_name
            )

            res = find_callees(
                self.repo_name,
                function_name
            )

            if isinstance(res, dict):

                callees = res.get(
                    "callees",
                    []
                )

                for callee in callees:

                    if not isinstance(
                        callee,
                        dict
                    ):
                        continue

                    file_path = callee.get(
                        "file"
                    )

                    callee_function = callee.get(
                        "callee_function"
                    )

                    if file_path:

                        self.examined_files.add(
                            file_path
                        )

                    if callee_function:

                        self.examined_symbols.add(
                            str(callee_function)
                        )

                    self._add_evidence({
                        "type": "call_chain",
                        "caller": function_name,
                        "target": callee_function,
                        "file": file_path
                    })

            return res

        # -----------------------------------------------------
        # find_dependencies
        # -----------------------------------------------------

        elif action == "find_dependencies":

            file_path = self._normalize_file_path(
                action_input.get("file_path")
            )

            if file_path:

                self.examined_files.add(
                    file_path
                )

            res = find_dependencies(
                self.repo_name,
                file_path
            )

            if isinstance(res, dict):

                if "dependencies" in res:

                    self._add_evidence({
                        "type": "import_dependency",
                        "file": res.get(
                            "file",
                            file_path
                        ),
                        "dependencies": res.get(
                            "dependencies",
                            []
                        )
                    })

            return res

        # -----------------------------------------------------
        # list_repository
        # -----------------------------------------------------

        elif action == "list_repository":

            return list_repository(
                self.repo_name
            )

        # -----------------------------------------------------
        # Unknown action
        # -----------------------------------------------------

        return {
            "error": f"Unknown action: '{action}'."
        }

    # =========================================================
    # JSON Extraction
    # =========================================================

    def _extract_json(
        self,
        text: str
    ) -> Optional[Dict[str, Any]]:

        if not isinstance(text, str):
            return None

        # Direct JSON
        try:

            parsed = json.loads(
                text.strip()
            )

            if isinstance(
                parsed,
                dict
            ):
                return parsed

        except Exception:
            pass

        # JSON inside markdown block
        match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```",
            text,
            re.DOTALL
        )

        if match:

            try:

                parsed = json.loads(
                    match.group(1).strip()
                )

                if isinstance(
                    parsed,
                    dict
                ):
                    return parsed

            except Exception:
                pass

        # JSON embedded in normal text
        start = text.find("{")
        end = text.rfind("}")

        if (
            start != -1
            and end != -1
            and end > start
        ):

            try:

                parsed = json.loads(
                    text[start:end + 1]
                )

                if isinstance(
                    parsed,
                    dict
                ):
                    return parsed

            except Exception:
                pass

        return None

    # =========================================================
    # Agent Loop
    # =========================================================

    def run(
        self,
        question: str
    ) -> Dict[str, Any]:

        history_prompt = ""

        for iteration in range(
            1,
            self.max_iterations + 1
        ):

            prompt = f"""
You are RepoTalk, an explainable Repository Intelligence Agent.

You are investigating ONLY this repository:

{self.repo_name}

The user's question is:

{question}

Your job is to investigate the repository using the available
tools and provide an evidence-backed answer.

IMPORTANT RULES:

1. Investigate ONLY the target repository.

2. Never investigate unrelated repositories.

3. Never investigate the Python virtual environment.

4. Never use information from another repository.

5. Do not guess repository facts.

6. Prefer structural tools when answering structural questions.

7. Use `inspect_symbol` to locate functions/classes.

8. Use `find_callers` to determine who calls a function.

9. Use `find_callees` to determine what a function calls.

10. Use `find_dependencies` for import relationships.

11. Use `search_code` for semantic code discovery.

12. Use `list_repository` for repository structure.

13. Use `read_file` when exact source lines are required.

14. After finding a symbol with `inspect_symbol`, use `read_file`
    when the final answer needs exact line-level evidence.

15. Do not repeatedly call the same tool unless the previous
    result was insufficient.

16. Every tool call must contribute new evidence.

17. After EVERY tool result, ask yourself:

       "Do I now have enough evidence to answer the question?"

    If YES:
       immediately use `final_answer`.

    If NO:
       perform exactly ONE additional useful tool call.

18. Prefer finishing simple questions in 2-3 tool calls.

19. Multi-file questions should normally finish in 3-5 tool calls.

20. Do NOT use all available iterations just because they exist.

21. The final answer must be based ONLY on repository evidence.

22. When exact source lines are available, cite them using:
       file.py:10-25

23. Do not invent line numbers.

24. Keep the execution flow concise and evidence-based.

25. `final_answer` is always preferred over unnecessary exploration
    once sufficient evidence has been collected.

TARGET REPOSITORY:

{self.repo_name}

USER QUESTION:

{question}

{TOOL_DESCRIPTIONS}

PREVIOUS INVESTIGATION:

{history_prompt if history_prompt else "No tools have been executed yet."}

TOOLS ALREADY USED:

{self.execution_trace}

FILES ALREADY EXAMINED:

{sorted(self.examined_files)}

SYMBOLS ALREADY EXAMINED:

{sorted(self.examined_symbols)}

Respond ONLY with ONE valid JSON object.

For a tool call:

{{
    "thought": "Brief reason for selecting this tool.",
    "action": "tool_name",
    "action_input": {{ ... }}
}}

For a final answer:

{{
    "thought": "Why the available evidence is sufficient.",
    "action": "final_answer",
    "action_input": {{
        "explanation": "Evidence-backed answer.",
        "execution_flow": "Step1 -> Step2 -> Step3",
        "evidence_citations": [
            "file.py:10-25",
            "other_file.py:30-45"
        ]
    }}
}}
"""

            llm_response = ask_mistral(
                prompt
            )

            # -------------------------------------------------
            # Ollama connection error
            # -------------------------------------------------

            if (
                isinstance(
                    llm_response,
                    str
                )
                and llm_response.startswith(
                    "Ollama Connection Error"
                )
            ):

                return {
                    "error": (
                        "Failed to connect to local LLM "
                        "(Ollama). Ensure Ollama is running "
                        "on http://localhost:11434 with "
                        "model 'mistral'."
                    ),
                    "details": llm_response,
                    "question": question,
                    "execution_trace": self.execution_trace,
                    "structured_steps": self.structured_steps,
                    "evidence_sources": self.evidence_sources
                }

            # -------------------------------------------------
            # Parse JSON
            # -------------------------------------------------

            parsed_response = self._extract_json(
                llm_response
            )

            if (
                not parsed_response
                or "action" not in parsed_response
            ):

                history_prompt += f"""
[Iteration {iteration}]

Model Output:
{str(llm_response)[:800]}

System Error:
The model response was not valid JSON.

Return ONLY one valid JSON object using the required format.
"""

                continue

            thought = parsed_response.get(
                "thought",
                ""
            )

            action = self._normalize_string(
                parsed_response.get(
                    "action"
                )
            )

            action_input = parsed_response.get(
                "action_input",
                {}
            )

            if not isinstance(
                action_input,
                dict
            ):
                action_input = {}

            # -------------------------------------------------
            # Final answer
            # -------------------------------------------------

            if action == "final_answer":

                explanation = action_input.get(
                    "explanation",
                    llm_response
                )

                execution_flow = action_input.get(
                    "execution_flow"
                )

                if not execution_flow:

                    execution_flow = (
                        " -> ".join(
                            self.execution_trace
                        )
                        if self.execution_trace
                        else "Direct Evidence"
                    )

                evidence_citations = action_input.get(
                    "evidence_citations",
                    []
                )

                if not isinstance(
                    evidence_citations,
                    list
                ):

                    evidence_citations = [
                        str(evidence_citations)
                    ]

                return {
                    "question": question,
                    "answer": explanation,
                    "execution_flow": execution_flow,
                    "execution_trace": self.execution_trace,
                    "evidence_citations": evidence_citations,
                    "structured_steps": self.structured_steps,
                    "evidence_sources": self.evidence_sources,
                    "files_examined": sorted(
                        self.examined_files
                    ),
                    "symbols_examined": sorted(
                        self.examined_symbols
                    ),
                    "iterations_used": iteration
                }

            # -------------------------------------------------
            # Validate action
            # -------------------------------------------------

            valid_actions = {
                "search_code",
                "read_file",
                "inspect_symbol",
                "find_callers",
                "find_callees",
                "find_dependencies",
                "list_repository"
            }

            if action not in valid_actions:

                history_prompt += f"""
[Iteration {iteration}]

Invalid action:
{action}

Choose one valid tool or final_answer.
"""

                continue

            # -------------------------------------------------
            # Prevent unnecessary repeated calls
            # -------------------------------------------------

            if (
                self._tool_already_used(action)
                and action in {
                    "list_repository",
                    "find_dependencies"
                }
            ):

                history_prompt += f"""
[Iteration {iteration}]

The tool `{action}` was already used.

Do not repeat it unless new input is required.
Choose another useful tool or final_answer.
"""

                continue

            # -------------------------------------------------
            # Record execution
            # -------------------------------------------------

            self.execution_trace.append(
                action
            )

            # -------------------------------------------------
            # Execute tool
            # -------------------------------------------------

            tool_output = self._execute_tool(
                action,
                action_input
            )

            # -------------------------------------------------
            # Prepare output summary
            # -------------------------------------------------

            output_text = str(
                tool_output
            )

            if len(output_text) > 1500:

                summary = (
                    output_text[:500]
                    + "... [truncated]"
                )

                observation = (
                    output_text[:1500]
                    + "... [truncated]"
                )

            else:

                summary = output_text
                observation = output_text

            # -------------------------------------------------
            # Structured step
            # -------------------------------------------------

            self.structured_steps.append({
                "step": iteration,
                "tool": action,
                "input": action_input,
                "thought": thought,
                "summary": summary
            })

            # -------------------------------------------------
            # Investigation history
            # -------------------------------------------------

            try:

                serialized_input = json.dumps(
                    action_input
                )

            except Exception:

                serialized_input = str(
                    action_input
                )

            history_prompt += f"""
[Iteration {iteration}]

Thought:
{thought}

Action:
{action}

Action Input:
{serialized_input}

Observation:
{observation}
"""

        # =====================================================
        # Maximum Iterations Reached
        # =====================================================

        synthesis_prompt = f"""
You are RepoTalk, an explainable Repository Intelligence Agent.

The investigation has reached the maximum number of iterations.

Target repository:

{self.repo_name}

User question:

{question}

You MUST synthesize an answer using ONLY the investigation
observations below.

Do not invent repository facts.

Do not claim evidence that was not observed.

Use exact file names and line ranges when they are available.

If exact line numbers are unavailable, cite the file and symbol
instead of inventing line numbers.

Investigation Trace:

{history_prompt}

Execution Trace:

{self.execution_trace}

Files Examined:

{sorted(self.examined_files)}

Symbols Examined:

{sorted(self.examined_symbols)}

Evidence Sources:

{self.evidence_sources}

Return a clear final answer containing:

1. Answer
2. Execution Flow
3. Evidence
4. Relevant Files
5. Relevant Symbols

Keep the answer concise but technically accurate.
"""

        final_synthesis = ask_mistral(
            synthesis_prompt
        )

        return {
            "question": question,
            "answer": final_synthesis,
            "execution_flow": (
                " -> ".join(
                    self.execution_trace
                )
                if self.execution_trace
                else "No tool execution"
            ),
            "execution_trace": self.execution_trace,
            "structured_steps": self.structured_steps,
            "evidence_sources": self.evidence_sources,
            "files_examined": sorted(
                self.examined_files
            ),
            "symbols_examined": sorted(
                self.examined_symbols
            ),
            "iterations_used": self.max_iterations
        }