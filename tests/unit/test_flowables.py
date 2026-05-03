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

"""Unit tests for :mod:`fes_pdf_builder.flowables`."""

from __future__ import annotations

from fes_pdf_builder.flowables import BookmarkAnchor, ChapterAnchor, FigureAnchor, HeaderState


class _FakeCanvas:
    def __init__(self) -> None:
        self.bookmarks: list[str] = []
        self.outline: list[tuple[str, str, int, int]] = []

    def bookmarkPage(self, key: str) -> None:  # noqa: N802
        self.bookmarks.append(key)

    def addOutlineEntry(self, title: str, key: str, level: int, closed: int) -> None:  # noqa: N802
        self.outline.append((title, key, level, closed))


def test_chapter_anchor_is_zero_size() -> None:
    state = HeaderState()
    a = ChapterAnchor("ch1", "Chapter 1", state=state, level=1)
    assert a.wrap(100, 100) == (0, 0)


def test_chapter_anchor_draw_updates_state_and_canvas() -> None:
    state = HeaderState(initial="prev")
    a = ChapterAnchor("ch1", "Chapter 1", state=state, level=1)
    a.canv = _FakeCanvas()  # type: ignore[attr-defined]
    a.draw()
    assert state.current == "Chapter 1"
    assert a.canv.bookmarks == ["ch1"]
    assert a.canv.outline == [("Chapter 1", "ch1", 1, 0)]


def test_figure_anchor_only_bookmarks() -> None:
    a = FigureAnchor("fig_001")
    assert a.wrap(100, 100) == (0, 0)
    a.canv = _FakeCanvas()  # type: ignore[attr-defined]
    a.draw()
    assert a.canv.bookmarks == ["fig_001"]
    assert a.canv.outline == []


def test_bookmark_anchor_only_bookmarks() -> None:
    a = BookmarkAnchor("ch1__a-heading")
    assert a.wrap(100, 100) == (0, 0)
    a.canv = _FakeCanvas()  # type: ignore[attr-defined]
    a.draw()
    assert a.canv.bookmarks == ["ch1__a-heading"]
    assert a.canv.outline == []


def test_header_state_current_is_chapter_tracks_level() -> None:
    state = HeaderState()
    # level=0 is front-matter (not a "chapter")
    a0 = ChapterAnchor("toc", "Table of Contents", state=state, level=0)
    a0.canv = _FakeCanvas()  # type: ignore[attr-defined]
    a0.draw()
    assert state.current_is_chapter is False

    # level=1 is a chapter
    a1 = ChapterAnchor("ch1", "Chapter 1", state=state, level=1)
    a1.canv = _FakeCanvas()  # type: ignore[attr-defined]
    a1.draw()
    assert state.current_is_chapter is True
