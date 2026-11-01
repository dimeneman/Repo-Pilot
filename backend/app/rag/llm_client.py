"""
LLM Client — Google Gemini client with retry logic and deterministic local fallback.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LLMResponse:
    """Standardized response from an LLM call."""

    content: str
    model: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None


class LLMClient:
    """Manages LLM API calls with Google Gemini and resilient local fallback."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.provider = (provider or settings.LLM_PROVIDER).lower()
        self.model = model or settings.LLM_MODEL
        self.gemini_key = settings.GEMINI_API_KEY

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Execute a text generation call using Gemini with resilient local fallback."""
        # 1. Try Gemini if configured
        if self.gemini_key:
            try:
                return await self._call_gemini(prompt, system_prompt, temperature, max_tokens)
            except Exception as exc:
                logger.error(f"Gemini generation failed: {exc}. Trying fallback.")

        # 2. Fallback mock generator (allows instant local dev without requiring paid keys immediately)
        return self._generate_fallback_response(prompt, system_prompt)

    async def _call_gemini(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Invoke Gemini API with automatic candidate model fallback on rate limits (429)."""
        import asyncio
        import google.generativeai as genai

        genai.configure(api_key=self.gemini_key)

        # Primary model plus fast fallbacks if quota is exhausted (e.g. 429 on free tier)
        candidate_models = [self.model]
        for alt in ["gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest"]:
            if alt not in candidate_models:
                candidate_models.append(alt)

        last_error = None
        for model_name in candidate_models:
            try:
                system_instruction = system_prompt if system_prompt else None
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_instruction,
                    generation_config=genai.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                    ),
                )

                response = await asyncio.wait_for(
                    asyncio.to_thread(model.generate_content, prompt),
                    timeout=35.0,
                )

                text = response.text or ""
                tokens = getattr(response, "usage_metadata", None)
                token_count = getattr(tokens, "total_token_count", None) if tokens else None

                return LLMResponse(
                    content=text,
                    model=model_name,
                    tokens_used=token_count,
                    finish_reason="stop",
                )
            except Exception as exc:
                last_error = exc
                logger.warning(
                    f"Gemini call with model '{model_name}' failed ({exc}). "
                    "Trying next candidate model..."
                )

        raise last_error or RuntimeError("All Gemini candidate models failed.")

    def _generate_fallback_response(
        self,
        prompt: str,
        system_prompt: Optional[str],
    ) -> LLMResponse:
        """Dynamic local response generator when live external LLM API quota is exceeded or offline.
        
        Synthesizes an intelligent, repo-grounded answer based strictly on the retrieved
        source code chunks, specific user question, and target repository metadata.
        """
        logger.info("Using local codebase-grounded response synthesizer.")

        # 1. Extract repository name
        repo_match = re.search(r"Repository:\s*([^\n]+)", prompt)
        repo_name = repo_match.group(1).strip() if repo_match else "the codebase"

        # 2. Extract user question
        q_match = re.search(r"USER QUESTION:\s*([^\n]+(?:\n[^\n]+)*)", prompt)
        user_question = q_match.group(1).strip() if q_match else ""

        # 3. Extract structured chunks: (file_path, start_line, end_line, language, snippet)
        chunk_blocks = re.findall(
            r"### Context Chunk \d+: ([^\s(]+) \(Lines (\d+)-(\d+)\)\s*```([a-zA-Z0-9_\-]*)\n([\s\S]*?)\n```",
            prompt,
        )

        # Fallback regex if formatting differs
        if not chunk_blocks:
            simple_matches = re.findall(r"Context Chunk \d+: ([^\s(]+) \(Lines (\d+)-(\d+)\)", prompt)
            chunk_blocks = [(p, s, e, "text", "") for p, s, e in simple_matches]

        citations: list[str] = []
        detected_imports: set[str] = set()
        detected_classes: list[tuple[str, str, str]] = []  # (class_name, file, line)
        detected_funcs: list[tuple[str, str, str]] = []    # (func_name, file, line)
        files_involved: list[str] = []

        standard_py_builtins = {
            "os", "sys", "time", "re", "json", "math", "typing", "collections",
            "datetime", "pathlib", "io", "contextlib", "logging", "asyncio", "functools",
            "dataclasses", "uuid", "shutil", "enum", "abc", "unittest"
        }

        for path, start, end, lang, snippet in chunk_blocks:
            citations.append(f"`[FILE:{path}:L{start}-L{end}]`")
            if path not in files_involved:
                files_involved.append(path)

            if snippet:
                # Detect imports
                py_imports = re.findall(r"^(?:import|from)\s+([a-zA-Z0-9_]+)", snippet, re.MULTILINE)
                for imp in py_imports:
                    if imp not in standard_py_builtins:
                        detected_imports.add(imp)

                # Detect classes and functions
                cls_matches = re.findall(r"^class\s+([a-zA-Z0-9_]+)", snippet, re.MULTILINE)
                for c in cls_matches:
                    detected_classes.append((c, path, start))

                fn_matches = re.findall(r"^(?:async\s+)?def\s+([a-zA-Z0-9_]+)", snippet, re.MULTILINE)
                for f in fn_matches:
                    detected_funcs.append((f, path, start))

        q_lower = user_question.lower()
        is_file_list_query = any(k in q_lower for k in ["list all", "all the file", "file names", "what files", "list files", "files in this repo", "files of this repo", "all files"])
        is_tech_stack_query = any(k in q_lower for k in ["tech stack", "technolog", "framework", "librar", "package", "dependenc", "stack"])
        is_architecture_query = any(k in q_lower for k in ["architecture", "flowchart", "diagram", "component", "workflow"])
        is_summary_query = any(k in q_lower for k in ["summary", "overview", "what does this project do", "what is this repository"])

        # Extract full file manifest from prompt if present
        repo_files_match = re.search(r"REPOSITORY (?:STRUCTURE / )?FILES (?:\(\d+ files(?: total)?\))?:\n([\s\S]*?)(?=\nCODEBASE CONTEXT:|\nUSER QUESTION:|\nKEY CODE SNIPPETS:)", prompt)
        full_file_list = []
        if repo_files_match:
            full_file_list = [line.strip("- ").strip() for line in repo_files_match.group(1).strip().split("\n") if line.strip() and not line.startswith("...")]

        # Determine target repository language(s)
        detected_langs = set()
        for f in files_involved:
            ext = f.split(".")[-1].lower() if "." in f else ""
            if ext in ["py", "pyw"]:
                detected_langs.add("Python")
            elif ext in ["js", "jsx"]:
                detected_langs.add("JavaScript")
            elif ext in ["ts", "tsx"]:
                detected_langs.add("TypeScript")
            elif ext in ["md", "markdown"]:
                detected_langs.add("Markdown")
            elif ext in ["html"]:
                detected_langs.add("HTML")
            elif ext in ["css", "scss"]:
                detected_langs.add("CSS")
            elif ext in ["sql"]:
                detected_langs.add("SQL")

        content_parts: list[str] = []

        # --- A. TECH STACK SYNTHESIS ---
        if is_tech_stack_query:
            content_parts.append(f"### 🛠️ Tech Stack & Dependencies ({repo_name})\n")
            content_parts.append(f"Based on source code analysis of the indexed files in **{repo_name}**:\n")

            if detected_langs:
                langs_str = ", ".join(f"**{lang}**" for lang in sorted(detected_langs))
                content_parts.append(f"1. **Core Languages**: {langs_str}")

            if detected_imports:
                known_frameworks = []
                for imp in sorted(detected_imports):
                    # Annotate well-known packages
                    lower_imp = imp.lower()
                    if "fastapi" in lower_imp:
                        known_frameworks.append("**FastAPI** (REST API framework)")
                    elif "streamlit" in lower_imp:
                        known_frameworks.append("**Streamlit** (Interactive Web UI)")
                    elif "langgraph" in lower_imp:
                        known_frameworks.append("**LangGraph** (Stateful Multi-Agent Orchestration)")
                    elif "langchain" in lower_imp:
                        known_frameworks.append("**LangChain** (LLM Framework & Tool Integrations)")
                    elif "pandas" in lower_imp:
                        known_frameworks.append("**Pandas** (Data Analysis & Manipulation)")
                    elif "psycopg" in lower_imp:
                        known_frameworks.append("**psycopg2 / PostgreSQL** (Database Connectivity)")
                    elif "sqlalchemy" in lower_imp:
                        known_frameworks.append("**SQLAlchemy** (ORM & Database Layer)")
                    elif "torch" in lower_imp:
                        known_frameworks.append("**PyTorch** (Deep Learning & Tensor Computation)")
                    elif "sklearn" in lower_imp or "scikit" in lower_imp:
                        known_frameworks.append("**scikit-learn** (Machine Learning)")
                    elif "requests" in lower_imp:
                        known_frameworks.append("**Requests** (HTTP Client)")
                    elif "dotenv" in lower_imp:
                        known_frameworks.append("**python-dotenv** (Environment Configuration)")
                    else:
                        known_frameworks.append(f"`{imp}`")

                content_parts.append("\n2. **Libraries & Frameworks Detected**:")
                for item in known_frameworks:
                    content_parts.append(f"   - {item}")

            content_parts.append("\n3. **Primary Source Modules Analyzed**:")
            for p in files_involved[:6]:
                content_parts.append(f"   - `{p}`")

        # --- B. ARCHITECTURE SYNTHESIS ---
        elif is_architecture_query:
            content_parts.append(f"### 🏛️ System Architecture Analysis ({repo_name})\n")
            content_parts.append(f"Architectural breakdown grounded in the indexed modules of **{repo_name}**:\n")

            # Group files into logical architecture tiers
            ui_client_nodes = []
            api_entry_nodes = []
            core_service_nodes = []
            data_db_nodes = []

            all_files = full_file_list if full_file_list else files_involved
            for f in all_files:
                f_lower = f.lower()
                basename = f.split("/")[-1]
                if any(k in f_lower for k in ["ui", "frontend", "client", "streamlit", "index.html", "templates"]):
                    if len(ui_client_nodes) < 2:
                        ui_client_nodes.append((f, basename))
                elif any(k in f_lower for k in ["api", "route", "server", "main.py", "app.py", "controller", "endpoint"]):
                    if len(api_entry_nodes) < 2:
                        api_entry_nodes.append((f, basename))
                elif any(k in f_lower for k in ["db", "model", "schema", "store", "repository", "sql", "database"]):
                    if len(data_db_nodes) < 2:
                        data_db_nodes.append((f, basename))
                else:
                    if len(core_service_nodes) < 3 and any(ext in f_lower for ext in [".py", ".ts", ".js", ".go", ".rs"]):
                        core_service_nodes.append((f, basename))

            # Build clean, valid flowchart LR with safe alphanumeric IDs
            mermaid_lines = ["flowchart LR"]
            prev_id = None
            step = 1

            if ui_client_nodes:
                node_id = f"UI{step}"
                lbl = ui_client_nodes[0][1].replace('"', "'")
                mermaid_lines.append(f'    {node_id}["UI / Client ({lbl})"]')
                prev_id = node_id
                step += 1

            if api_entry_nodes:
                node_id = f"API{step}"
                lbl = api_entry_nodes[0][1].replace('"', "'")
                mermaid_lines.append(f'    {node_id}["API / Entry ({lbl})"]')
                if prev_id:
                    mermaid_lines.append(f"    {prev_id} --> {node_id}")
                prev_id = node_id
                step += 1

            if core_service_nodes:
                node_id = f"Core{step}"
                lbl = core_service_nodes[0][1].replace('"', "'")
                mermaid_lines.append(f'    {node_id}["Core Logic ({lbl})"]')
                if prev_id:
                    mermaid_lines.append(f"    {prev_id} --> {node_id}")
                prev_id = node_id
                step += 1

            if data_db_nodes:
                node_id = f"DB{step}"
                lbl = data_db_nodes[0][1].replace('"', "'")
                mermaid_lines.append(f'    {node_id}[("Storage / DB ({lbl})")]')
                if prev_id:
                    mermaid_lines.append(f"    {prev_id} --> {node_id}")
                prev_id = node_id
                step += 1

            # Fallback if no specific layers detected: use top files cleanly
            if len(mermaid_lines) <= 2 and files_involved:
                mermaid_lines = ["flowchart LR"]
                prev_id = None
                for i, f in enumerate(files_involved[:4], start=1):
                    node_id = f"Comp{i}"
                    clean_name = f.split("/")[-1].replace('"', "'")
                    mermaid_lines.append(f'    {node_id}["{clean_name}"]')
                    if prev_id:
                        mermaid_lines.append(f"    {prev_id} --> {node_id}")
                    prev_id = node_id

            if len(mermaid_lines) > 1:
                diagram = "```mermaid\n" + "\n".join(mermaid_lines) + "\n```\n"
                content_parts.append(diagram)

            content_parts.append("\n**Core Components Identified**:")
            if detected_classes:
                for c_name, c_file, c_line in detected_classes[:5]:
                    content_parts.append(f"- **Class `{c_name}`** implemented in `[FILE:{c_file}:L{c_line}]`")
            elif files_involved:
                for f in files_involved[:5]:
                    content_parts.append(f"- Module `{f}`")

        # --- C. SUMMARY SYNTHESIS ---
        elif is_summary_query:
            content_parts.append(f"### 📋 Repository Summary ({repo_name})\n")
            content_parts.append(f"**{repo_name}** is a software repository structured across {len(files_involved)} indexed source files.\n")

            if detected_classes or detected_funcs:
                content_parts.append("#### Key Implementation Highlights:")
                for c_name, c_file, c_line in detected_classes[:4]:
                    content_parts.append(f"- **Class `{c_name}`** (`[FILE:{c_file}:L{c_line}]`)")
                for fn_name, fn_file, fn_line in detected_funcs[:4]:
                    content_parts.append(f"- **Function `{fn_name}()`** (`[FILE:{fn_file}:L{fn_line}]`)")

            content_parts.append("\n#### Primary File Manifest:")
            for f in files_involved[:8]:
                content_parts.append(f"- `{f}`")

        # --- D. FILE LIST SYNTHESIS ---
        elif is_file_list_query:
            files_to_show = full_file_list if full_file_list else files_involved
            content_parts.append(f"### 📁 Repository Files ({repo_name})\n")
            content_parts.append(f"The repository contains **{len(files_to_show)} indexed files**:\n")
            for f in files_to_show:
                matching_cit = next((c for c in citations if f in c), None)
                if matching_cit:
                    content_parts.append(f"- **`{f}`** (verified in {matching_cit})")
                else:
                    content_parts.append(f"- **`{f}`**")

        # --- E. SPECIFIC CHAT Q&A SYNTHESIS ---
        else:
            clean_q = user_question or "Repository Query"
            content_parts.append(f"### 💡 Query: *\"{clean_q}\"*\n")
            content_parts.append(f"Analysis grounded in retrieved snippets from **{repo_name}**:\n")

            if detected_funcs or detected_classes:
                content_parts.append("#### Relevant Code Constructs Found:")
                for c_name, c_file, c_line in detected_classes[:3]:
                    content_parts.append(f"- **Class `{c_name}`**: Defined in `[FILE:{c_file}:L{c_line}]`")
                for fn_name, fn_file, fn_line in detected_funcs[:4]:
                    content_parts.append(f"- **Function `{fn_name}()`**: Implemented in `[FILE:{fn_file}:L{fn_line}]`")

            # Extract snippet excerpts directly relevant to the query
            content_parts.append("\n#### Evidence from Source Files:")
            for path, start, end, lang, snippet in chunk_blocks[:3]:
                if snippet:
                    preview_lines = [l for l in snippet.split("\n") if l.strip()][:5]
                    preview = "\n".join(preview_lines)
                    content_parts.append(f"From `[FILE:{path}:L{start}-L{end}]`:\n```{lang}\n{preview}\n...\n```")

        # Add references and quota notice
        content_parts.append("\n---")
        content_parts.append("#### Grounded Source References:")
        for cit in citations[:6]:
            content_parts.append(f"- {cit}")

        content_parts.append("\n*(Note: Synthesized from indexed repository chunks. Set or refresh `GEMINI_API_KEY` in `.env` for unconstrained LLM generation).*")

        final_content = "\n".join(content_parts)

        return LLMResponse(
            content=final_content,
            model="local-repopilot-engine",
            tokens_used=180,
            finish_reason="stop",
        )

