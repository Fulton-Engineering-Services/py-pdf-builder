# Copyright 2026 Fulton Engineering Services LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for :mod:`fes_pdf_builder.diagrams.sequence`."""

from __future__ import annotations

import re
from io import BytesIO

import pytest

from fes_pdf_builder.diagrams.sequence import parse_sequence, render_sequence_png

SAMPLE_SEQUENCE = """sequenceDiagram
    participant Client as "Client (benchmark harness)"
    participant Server as "llama-server / API"
    participant Model as "Reasoning-tuned model"

    Client->>Server: "chat/completions (prompt, max_tokens)"
    Server->>Model: prefill prompt tokens
    Model-->>Server: "opening think token"
    Server-->>Client: "stream chunk"

    note over Server,Model: "the inner loop owns wall-clock latency"

    loop "reasoning trace"
        Model-->>Server: "reasoning token"
        Server-->>Client: "stream chunk"
    end

    Model-->>Server: EOS
    Server-->>Client: "finish_reason=stop"
"""


def test_parse_sequence_extracts_participants_with_aliases() -> None:
    parts, _ = parse_sequence(SAMPLE_SEQUENCE)
    assert len(parts) == 3
    pids = [p.pid for p in parts]
    assert pids == ["Client", "Server", "Model"]
    labels = {p.pid: p.label for p in parts}
    assert labels["Client"] == "Client (benchmark harness)"
    assert labels["Server"] == "llama-server / API"
    assert labels["Model"] == "Reasoning-tuned model"


def test_parse_sequence_extracts_messages_and_dashed_flag() -> None:
    _, steps = parse_sequence(SAMPLE_SEQUENCE)
    msgs = [s for s in steps if s.kind == "msg"]
    assert len(msgs) == 8

    first = msgs[0]
    assert first.payload["from"] == "Client"
    assert first.payload["to"] == "Server"
    assert first.payload["dashed"] is False
    assert "chat/completions" in first.payload["text"]

    third = msgs[2]
    assert third.payload["from"] == "Model"
    assert third.payload["to"] == "Server"
    assert third.payload["dashed"] is True


def test_parse_sequence_handles_notes_loops_and_end() -> None:
    _, steps = parse_sequence(SAMPLE_SEQUENCE)

    notes = [s for s in steps if s.kind == "note"]
    assert len(notes) == 1
    assert notes[0].payload["pids"] == ["Server", "Model"]
    assert "wall-clock latency" in notes[0].payload["text"]

    opens = [s for s in steps if s.kind == "block_open"]
    closes = [s for s in steps if s.kind == "block_close"]
    assert len(opens) == 1
    assert opens[0].payload["block_kind"] == "loop"
    assert opens[0].payload["label"] == "reasoning trace"
    assert len(closes) == 1


def test_parse_sequence_returns_empty_for_empty_input() -> None:
    parts, steps = parse_sequence("")
    assert parts == []
    assert steps == []


def test_parse_sequence_ignores_autonumber_and_unknown_directives() -> None:
    _, steps = parse_sequence("sequenceDiagram\nautonumber\nactivate Foo\ndeactivate Foo\n")
    assert steps == []


def test_render_sequence_png_returns_buffer_and_dimensions() -> None:
    matplotlib = pytest.importorskip("matplotlib")
    del matplotlib

    result = render_sequence_png(SAMPLE_SEQUENCE)
    assert result is not None, "expected matplotlib renderer to succeed"
    buf, w_pts, h_pts = result
    assert isinstance(buf, BytesIO)
    assert w_pts > 0
    assert h_pts > 0
    payload = buf.getvalue()
    assert payload.startswith(b"\x89PNG"), "expected a real PNG payload"


def test_render_sequence_png_returns_none_for_empty_input() -> None:
    assert render_sequence_png("") is None


def test_render_sequence_png_dispatches_through_make_diagram_box() -> None:
    """The flowchart/sequence dispatcher in mermaid.make_diagram_box should
    pick up sequenceDiagram blocks and route them through the matplotlib
    renderer instead of falling back to the structured-text box."""
    pytest.importorskip("matplotlib")
    from fes_pdf_builder.diagrams.mermaid import make_diagram_box
    from fes_pdf_builder.styles import make_styles
    from fes_pdf_builder.toc import FigureRegistry

    figs = FigureRegistry()
    flowables = make_diagram_box(
        SAMPLE_SEQUENCE,
        make_styles(),
        figures=figs,
        chapter_title="Sequence Test Chapter",
    )
    # 1 anchor + 1 visual flowable
    assert len(flowables) == 2
    assert len(figs) == 1
    assert figs.entries[0].diagram_type == "Sequence Diagram"
    assert re.match(r"^fig_\d{3}$", figs.entries[0].fig_key) is not None
