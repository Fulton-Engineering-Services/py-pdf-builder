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

"""PDF report builders.

* :mod:`fes_pdf_builder.reports.base` — shared ``build_doc()`` driver, cover-page
  factory, part-divider factory.
* :mod:`fes_pdf_builder.reports.single_markdown` — generic single-file
  markdown → per-H2-chapter PDF builder.
"""

from __future__ import annotations

from .base import ReportContext, build_doc, concept_overview, cover_pages, part_divider
from .single_markdown import SingleMdConfig, build_single_markdown_pdf

__all__ = [
    "ReportContext",
    "SingleMdConfig",
    "build_doc",
    "build_single_markdown_pdf",
    "concept_overview",
    "cover_pages",
    "part_divider",
]
