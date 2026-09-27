from types import SimpleNamespace

from mcbuild.llm.client import OpenRouterClient


def _tool_schema():
    return [
        {
            "type": "function",
            "function": {
                "name": "query",
                "description": "Read build state.",
                "parameters": {
                    "type": "object",
                    "properties": {"mode": {"type": "string"}},
                    "required": ["mode"],
                },
            },
        }
    ]


def test_ollama_backend_defaults_to_local_openai_compatible_endpoint(monkeypatch):
    monkeypatch.delenv("MCBUILD_BASE_URL", raising=False)
    monkeypatch.delenv("MCBUILD_API_KEY", raising=False)

    client = OpenRouterClient(backend="ollama")

    assert client.is_ollama is True
    assert client.backend == "ollama"
    assert client.base_url == "http://127.0.0.1:11434/v1"


def test_ollama_backend_reads_remote_endpoint_from_environment(monkeypatch):
    monkeypatch.setenv("MCBUILD_LLM_BACKEND", "ollama")
    monkeypatch.setenv("MCBUILD_BASE_URL", "http://192.168.1.58:11434/v1")
    monkeypatch.setenv("MCBUILD_API_KEY", "ollama")

    client = OpenRouterClient()

    assert client.is_ollama is True
    assert client.base_url == "http://192.168.1.58:11434/v1"


def test_ollama_tool_turn_disables_reasoning_and_omits_user_field():
    client = OpenRouterClient(backend="ollama", base_url="http://ollama.test:11434/v1")
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        message = SimpleNamespace(content="", tool_calls=[], reasoning=None, reasoning_details=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)

    client._client.chat.completions.create = fake_create  # ty: ignore[invalid-assignment]
    client.chat(
        model="qwen3.5:9b",
        messages=[{"role": "user", "content": "Use the query tool."}],
        tools=_tool_schema(),
        reasoning="medium",
        stream=False,
    )

    assert "user" not in captured
    assert captured["extra_body"] == {"reasoning_effort": "none"}


def test_ollama_streaming_tool_turn_disables_reasoning_and_omits_user_field():
    client = OpenRouterClient(backend="ollama", base_url="http://ollama.test:11434/v1")
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        delta = SimpleNamespace(content="ok", reasoning=None, reasoning_details=None, tool_calls=None)
        return [SimpleNamespace(choices=[SimpleNamespace(delta=delta)], usage=None)]

    client._client.chat.completions.create = fake_create  # ty: ignore[invalid-assignment]
    result = client.chat(
        model="qwen3.5:9b",
        messages=[{"role": "user", "content": "Use the query tool."}],
        tools=_tool_schema(),
        reasoning="medium",
        stream=True,
    )

    assert result.message.content == "ok"
    assert "user" not in captured
    assert captured["extra_body"] == {"reasoning_effort": "none"}
    assert captured["stream"] is True
    assert captured["stream_options"] == {"include_usage": True}


def test_ollama_non_tool_turn_maps_reasoning_levels():
    client = OpenRouterClient(backend="ollama")

    assert client._extra_body("medium", tools=None) == {"reasoning_effort": "medium"}
    assert client._extra_body("off", tools=None) == {"reasoning_effort": "none"}
