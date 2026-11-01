"""
Prompt builder — crafts tailored system and user prompts for different repository intelligence modes.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


class PromptBuilder:
    """Builds structured LLM prompts for different modes (chat, summary, api discovery, etc.)."""

    SYSTEM_BASE = """You are RepoPilot, a senior staff AI software engineer and codebase intelligence assistant.
Your goal is to answer developer questions accurately, deeply, and strictly grounded in the provided codebase context.

CRITICAL CITATION RULES:
1. Whenever referencing logic, functions, classes, or configuration, you MUST cite the exact file path and line numbers using this inline format: `[FILE:path/to/file.ext:Lstart-Lend]`.
2. Do NOT invent or hallucinate file paths or line numbers. Only cite files that appear in the provided context.
3. If the context does not contain enough information to answer definitively, state what is known and clarify what is missing.
4. Format your output in clear GitHub-flavored Markdown. Include syntax-highlighted code blocks where helpful.
"""

    @classmethod
    def format_context_chunks(cls, chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved code chunks into a clear contextual block."""
        if not chunks:
            return "No relevant code snippets found in repository."

        formatted_blocks = []
        for i, chunk in enumerate(chunks, start=1):
            file_path = chunk.get("file_path", "unknown")
            start_line = chunk.get("start_line", 1)
            end_line = chunk.get("end_line", 1)
            language = chunk.get("language") or "text"
            content = chunk.get("content", "").strip()

            block = (
                f"### Context Chunk {i}: {file_path} (Lines {start_line}-{end_line})\n"
                f"```{language.lower()}\n"
                f"{content}\n"
                f"```"
            )
            formatted_blocks.append(block)

        return "\n\n".join(formatted_blocks)

    @classmethod
    def build_chat_prompt(
        cls,
        question: str,
        context_chunks: List[Dict[str, Any]],
        repo_name: str,
        file_list: Optional[List[str]] = None,
    ) -> tuple[str, str]:
        """Build standard Q&A chat prompt."""
        context_text = cls.format_context_chunks(context_chunks)
        files_section = ""
        if file_list:
            files_preview = "\n".join(f"- {f}" for f in file_list[:120])
            if len(file_list) > 120:
                files_preview += f"\n... and {len(file_list) - 120} more files."
            files_section = f"\nREPOSITORY STRUCTURE / FILES ({len(file_list)} files total):\n{files_preview}\n"

        user_prompt = f"""Repository: {repo_name}
{files_section}
CODEBASE CONTEXT:
{context_text}

USER QUESTION:
{question}

Please provide a detailed, well-structured answer.
When referencing specific source lines or implementations from the codebase context, use inline citations like `[FILE:path:Lstart-Lend]`.
If the user asks to list or identify files in the repository, refer to the REPOSITORY STRUCTURE / FILES list above so you provide a comprehensive and accurate overview of the codebase.
Do NOT output a Mermaid diagram unless the user explicitly requested a flowchart, diagram, or architecture graph in their question.
"""
        return cls.SYSTEM_BASE, user_prompt

    @classmethod
    def build_summary_prompt(
        cls,
        repo_name: str,
        file_list: List[str],
        language_stats: Dict[str, Any],
        sample_chunks: List[Dict[str, Any]],
    ) -> tuple[str, str]:
        """Build repository summary prompt with Mermaid architecture."""
        system_prompt = (
            cls.SYSTEM_BASE
            + "\nYou are conducting an executive architectural review of this repository."
        )

        files_preview = "\n".join(file_list[:100])
        if len(file_list) > 100:
            files_preview += f"\n... and {len(file_list) - 100} more files."

        context_text = cls.format_context_chunks(sample_chunks)

        user_prompt = f"""Please generate a comprehensive, resume-grade repository summary for **{repo_name}**.

LANGUAGE STATS:
{json.dumps(language_stats, indent=2)}

REPOSITORY FILE TREE:
{files_preview}

KEY CODE SNIPPETS:
{context_text}

Produce a structured breakdown covering:
1. **Executive Overview & Purpose**: What this project does and its core value proposition.
2. **Tech Stack & Libraries**: Primary languages, frameworks, databases, and tooling detected.
3. **Architecture & Module Organization**: High-level structure and responsibilities of key folders.
4. **Key Data & Control Flows**: How requests, jobs, or data move through the system.
5. **System Architecture Diagram**: MUST include EXACTLY ONE valid, syntax-clean `mermaid` flowchart diagram illustrating the major components:
```mermaid
flowchart LR
    Client["Client / User"] --> API["Server / Controller"]
    API --> Service["Core Service / Logic"]
    Service --> Storage[("Database / Store")]
```
Rules for Mermaid:
- Use `flowchart LR`.
- Keep it clean, simple, and readable (between 4 and 7 primary components).
- Ground only in the actual detected architecture of **{repo_name}**.
- Node IDs must be simple alphanumeric strings (no file paths, slashes, dots, or dashes).
- All labels must be short (under 28 chars) and enclosed in double quotes: `ID["Label"]`.
6. **Key API Endpoints or Entrypoints**: Found in the codebase.
"""
        return system_prompt, user_prompt

    @classmethod
    def build_api_discovery_prompt(
        cls,
        repo_name: str,
        context_chunks: List[Dict[str, Any]],
    ) -> tuple[str, str]:
        """Build prompt to detect all REST, GraphQL, RPC, or CLI endpoints."""
        context_text = cls.format_context_chunks(context_chunks)
        user_prompt = f"""Analyze the codebase context for **{repo_name}** to discover and catalog all API endpoints, routes, GraphQL schemas, or CLI commands.

CODE CONTEXT:
{context_text}

For each endpoint discovered, document:
- **HTTP Method & Route / Operation Name**
- **File & Line Citation**: `[FILE:path:Lstart-Lend]`
- **Handler Function / Controller**
- **Authentication / Authorization Required** (if detectable)
- **Request / Response Payload summary**
"""
        return cls.SYSTEM_BASE, user_prompt

    @classmethod
    def build_readme_prompt(
        cls,
        repo_name: str,
        context_chunks: List[Dict[str, Any]],
        language_stats: Dict[str, Any],
    ) -> tuple[str, str]:
        """Build prompt to generate a production-ready README.md."""
        context_text = cls.format_context_chunks(context_chunks)
        user_prompt = f"""Generate a polished, production-grade `README.md` for the repository **{repo_name}**.

DETECTED LANGUAGES:
{json.dumps(language_stats, indent=2)}

KEY CODEBASE SAMPLES:
{context_text}

Include:
- Project title & catchy tagline
- Feature breakdown with emojis
- Architecture diagram (in Mermaid)
- Prerequisites & Installation instructions
- Usage examples
- Configuration / Environment variables table
- Contributing & License
"""
        return cls.SYSTEM_BASE, user_prompt

    @classmethod
    def build_bug_scan_prompt(
        cls,
        repo_name: str,
        context_chunks: List[Dict[str, Any]],
    ) -> tuple[str, str]:
        """Build prompt for security review and bug detection."""
        context_text = cls.format_context_chunks(context_chunks)
        user_prompt = f"""Perform a code quality, security, and bug audit on the retrieved code for **{repo_name}**.

CODE CONTEXT:
{context_text}

Identify potential issues such as:
1. Security vulnerabilities (injection, auth bypass, unvalidated input, hardcoded secrets)
2. Resource leaks, race conditions, or unhandled exceptions
3. Performance bottlenecks or anti-patterns
4. Edge-case bugs

For each finding, provide:
- **Severity**: [Critical | High | Medium | Low]
- **Location**: `[FILE:path:Lstart-Lend]`
- **Description of the risk**
- **Recommended fix with code snippet**
"""
        return cls.SYSTEM_BASE, user_prompt

    @classmethod
    def build_architecture_prompt(
        cls,
        repo_name: str,
        context_chunks: List[Dict[str, Any]],
        file_list: Optional[List[str]] = None,
        language_stats: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, str]:
        """Build prompt dedicated to architecture & Mermaid diagrams."""
        context_text = cls.format_context_chunks(context_chunks)
        files_section = ""
        if file_list:
            files_preview = "\n".join(f"- {f}" for f in file_list[:80])
            if len(file_list) > 80:
                files_preview += f"\n... and {len(file_list) - 80} more files."
            files_section = f"\nREPOSITORY FILE MANIFEST ({len(file_list)} files total):\n{files_preview}\n"

        lang_section = ""
        if language_stats:
            lang_section = f"\nDETECTED LANGUAGES & TECH:\n{json.dumps(language_stats, indent=2)}\n"

        user_prompt = f"""Generate a clear, accurate, repository-specific architectural analysis for **{repo_name}**.
{lang_section}
{files_section}
KEY CODE CONTEXT:
{context_text}

STRUCTURE YOUR RESPONSE INTO THESE SECTIONS:
1. **High-Level Architecture Overview**: High-level explanation of how **{repo_name}** is organized, its primary modules, and their responsibilities.
2. **System Architecture Diagram**:
Provide EXACTLY ONE clean, valid, high-contrast `mermaid` diagram enclosed in a ```mermaid ... ``` block.

CRITICAL MERMAID SYNTAX RULES:
- MUST start with: `flowchart LR`
- Keep it clean, readable, and simple (between 4 and 7 primary components).
- Ground it ONLY in the detected modules and actual responsibilities of **{repo_name}** (e.g. User/Client, Entrypoint, Core Logic/Pipelines, Storage/Models, External Utilities).
- DO NOT invent generic architecture or components from unrelated projects.
- Use simple alphanumeric IDs for each node (e.g. `Client`, `Server`, `Engine`, `DB`, `Worker`). NEVER use file paths, dots, hyphens, slashes, or special symbols in the node ID itself.
- ALWAYS wrap node text labels in double quotes inside brackets: e.g. `Client["Web Client"]`, `API["FastAPI Handler"]`, `Storage[("SQLite DB")]`.
- Connect nodes cleanly using standard arrows: `-->` or `-->|"action"|`.
- Example of valid format:
```mermaid
flowchart LR
    Client["Client / User"] --> API["API Entrypoint"]
    API --> Core["Processing Engine"]
    Core --> Storage[("Database Layer")]
```

3. **Component Responsibilities & Data Flow**: Explain the responsibilities of each component shown in the diagram and how data flows between them.
4. **Key Files & Entrypoints**: List the 3-5 primary files defining this architecture with `[FILE:path:Lstart-Lend]` citations.
"""
        return cls.SYSTEM_BASE, user_prompt

