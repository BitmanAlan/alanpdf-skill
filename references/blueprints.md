# AlanPDF Blueprints

## Purpose

Use these blueprints to map business intent to layout behavior before rendering.

## `proposal`

Use for:

- 策划方案
- 白皮书
- 项目说明
- long-form consulting proposals
- strategy memos with comparison tables

Visual targets:

- Page 1 uses an integrated cover block plus the beginning of the document body.
- When `toc: true`, the first body area can begin with a compact executive-summary / content-navigation panel instead of a separate TOC page.
- Main title is left-aligned and heavy.
- Secondary Chinese title uses a lighter corporate blue.
- Metadata sits below the hero block in a compact stack.
- Section headings are dark navy with a thin blue underline.
- Tables use dark header rows and striped body rows.
- Callouts appear as tinted boxes with a left accent rule.

Recommended fields:

- `title`
- `subtitle`
- `doc-label`
- `version`
- `date`
- `confidentiality`
- `meta-label`

## `pricing-memo`

Use for:

- 费用说明
- 报价单
- 服务费用拆解
- 培训/顾问服务报价
- contract-adjacent pricing summaries

Visual targets:

- Page 1 uses a centered stacked cover block with generous whitespace.
- A small running label may appear at the top-right.
- Body starts with a large pricing summary table.
- Numeric columns read cleanly and align to the right.
- Totals rows use dark emphasis.
- Package-price rows use a green highlight.
- Disclaimers may be red and underlined near the end.

Recommended fields:

- `title`
- `subtitle`
- `doc-label`
- `author`
- `date`
- `meta-label`

## `equity-report`

Use for:

- 证券研究报告
- 投顾快评
- 行业/个股跟踪
- 首次覆盖 / 深度点评
- investment-advisory research notes

Visual targets:

- Page 1 uses an integrated research cover block plus the beginning of the body.
- When `toc: true`, integrated reports should prefer a compact navigation panel on page 1 over a ceremonial standalone TOC page.
- The upper section includes company/report title, a compact metadata line, and a four-column research summary strip.
- Body starts immediately with investment view rather than a ceremonial cover-only page.
- Forecast and valuation tables read as analytical artifacts, not generic markdown exports.
- Risk blocks are visually separated from normal narrative text.
- Compliance/disclaimer content is visually distinct and restrained.

Recommended fields:

- `title`
- `subtitle`
- `doc-label`
- `meta-label`
- `ticker`
- `industry`
- `rating`
- `target-price`
- `price-upside`
- `analyst`
- `date`
- `confidentiality`

## Table Conventions

Use plain Markdown tables when possible.

Add a marker above the table when the role matters:

```md
<!-- alanpdf: table=pricing -->
```

`pricing` behavior:

- Detect numeric columns and align them right.
- Emphasize rows containing `合计`, `总费用`, `项目总费用`, or similar markers.
- Highlight rows containing `合作打包价` or other recommendation markers.

`comparison` behavior:

- Keep strong header contrast.
- Preserve striped body rows.
- Favor readability over dense borders.

`valuation` / `forecast` behavior:

- Keep dense numeric columns right-aligned.
- Use restrained alternating fills.
- Favor analytical readability over decorative emphasis.

`peer-comparison` behavior:

- Keep peer rows neutral.
- Highlight the covered-company row when it is labeled as `覆盖标的`, `本公司`, or similar.

## Block Conventions

Use a marker above the next paragraph, list, or table when the content needs semantic styling:

```md
<!-- alanpdf: block=thesis -->
```

Supported block roles:

- `key-takeaway`: compact conclusion box
- `thesis`: investment or strategic thesis block
- `rating-box`: analyst view / stance summary; use `标签：值` bullets when you want KPI cards
- `risk-disclosure`: red-tinted risk warning block
- `disclaimer`: restrained legal/compliance-style warning block

## Figure Conventions

Use a figure marker when the report includes a chart, screenshot, or other visual that needs explicit caption/source treatment:

```md
<!-- alanpdf: figure path="figures/outlook.png" caption="图1：盈利预测与估值变化" source="公司公告，AlanPDF整理" fit=wide -->
```

Guidance:

- Prefer relative paths so the markdown stays portable.
- Keep captions short and analytical.
- Always provide a `source` line for research-style documents when the figure comes from an external dataset, company filing, or internal整理.
- Use `fit=narrow` for small supporting visuals and `fit=full` only when the figure is the main content unit of the page.

## Compact Navigation Guidance

For integrated blueprints, you can move navigation onto page 1 with frontmatter:

```yaml
toc: true
summary_points:
  - 第一条判断
  - 第二条判断
summary_note: 可选补充说明
```

This produces a compact navigation panel before the正文内容，而不是额外插入一个独立目录页。

## Authoring Guidance

- Prefer short business paragraphs over long essay blocks.
- Put the strongest statement near the top of each section.
- Use blockquotes for conclusions, recommendations, or “核心认知” callouts.
- Keep tables narrow enough to fit A4 without forcing tiny text.
- If a table becomes too dense, split it into two smaller tables instead of shrinking the type.
