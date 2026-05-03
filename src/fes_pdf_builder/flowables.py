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

"""Zero-height flowables that fire side-effects at render time.

Every report needs the same render-time bookmark / outline / running-header trick.

The two flowables exposed here both rely on a deferred-execution invariant:

* They are appended to the ReportLab story by parser/renderer code at
  *parse* time.
* When ReportLab paginates the document, ``draw()`` runs at *render* time,
  on the page where the flowable physically lands.
* Page templates registered via ``onPageEnd`` (rather than ``onPage``) fire
  *after* every flowable on the page has drawn — meaning a
  :class:`ChapterAnchor` that appears at the top of a new chapter can update
  the running-header state *before* the header text is painted.

This eliminates the stale-header bug where a new chapter's first page would
otherwise show the previous chapter's title.
"""

from __future__ import annotations

from reportlab.platypus.flowables import Flowable

__all__ = ["BookmarkAnchor", "ChapterAnchor", "FigureAnchor", "HeaderState"]


class HeaderState:
    """Mutable container for the current chapter title.

    The page-template's ``onPageEnd`` callback reads ``self.current`` to
    paint the running header. :class:`ChapterAnchor.draw` mutates it. We use
    a simple attribute (rather than a list) so multiple report builds in
    the same Python process can each construct a fresh state instance.

    ``current_is_chapter`` distinguishes "real" chapters / appendices
    (``ChapterAnchor.level >= 1``) from front-matter pages like the TOC,
    Preface, or part dividers (``level == 0``). The page-template uses it
    to prefix the running header with ``"Chapter: "`` only on chapter
    pages.
    """

    __slots__ = ("current", "current_is_chapter")

    def __init__(self, initial: str = "") -> None:
        self.current: str = initial
        self.current_is_chapter: bool = False


class ChapterAnchor(Flowable):
    """Zero-height flowable that fires three side-effects at render time:

    1. Updates ``state.current`` so the page-template's ``onPageEnd`` callback
       paints the correct chapter title in the running header.
    2. Registers a named PDF destination via ``canvas.bookmarkPage()`` so
       TOC ``<a href="#key">`` links have a target to jump to.
    3. Adds an entry to the PDF outline (bookmarks panel) via
       ``canvas.addOutlineEntry()`` so viewers display a navigation tree.

    Because :func:`reporting.page_templates.main_page_painter` is registered
    as ``onPageEnd`` (not ``onPage``), this flowable's ``draw`` has already
    updated the header state before the header is painted on the same page.

    Attributes:
        key: PDF destination key (used by ``<a href="#key">`` links).
        title: Display text for the running header and outline entry.
        level: PDF outline level (0 = top-level part, 1 = chapter, ...).
    """

    def __init__(
        self,
        key: str,
        title: str,
        *,
        state: HeaderState,
        level: int = 0,
    ) -> None:
        super().__init__()
        self.key = key
        self.title = title
        self.level = level
        self._state = state
        self.width = 0
        self.height = 0

    def wrap(self, availW, availH):  # noqa: N803 - ReportLab API
        return 0, 0

    def draw(self) -> None:
        self._state.current = self.title
        self._state.current_is_chapter = self.level >= 1
        self.canv.bookmarkPage(self.key)
        self.canv.addOutlineEntry(self.title, self.key, self.level, 0)


class FigureAnchor(Flowable):
    """Zero-height flowable that registers a named PDF destination.

    Unlike :class:`ChapterAnchor` it does NOT update the running header or
    add a PDF outline entry — figures appear in the table of contents'
    Figures section instead, and are linked there via plain
    ``<a href="#fig_key">`` markup.

    Attributes:
        key: PDF destination key (e.g. ``"fig_007"``).
    """

    def __init__(self, key: str) -> None:
        super().__init__()
        self.key = key
        self.width = 0
        self.height = 0

    def wrap(self, availW, availH):  # noqa: N803 - ReportLab API
        return 0, 0

    def draw(self) -> None:
        self.canv.bookmarkPage(self.key)


class BookmarkAnchor(Flowable):
    """Zero-height flowable that registers a generic PDF destination.

    Mechanically identical to :class:`FigureAnchor` (zero-height, calls
    ``canvas.bookmarkPage(self.key)`` at render time) but lives under a
    separate name so heading-level cross-reference targets stay
    distinguishable from figure anchors in stack traces, tests, and
    grep output. Used by the markdown parser to attach a bookmark to
    every H2/H3/H4 inside a chapter so ``[text](#fragment)`` and
    ``[text](other.md#fragment)`` cross-references resolve to the
    corresponding heading.

    Attributes:
        key: PDF destination key (e.g.
            ``"kv_cache__why-corpus-choice-matters"``).
    """

    def __init__(self, key: str) -> None:
        super().__init__()
        self.key = key
        self.width = 0
        self.height = 0

    def wrap(self, availW, availH):  # noqa: N803 - ReportLab API
        return 0, 0

    def draw(self) -> None:
        self.canv.bookmarkPage(self.key)


def _flowables_used_in_doctests() -> list[Flowable]:  # pragma: no cover
    """Helper for doctests / tests; not part of the public API."""
    state = HeaderState()
    return [
        ChapterAnchor("ch1", "Chapter 1", state=state, level=1),
        FigureAnchor("fig_001"),
        BookmarkAnchor("ch1__a-heading"),
    ]
