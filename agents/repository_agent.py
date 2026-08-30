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

2. `read_file`: Read line-numbered code from a file.
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

8. `final_answer`: Output the final evidence-backed explanation when enough information has been gathered.
   Action Input: {
       "explanation": "Detailed explanation of the findings...",
       "execution_path": "WSGI -> function_a() -> function_b()",
       "files_examined": ["file1.py", "file2.py"],
       "symbols_examined": ["function_a", "function_b"]
   }
"""


class RepositoryAgent:
    def __init__(self, repo_name: str, max_iterations: int = 6):
        self.repo_name = repo_name
        self.max_iterations = max_iterations
        self.examined_files = set()
        self.examined_symbols = set()
        self.evidence_log = []

    def _execute_tool(self, action: str, action_input: Dict[str, Any]) -> Any:
        action_input = action_input or {}
        
        if action == "search_code":
            query = action_input.get("query", "")
            return search_code(query)
            
        elif action == "read_file":
            file_path = action_input.get("file_path", "")
            start_line = int(action_input.get("start_line", 1))
            max_lines = int(action_input.get("max_lines", 100))
            if file_path:
                self.examined_files.add(file_path)
            return read_file(file_path, start_line, max_lines)
            
        elif action == "inspect_symbol":
            symbol_name = action_input.get("symbol_name", "")
            if symbol_name:
                self.examined_symbols.add(symbol_name)
            return inspect_symbol(self.repo_name, symbol_name)
            
        elif action == "find_callers":
            func_name = action_input.get("function_name", "")
            if func_name:
                self.examined_symbols.add(func_name)
            return find_callers(self.repo_name, func_name)
            
        elif action == "find_callees":
            func_name = action_input.get("function_name", "")
            if func_name:
                self.examined_symbols.add(func_name)
            return find_callees(self.repo_name, func_name)
            
        elif action == "find_dependencies":
            file_path = action_input.get("file_path", None)
            if file_path:
                self.examined_files.add(file_path)
            return find_dependencies(self.repo_name, file_path)
            
        elif action == "list_repository":
            return list_repository(self.repo_name)
            
        else:
            return {"error": f"Unknown action: '{action}'."}

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extracts JSON object from model output."""
        try:
            # First try direct parse
            return json.loads(text.strip())
        except Exception:
            pass

        # Try regex extract from markdown blocks or raw text
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except Exception:
                pass

        # Find first { and matching }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end+1].strip())
            except Exception:
                pass

        return None

    def run(self, question: str) -> Dict[str, Any]:
        """Executes the agentic investigation loop."""
        history_prompt = ""
        
        for iteration in range(1, self.max_iterations + 1):
            prompt = f"""
You are RepoTalk, an explainable Repository Intelligence Agent investigating the repository '{self.repo_name}'.
Your goal is to answer the user's question with repository evidence by iteratively selecting tools.

Target Repository: {self.repo_name}
User Question: {question}

{TOOL_DESCRIPTIONS}

Investigation History & Observations:
{history_prompt if history_prompt else "No actions taken yet."}

You MUST respond strictly with a SINGLE valid JSON object in the following format:
{{
  "thought": "Explain your reasoning for this step...",
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
                    "evidence_log": self.evidence_log
                }

            parsed_response = self._extract_json(llm_response)

            if not parsed_response or "action" not in parsed_response:
                # If parsing failed, retry with feedback
                history_prompt += f"\n[Iteration {iteration}]\nModel Raw Output: {llm_response[:300]}\nSystem Error: Could not parse response as valid JSON with 'action' and 'action_input'. Please respond strictly in JSON format.\n"
                continue


            thought = parsed_response.get("thought", "")
            action = parsed_response.get("action", "")
            action_input = parsed_response.get("action_input", {})

            self.evidence_log.append({
                "iteration": iteration,
                "thought": thought,
                "action": action,
                "action_input": action_input
            })

            if action == "final_answer":
                explanation = action_input.get("explanation", llm_response)
                execution_path = action_input.get("execution_path", "N/A")
                files_examined = action_input.get("files_examined", list(self.examined_files))
                symbols_examined = action_input.get("symbols_examined", list(self.examined_symbols))

                return {
                    "question": question,
                    "answer": explanation,
                    "execution_path": execution_path,
                    "files_examined": files_examined,
                    "symbols_examined": symbols_examined,
                    "iterations_used": iteration,
                    "evidence_log": self.evidence_log
                }

            # Execute selected tool
            tool_output = self._execute_tool(action, action_input)
            
            # Format observation for history
            output_snippet = str(tool_output)
            if len(output_snippet) > 1500:
                output_snippet = output_snippet[:1500] + "... [truncated]"

            history_prompt += f"""
[Iteration {iteration}]
Thought: {thought}
Action: {action}
Action Input: {json.dumps(action_input)}
Observation: {output_snippet}
"""

        # If max iterations reached, synthesize final answer
        synthesis_prompt = f"""
You are RepoTalk Repository Intelligence Agent. You reached the maximum investigation limit.
Synthesize your findings so far to answer the question with evidence.

User Question: {question}
Inspected Files: {list(self.examined_files)}
Inspected Symbols: {list(self.examined_symbols)}

Investigation History:
{history_prompt}

Provide a comprehensive, evidence-backed answer with an execution path if applicable.
"""
        final_synth = ask_mistral(synthesis_prompt)
        return {
            "question": question,
            "answer": final_synth,
            "execution_path": "Reconstructed from multi-step investigation",
            "files_examined": list(self.examined_files),
            "symbols_examined": list(self.examined_symbols),
            "iterations_used": self.max_iterations,
            "evidence_log": self.evidence_log
        }
