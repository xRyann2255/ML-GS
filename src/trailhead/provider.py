"""Stage 3 NARRATE — the model interface, and the ONLY place a model is reached.

Non-negotiable #1 says a model cannot verify itself, so everything that checks
anything is ordinary code. That is a promise until it is structural: one
one-method protocol, imported by exactly one module (`narrate.py`), makes it
greppable. If `provider` appears in an import line anywhere in survey, mapper,
checkpoints, runner, resolve, verify or render, the project has lost its pitch.

Three implementations of one method:

    StubProvider    DEFAULT. Replays `.trailhead/narration/<key>.json`.
    ClaudeProvider  opt-in (`--provider claude`). Imports `anthropic` INSIDE the
                    call, so the package imports cleanly with no dependency
                    installed anywhere on the machine.

The agent-narration route makes the stub the normal path rather than a testing
convenience: `narrate --emit-prompts` writes one prompt pack per unit, the host
coding agent answers each pack into the store, and the stub replays it. Record
and replay therefore share ONE directory and ONE key — `cache_key` below — or
replay misses every single time and every stop falls back to its template.
"""
import hashlib
import json
import os
from pathlib import Path
from typing import Protocol

#: The §5.5 response schema, verbatim. `additionalProperties: false` at both
#: levels is the first of the three defences against a line number coming back:
#: there is no field to put one in. The other two are the parser's cite-key
#: check (`narrate.parse`) and `tools/check-fixtures.js:80`.
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["claims"],
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["text", "status", "cite"],
                "properties": {
                    "text": {"type": "string"},
                    "status": {"type": "string", "enum": ["verified", "inferred"]},
                    "cite": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "file": {"type": "string"},
                            "quote": {"type": "string"},
                            "focus": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
            },
        }
    },
}

#: The only keys a `cite` may carry. A response using any other key is rejected
#: whole and never repaired — see `narrate.parse`.
CITE_KEYS = frozenset({"file", "quote", "focus"})

#: Named in the pitch, and its limits are real: thinking is adaptive and ON by
#: default on this model and shares the budget with the response, so 16000 is
#: the floor at which the 8-hop `trace` unit reliably completes. A truncated
#: response is invalid JSON and costs the whole unit.
DEFAULT_MODEL = "claude-opus-5"
DEFAULT_MAX_TOKENS = 16000


class MissingNarration(RuntimeError):
    """`--offline` and the store has no answer for this prompt.

    Deliberately fatal. Offline exists so a rehearsal cannot silently become a
    demo of the template fallback: if the cache does not cover the run, the
    operator wants to know now, not from a page with no claims on it.
    """


def cache_key(system: str, user: str) -> str:
    """The one narration key: sha256 of `system + "\\x00" + user`.

    Both halves, because a system-prompt edit changes what the model was asked
    and must invalidate. The prompt already embeds the evidence — the numbered
    source windows — so any change to the repo, the survey or the packing
    changes these bytes too. That is why there is no PROMPT_VERSION constant to
    forget to bump.

    The NUL separator is not decoration: without it, moving one sentence from
    the end of `system` to the start of `user` would hash identically.
    """
    return hashlib.sha256((system + "\x00" + user).encode("utf-8")).hexdigest()


class Provider(Protocol):
    """One method. That is the entire model surface of this project."""

    name: str

    def complete(self, system: str, user: str, schema: dict) -> dict:
        """Return the parsed JSON response, or a `{"_stop_reason": …}` sentinel."""


class StubProvider:
    """Replay from `.trailhead/narration/<key>.json` — the default provider.

    The store is written by the host agent answering an `--emit-prompts` pack,
    or by a live `ClaudeProvider` run; nothing distinguishes the two on disk,
    which is exactly the point. `narrate.run` looks in the same directory before
    it calls anybody, so in the normal pipeline this method is reached only on a
    genuine miss.

    A miss returns `{"claims": []}` rather than raising: the unit then renders
    from its deterministic template blocks and the page is still honest, just
    thinner. Under `--offline` a miss raises instead.
    """

    name = "stub"
    model = "stub"

    def __init__(self, directory: Path, *, offline: bool = False):
        self.directory = Path(directory)
        self.offline = offline

    def complete(self, system: str, user: str, schema: dict) -> dict:
        key = cache_key(system, user)
        path = self.directory / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        if self.offline:
            raise MissingNarration(
                f"no narration for {key} in {self.directory} and --offline is set"
            )
        return {"claims": []}


class ClaudeProvider:
    """The live path. Opt-in via `--provider claude`; never the default.

    `import anthropic` is inside `complete` on purpose. The agent-narration
    route removed the last third-party dependency from this project, and a
    module-scope import would put it back — `import trailhead.narrate` would
    fail on a clean machine and take every test with it, including the ones
    that never touch a model.

    Two env vars and no code above the protocol: `TRAILHEAD_BASE_URL` swaps in
    the internal gateway, `ANTHROPIC_API_KEY` carries the credential.
    """

    name = "claude"

    def __init__(self, *, model: str = DEFAULT_MODEL,
                 base_url: str | None = None,
                 max_tokens: int = DEFAULT_MAX_TOKENS):
        self.model = model
        self.base_url = base_url or os.environ.get("TRAILHEAD_BASE_URL") or None
        self.max_tokens = max_tokens

    def complete(self, system: str, user: str, schema: dict) -> dict:
        import anthropic  # noqa: PLC0415 — deliberate, see the class docstring

        kwargs = {}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        client = anthropic.Anthropic(**kwargs)

        # No temperature / top_p / top_k: Opus 5 rejects them with a 400.
        # Determinism comes from the disk cache, not from sampling parameters.
        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )

        # `max_tokens` and `refusal` both come back HTTP 200 with content that
        # will not satisfy the schema. They are parse failures with their own
        # ledger reason, not exceptions — §9 row 11.
        stop = getattr(response, "stop_reason", None)
        if stop in ("max_tokens", "refusal"):
            return {"_stop_reason": stop}

        text = "".join(
            getattr(block, "text", "")
            for block in getattr(response, "content", [])
            if getattr(block, "type", "") == "text"
        )
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return {"_stop_reason": "invalid_json"}


def build(name: str, directory: Path, *, offline: bool = False,
          model: str = DEFAULT_MODEL, base_url: str | None = None) -> Provider:
    """`--provider` string to instance, so the CLI holds no provider knowledge.

    `directory` is the narration store (`<work>/narration`); the live provider
    ignores it because `narrate.run` owns the cache for every provider.
    """
    if name == "stub":
        return StubProvider(directory, offline=offline)
    if name == "claude":
        return ClaudeProvider(model=model, base_url=base_url)
    raise ValueError(f"unknown provider {name!r} — expected 'stub' or 'claude'")
