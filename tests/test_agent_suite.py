import sys
import os
import json

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.repository_agent import RepositoryAgent


TEST_CASES = [
    {
        "category": "Architecture",
        "question": "How is the RepoTalk backend application structured?"
    },
    {
        "category": "Execution Flow",
        "question": "How does the parse-repo endpoint process files and build the dependency graph?"
    },
    {
        "category": "Symbol Tracing",
        "question": "Where is parse_python_file defined and which functions call it?"
    },
    {
        "category": "Dependency Analysis",
        "question": "What modules does backend/routes/repo.py depend on?"
    },
    {
        "category": "Cross-File Reasoning",
        "question": "How does a request to /ask travel from repo.py to llm_service.py?"
    },
    {
        "category": "Semantic Inquiry",
        "question": "Where is semantic search implemented and how are vector embeddings indexed?"
    }
]


def run_benchmark():
    print("=" * 70)
    print("[REPOTALK AGENT RELIABILITY & EVIDENCE SUITE]")
    print("=" * 70)

    results = []

    for idx, test in enumerate(TEST_CASES, 1):
        category = test["category"]
        question = test["question"]

        print(f"\n[{idx}/6] Category: {category}")
        print(f"Question: \"{question}\"")
        print("-" * 50)

        agent = RepositoryAgent(repo_name=".", max_iterations=5)
        res = agent.run(question)

        if "error" in res:
            print(f"[FAIL] Error: {res['error']}")
            results.append({
                "category": category,
                "status": "FAILED",
                "error": res["error"]
            })
            continue

        exec_trace = res.get("execution_trace", [])
        steps = res.get("structured_steps", [])
        evidence_sources = res.get("evidence_sources", [])
        files_examined = res.get("files_examined", [])
        symbols_examined = res.get("symbols_examined", [])
        iterations = res.get("iterations_used", 0)

        print(f"[OK] Iterations Used: {iterations}")
        print(f"  Execution Trace: {exec_trace}")
        print(f"  Files Examined: {files_examined}")
        print(f"  Symbols Examined: {symbols_examined}")
        print(f"  Evidence Sources Count: {len(evidence_sources)}")

        # Validation Checks
        has_tools = len(exec_trace) > 0
        has_sources = len(evidence_sources) > 0
        has_files = len(files_examined) > 0

        passed = has_tools and (has_sources or has_files)

        results.append({
            "category": category,
            "question": question,
            "status": "PASSED" if passed else "NEEDS_IMPROVEMENT",
            "iterations": iterations,
            "execution_trace": exec_trace,
            "files_examined_count": len(files_examined),
            "symbols_examined_count": len(symbols_examined),
            "evidence_sources_count": len(evidence_sources)
        })

    print("\n" + "=" * 70)
    print("[BENCHMARK SUMMARY]")
    print("=" * 70)
    print(json.dumps(results, indent=2))
    return results



if __name__ == "__main__":
    run_benchmark()
