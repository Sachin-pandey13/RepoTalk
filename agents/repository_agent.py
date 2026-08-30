import json
import re
from typing import Dict, Any, List
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
1. `search_code`: Search indexed repository vectors semantically.
   Action Input: {"query": "search query string"}

2. `read_file`: Read line-numbered source code from a file.
   Action Input: {"file_path": "path/to/file.py", "start_line": 1, "max_lines": 100}

3. `inspect_symbol`: Find function or class definitions across repository AST.
   Action Input: {"symbol_name": "function_or_class_name"}

4. `find_callers`: Find functions that call a target function.
   Action Input: {"function_name": "target_function_name"}

5. `find_callees`: Find functions called by a target function.
   Action Input: {"function_name": "target_function_name"}

6. `find_dependencies`: Find import dependencies for a file or entire repository.
   Action Input: {"file_path": "optional/path/to/file.py"}

7. `list_repository`: Get structural overview of files in the repository.
   Action Input: {}

8. `final_answer`: Output the final evidence-backed explanation when you have gathered sufficient information (do NOT needlessly run more tool steps).
   Action Input: {
       "explanation": "Clear, detailed explanation citing exact file:line references and symbols...",
       "execution_flow": "Step1 -> Step2 -> Step3",
       "evidence_citations": ["file.py:10-45 (symbol_name)", "file2.py:50-80"]
   }
"""


class RepositoryAgent:
    def __init__(self, repo_name: str, max_iterations: int = 6):
        self.repo_name = repo_name
        self.max_iterations = max_iterations
        self.examined_files = set()
        self.examined_symbols = set()
        self.execution_trace = []
        self.structured_steps = []
        self.evidence_sources = []

    def _execute_tool(self, action: str, action_input: Dict[str, Any]) -> Any:
        action_input = action_input or {}
        
        if action == "search_code":
            query = action_input.get("query", "")
            res = search_code(query)
            if isinstance(res, list):
                for item in res:
                    if isinstance(item, dict) and "file" in item:
                        self.examined_files.add(item["file"])
                        self.evidence_sources.append({
                            "type": "semantic_chunk",
                            "file": item["file"],
                            "score": item.get("score")
                        })
            return res
            
        elif action == "read_file":
            file_path = action_input.get("file_path", "")
            start_line = int(action_input.get("start_line", 1))
            max_lines = int(action_input.get("max_lines", 100))
            if file_path:
                self.examined_files.add(file_path)
            res = read_file(file_path, start_line, max_lines)
            if isinstance(res, dict) and "showing_start" in res:
                self.evidence_sources.append({
                    "type": "code_snippet",
                    "file": file_path,
                    "lines": f"{res['showing_start']}-{res['showing_end']}",
                    "total_lines": res.get("total_lines")
                })
            return res
            
        elif action == "inspect_symbol":
            symbol_name = action_input.get("symbol_name", "")
            if symbol_name:
                self.examined_symbols.add(symbol_name)
            res = inspect_symbol(self.repo_name, symbol_name)
            if isinstance(res, dict) and "definitions" in res:
                for defn in res["definitions"]:
                    self.examined_files.add(defn["file"])
                    self.evidence_sources.append({
                        "type": "ast_declaration",
                        "symbol": symbol_name,
                        "kind": defn.get("type"),
                        "file": defn.get("file")
                    })
            return res
            
        elif action == "find_callers":
            func_name = action_input.get("function_name", "")
            if func_name:
                self.examined_symbols.add(func_name)
            res = find_callers(self.repo_name, func_name)
            if isinstance(res, dict) and "callers" in res:
                for caller in res["callers"]:
                    self.examined_files.add(caller["file"])
                    self.examined_symbols.add(caller["caller_function"])
                    self.evidence_sources.append({
                        "type": "call_chain",
                        "caller": caller["caller_function"],
                        "target": func_name,
                        "file": caller["file"]
                    })
            return res
            
        elif action == "find_callees":
            func_name = action_input.get("function_name", "")
            if func_name:
                self.examined_symbols.add(func_name)
            res = find_callees(self.repo_name, func_name)
            if isinstance(res, dict) and "callees" in res:
                for callee in res["callees"]:
                    self.examined_files.add(callee["file"])
                    self.examined_symbols.add(callee["callee_function"])
                    self.evidence_sources.append({
                        "type": "call_chain",
                        "caller": func_name,
                        "target": callee["callee_function"],
                        "file": callee["file"]
                    })
            return res
            
        elif action == "find_dependencies":
            file_path = action_input.get("file_path", None)
            if file_path:
                self.examined_files.add(file_path)
            res = find_dependencies(self.repo_name, file_path)
            if isinstance(res, dict) and "dependencies" in res:
                self.evidence_sources.append({
                    "type": "import_dependency",
                    "file": res.get("file", file_path),
                    "dependencies": res.get("dependencies", [])
                })
            return res
            
        elif action == "list_repository":
            return list_repository(self.repo_name)
            
        else:
            return {"error": f"Unknown action: '{action}'."}

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extracts JSON object from model output."""
        try:
            return json.loads(text.strip())
        except Exception:
            pass

        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except Exception:
                pass

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end+1].strip())
            except Exception:
                pass

        return None

    def run(self, question: str) -> Dict[str, Any]:
        """Executes the agentic investigation loop with hardened trace & evidence collection."""
        history_prompt = ""
        
        for iteration in range(1, self.max_iterations + 1):
            prompt = f"""
You are RepoTalk, an explainable Repository Intelligence Agent investigating '{self.repo_name}'.
Your goal is to answer the user's question with direct repository evidence by selecting structural tools.

Target Repository: {self.repo_name}
User Question: {question}

{TOOL_DESCRIPTIONS}

Investigation History & Observations:
{history_prompt if history_prompt else "No actions taken yet."}

Respond ONLY with a SINGLE valid JSON object in the following format:
{{
  "thought": "Explain why you are choosing this tool step...",
  "action": "tool_name_or_final_answer",
  "action_input": {{ ... }}
}}
"""
            llm_response = ask_mistral(prompt)

            if isinstance(llm_response, str) and llm_response.startswith("Ollama Connection Error"):
                return {
                    "error": "Failed to connect to local LLM (Ollama). Ensure Ollama is running on http://localhost:11434 with model 'mistral'.",
                    "details": llm_response,
                    "question": question,
                    "execution_trace": self.execution_trace,
                    "structured_steps": self.structured_steps,
                    "evidence_sources": self.evidence_sources
                }

            parsed_response = self._extract_json(llm_response)

            if not parsed_response or "action" not in parsed_response:
                history_prompt += f"\n[Iteration {iteration}]\nModel Output: {llm_response[:300]}\nSystem Error: Response could not be parsed as JSON with 'action' and 'action_input'. Re-format as JSON.\n"
                continue

            thought = parsed_response.get("thought", "")
            action = parsed_response.get("action", "")
            action_input = parsed_response.get("action_input", {})

            if action == "final_answer":
                explanation = action_input.get("explanation", llm_response)
                execution_flow = action_input.get("execution_flow", " -> ".join(self.execution_trace) if self.execution_trace else "Direct Evidence")
                evidence_citations = action_input.get("evidence_citations", [])

                return {
                    "question": question,
                    "answer": explanation,
                    "execution_flow": execution_flow,
                    "execution_trace": self.execution_trace,
                    "evidence_citations": evidence_citations,
                    "structured_steps": self.structured_steps,
                    "evidence_sources": self.evidence_sources,
                    "files_examined": list(self.examined_files),
                    "symbols_examined": list(self.examined_symbols),
                    "iterations_used": iteration
                }

            # Record step execution
            self.execution_trace.append(action)

            # Execute selected tool
            tool_output = self._execute_tool(action, action_input)
            
            output_snippet = str(tool_output)
            if len(output_snippet) > 1200:
                summary_snippet = output_snippet[:300] + "..."
                output_snippet = output_snippet[:1200] + "... [truncated]"
            else:
                summary_snippet = output_snippet

            self.structured_steps.append({
                "step": iteration,
                "tool": action,
                "input": action_input,
                "thought": thought,
                "summary": summary_snippet
            })

            history_prompt += f"""
[Iteration {iteration}]
Thought: {thought}
Action: {action}
Action Input: {json.dumps(action_input)}
Observation: {output_snippet}
"""

        # If max iterations reached, synthesize final answer
        synthesis_prompt = f"""
You are RepoTalk Repository Intelligence Agent. You completed {self.max_iterations} investigation steps.
Synthesize your findings into a clear, evidence-backed answer. Citing exact files, line numbers, and symbols.

User Question: {question}
Inspected Files: {list(self.examined_files)}
Inspected Symbols: {list(self.examined_symbols)}

Investigation Steps & Observations:
{history_prompt}

Provide a structured final explanation with evidence citations and execution flow.
"""
        final_synth = ask_mistral(synthesis_prompt)
        return {
            "question": question,
            "answer": final_synth,
            "execution_flow": " -> ".join(self.execution_trace),
            "execution_trace": self.execution_trace,
            "structured_steps": self.structured_steps,
            "evidence_sources": self.evidence_sources,
            "files_examined": list(self.examined_files),
            "symbols_examined": list(self.examined_symbols),
            "iterations_used": self.max_iterations
        }
