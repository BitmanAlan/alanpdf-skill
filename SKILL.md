---
name: alanpdf
description: Generate business-grade PDFs from Markdown with scenario-driven document blueprints, especially for Chinese proposals, whitepapers, pricing memos, project费用说明,报价单,策划方案, securities research reports,投顾快评, and other table-heavy business documents. Use when the user wants a professionally typeset PDF that should feel like a consulting proposal, polished pricing memo, or broker-style research report rather than a generic markdown export.
---

# AlanPDF

## Overview

Use `alanpdf` for business documents where structure matters as much as color. This skill is optimized for continuous corporate documents with integrated cover blocks, restrained corporate styling, strong section hierarchy, scenario-specific content blocks, and tables that need numeric alignment and semantic emphasis.

Read [references/blueprints.md](references/blueprints.md) and [references/styles.md](references/styles.md) before collecting options or mapping the document.

## Workflow

1. Identify the source format.

- If the user already has Markdown, work directly from it.
- If the user provides a DOCX or PDF and wants to match its style, inspect that source first with the appropriate document skill before converting.

2. Choose the blueprint before discussing color/style details.

- `proposal`: for策划方案,方案书,白皮书,项目说明, long-form business narratives, comparison-heavy docs.
- `pricing-memo`: for费用说明,报价单,成本拆解,服务方案报价, contract-adjacent financial summaries.
- `equity-report`: for证券研究报告,投顾快评,行业/个股跟踪, investment-advisory writeups.

Then choose the style:

- `navy-consulting`
- `emerald-executive`
- `charcoal-minimal`
- `warm-whitepaper`
- `broker-classic`
- `sellside-slate`
- `ir-clean`

Then choose density when needed:

- `brief`: higher whitespace, faster executive reading
- `standard`
- `detailed`: tighter typesetting for denser reports

3. Ask for missing inputs in one pass.

Collect only the fields needed for the chosen blueprint:

- `title`
- `subtitle`
- `doc label`
- `author`
- `date`
- `version`
- `meta label`
- `confidentiality`
- optional watermark
- optional back-cover material

4. Normalize the Markdown to the selected blueprint.

- Treat `#` as a continuous section heading, not a forced chapter divider.
- Treat `##` as a subsection.
- Keep paragraphs concise and business-readable.
- Use Markdown tables for structured comparisons and fee breakdowns.
- Use blockquotes for boxed callouts and key conclusions.
- Prefer YAML frontmatter when the document carries reusable metadata such as `blueprint`, `style`, `density`, `ticker`, `rating`, `target_price`, `price_upside`, or `analyst`.

5. Add table markers when the intent is not obvious.

Insert a comment immediately above a table:

```md
<!-- alanpdf: table=pricing -->
| 项目 | 方案A | 方案B |
| --- | ---: | ---: |
| ... | ... | ... |
```

Supported roles:

- `pricing`: fee tables,报价表, totals rows, package-price rows
- `comparison`: side-by-side comparisons, feature matrices,方案对比
- `valuation`: valuation summary tables
- `forecast`: financial forecast / estimate tables
- `peer-comparison`: peer benchmark tables with target row emphasis
- `rating-history`: historical rating/action tables

6. Add semantic block markers when the document has scenario-specific highlight boxes.

```md
<!-- alanpdf: block=thesis -->
1. 海外渠道修复带动硬件收入恢复。
2. SaaS 与运维服务占比上升，毛利率中枢改善。

<!-- alanpdf: block=risk-disclosure -->
- 海外业务恢复慢于预期
- 汇率波动影响利润兑现
```

Supported roles:

- `key-takeaway`
- `thesis`
- `rating-box`
- `risk-disclosure`
- `disclaimer`

`rating-box` can also be authored as key-value bullets for KPI-style cards:

```md
<!-- alanpdf: block=rating-box -->
- 评级：增持
- 目标价：18.50元
- 收盘价：14.92元
- 预期空间：+24%
```

7. Add figure markers for charts, screenshots, or research figures that need caption and source lines.

```md
<!-- alanpdf: figure path="figures/revenue-outlook.png" caption="图1：收入与利润预测" source="公司公告，AlanPDF整理" fit=wide -->
```

Rules:

- `path` may be relative to the Markdown file location.
- Use `fit=full|wide|standard|narrow` when needed.
- Use figure markers for report figures that need explicit caption/source treatment, especially in research reports.

For integrated blueprints that need navigation on page 1 instead of a separate TOC page, enable `toc: true` in frontmatter and optionally add:

```yaml
summary_points:
  - 第一条高层判断
  - 第二条高层判断
summary_note: 可选说明
```

This creates a compact executive-summary / content-navigation panel ahead of the body rather than a standalone TOC page.

8. Prefer the deterministic renderer.

Run:

```bash
python3 scripts/alanpdf.py \
  --input input.md \
  --output output.pdf \
  --blueprint proposal \
  --style navy-consulting \
  --title "HarborGrid Operations Cloud" \
  --subtitle "港口与仓储一体化运营中台" \
  --doc-label "产品策划方案 · 实现思路 · 预算规划" \
  --meta-label "产品策划方案" \
  --version "V1.0" \
  --date "2026年4月" \
  --confidentiality "公开演示版"
```

For pricing memos:

```bash
python3 scripts/alanpdf.py \
  --input fee.md \
  --output fee.pdf \
  --blueprint pricing-memo \
  --style emerald-executive \
  --title "Astera Logistics" \
  --subtitle "AI 运营与决策赋能项目" \
  --doc-label "项目费用构成说明" \
  --meta-label "Astera Logistics AI 运营与决策赋能项目 · 项目费用说明" \
  --author "AlanPDF Demo Team" \
  --date "2026年4月"
```

For research reports:

```bash
python3 scripts/alanpdf.py \
  --input equity.md \
  --output equity.pdf \
  --blueprint equity-report \
  --style broker-classic \
  --density brief \
  --title "NovaForge Robotics" \
  --subtitle "首次覆盖报告" \
  --doc-label "智能制造行业 · 个股深度研究" \
  --meta-label "证券研究报告" \
  --ticker "NFRG.US" \
  --industry "工业机器人与智能制造" \
  --rating "增持" \
  --target-price "18.50元" \
  --price-upside "+24%" \
  --analyst "AlanPDF Research" \
  --date "2026年4月"
```

## Constraints

- Default to a concrete scenario blueprint first, then choose a style preset. Do not start with arbitrary theme exploration unless the user explicitly wants custom art direction.
- Default to `--toc false` for these business blueprints unless the document is long enough that a TOC adds real value.
- Keep ornament low. The target aesthetic is corporate, not editorial-artistic.
- When the content is mostly numeric, prioritize table clarity over decorative elements.
- If the system is missing `reportlab`, install it before rendering:

```bash
python3 -m pip install -r requirements.txt
```

## Resources

- [references/blueprints.md](references/blueprints.md): blueprint rules, visual targets, and authoring guidance.
- [references/styles.md](references/styles.md): color/style presets and when to use them.
- `scripts/alanpdf.py`: deterministic renderer based on `lovstudio/md2pdf`, adapted for business document blueprints.
