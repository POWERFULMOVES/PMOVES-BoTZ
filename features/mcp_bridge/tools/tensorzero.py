"""
TensorZero MCP Tools

MCP tools for TensorZero LLM gateway:
- tensorzero_chat: Chat completion with dynamic model selection
- tensorzero_embed: Generate embeddings
- tensorzero_models: List available providers
- tensorzero_health: Gateway health check

Key Feature: Dynamic model routing using provider::model_name syntax:
- openai::qwen3:8b (Ollama local)
- anthropic::claude-sonnet-4-5-20250514 (Anthropic cloud)
- google_ai_studio_gemini::gemini-2.0-flash (Gemini cloud)

Usage:
    result = await handle_tool("tensorzero_chat", {
        "model": "openai::qwen3:8b",  # Dynamic syntax
        "messages": [{"role": "user", "content": "Hello"}]
    })
"""

import json
import os
from typing import Any

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

TENSORZERO_URL = os.getenv("TENSORZERO_URL", "http://localhost:3030")


# Tool definitions
TOOLS = [
    {
        "name": "tensorzero_chat",
        "description": "Chat completion via TensorZero gateway with dynamic model selection. Use provider::model_name syntax.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Model to use (e.g., 'openai::qwen3:8b', 'anthropic::claude-sonnet-4-5-20250514')",
                    "default": "openai::qwen3:8b",
                },
                "messages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string", "enum": ["system", "user", "assistant"]},
                            "content": {"type": "string"},
                        },
                        "required": ["role", "content"],
                    },
                    "description": "Chat messages",
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens to generate",
                    "default": 1024,
                },
                "temperature": {
                    "type": "number",
                    "description": "Sampling temperature",
                    "default": 0.7,
                },
            },
            "required": ["messages"],
        },
    },
    {
        "name": "tensorzero_embed",
        "description": "Generate embeddings via TensorZero",
        "inputSchema": {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Text to embed",
                },
                "model": {
                    "type": "string",
                    "description": "Embedding model",
                    "default": "openai::nomic-embed-text",
                },
            },
            "required": ["input"],
        },
    },
    {
        "name": "tensorzero_providers",
        "description": "List available TensorZero providers and their capabilities",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "tensorzero_health",
        "description": "Check TensorZero gateway health",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


# Provider information
PROVIDERS = {
    "local": {
        "ollama": {
            "prefix": "openai::",
            "base_url": "http://pmoves-ollama:11434/v1",
            "description": "Primary local models via Ollama",
            "example_models": ["qwen3:8b", "llama3.1", "phi3"],
        },
        "lmstudio": {
            "prefix": "openai::",
            "base_url": "http://host.docker.internal:1234/v1",
            "description": "LM Studio local models",
        },
        "vllm": {
            "prefix": "openai::",
            "base_url": "http://pmoves-vllm:8000/v1",
            "description": "High-throughput vLLM inference",
        },
    },
    "cloud": {
        "anthropic": {
            "prefix": "anthropic::",
            "description": "Claude models for complex reasoning",
            "example_models": ["claude-sonnet-4-5-20250514", "claude-3-haiku-20240307"],
        },
        "gemini": {
            "prefix": "google_ai_studio_gemini::",
            "description": "Gemini models (cost-effective)",
            "example_models": ["gemini-2.0-flash"],
        },
        "openrouter": {
            "prefix": "openai::",
            "base_url": "https://openrouter.ai/api/v1",
            "description": "Aggregated cloud model access",
        },
        "nvidia_nims": {
            "prefix": "openai::",
            "base_url": "https://integrate.api.nvidia.com/v1",
            "description": "NVIDIA optimized models",
        },
    },
}


async def handle_tool(name: str, arguments: dict) -> dict:
    """
    Handle tool invocation.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        Tool result as MCP content block
    """
    if name == "tensorzero_providers":
        return _handle_providers()

    if not HAS_HTTPX:
        return {"content": [{"type": "text", "text": "Error: httpx not installed"}]}

    try:
        if name == "tensorzero_chat":
            return await _handle_chat(arguments)
        elif name == "tensorzero_embed":
            return await _handle_embed(arguments)
        elif name == "tensorzero_health":
            return await _handle_health()
        else:
            return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


async def _handle_chat(args: dict) -> dict:
    """Handle tensorzero_chat tool."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        payload = {
            "model": args.get("model", "openai::qwen3:8b"),
            "messages": args["messages"],
            "max_tokens": args.get("max_tokens", 1024),
            "temperature": args.get("temperature", 0.7),
        }

        response = await client.post(
            f"{TENSORZERO_URL}/v1/chat/completions",
            json=payload,
        )
        response.raise_for_status()
        result = response.json()

        # Extract the response content
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Include usage info
        usage = result.get("usage", {})
        usage_text = ""
        if usage:
            usage_text = f"\n\n---\nTokens: {usage.get('prompt_tokens', 0)} in / {usage.get('completion_tokens', 0)} out"

        return {
            "content": [
                {
                    "type": "text",
                    "text": content + usage_text,
                }
            ]
        }


async def _handle_embed(args: dict) -> dict:
    """Handle tensorzero_embed tool."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {
            "model": args.get("model", "openai::nomic-embed-text"),
            "input": args["input"],
        }

        response = await client.post(
            f"{TENSORZERO_URL}/v1/embeddings",
            json=payload,
        )
        response.raise_for_status()
        result = response.json()

        embedding = result.get("data", [{}])[0].get("embedding", [])

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Generated embedding with {len(embedding)} dimensions",
                }
            ]
        }


async def _handle_health() -> dict:
    """Handle tensorzero_health tool."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(f"{TENSORZERO_URL}/health")
            status = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            status = f"offline: {str(e)}"

    return {
        "content": [
            {
                "type": "text",
                "text": f"TensorZero Status: {status}\nEndpoint: {TENSORZERO_URL}",
            }
        ]
    }


def _handle_providers() -> dict:
    """Handle tensorzero_providers tool."""
    output_lines = [
        "TensorZero Providers",
        "===================",
        "",
        "Use provider::model_name syntax for dynamic model selection.",
        "",
        "## LOCAL PROVIDERS",
    ]

    for name, info in PROVIDERS["local"].items():
        output_lines.append(f"\n### {name}")
        output_lines.append(f"  Prefix: {info.get('prefix', 'N/A')}")
        output_lines.append(f"  {info.get('description', '')}")
        if "example_models" in info:
            output_lines.append(f"  Examples: {', '.join(info['example_models'])}")

    output_lines.append("\n## CLOUD PROVIDERS")

    for name, info in PROVIDERS["cloud"].items():
        output_lines.append(f"\n### {name}")
        output_lines.append(f"  Prefix: {info.get('prefix', 'N/A')}")
        output_lines.append(f"  {info.get('description', '')}")
        if "example_models" in info:
            output_lines.append(f"  Examples: {', '.join(info['example_models'])}")

    output_lines.extend([
        "",
        "## USAGE EXAMPLES",
        "  openai::qwen3:8b              # Ollama local",
        "  anthropic::claude-sonnet-4-5-20250514  # Claude cloud",
        "  google_ai_studio_gemini::gemini-2.0-flash  # Gemini cloud",
    ])

    return {
        "content": [
            {
                "type": "text",
                "text": "\n".join(output_lines),
            }
        ]
    }
