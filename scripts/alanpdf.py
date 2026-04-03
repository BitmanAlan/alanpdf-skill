#!/usr/bin/env python3
"""
alanpdf — Convert Markdown to business-grade PDF.

Features:
  - CJK/Latin mixed text with automatic font switching
  - Fenced code blocks with preserved indentation and line breaks
  - Markdown tables with business-aware alignment and totals-row emphasis
  - Integrated corporate cover blocks, clickable TOC, PDF bookmarks, page numbers
  - Frontispiece (full-page image after cover) and back cover (banner branding)
  - Configurable blueprints and themes
  - Watermark support
  - Running header with report title + chapter name
  - Footer with author/brand, page number, date

Usage:
  python alanpdf.py --input report.md --output report.pdf --blueprint proposal --style navy-consulting

Dependencies:
  pip install reportlab --break-system-packages
"""

import re, os, sys, json, argparse, shlex
from datetime import date
import yaml
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.units import mm
from reportlab.lib.colors import Color, HexColor, black, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak,
    Table, TableStyle, NextPageTemplate, Flowable, KeepTogether, CondPageBreak, Image
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ═══════════════════════════════════════════════════════════════════════
# FONTS — cross-platform font discovery (macOS / Linux / Windows)
# ═══════════════════════════════════════════════════════════════════════
import platform as _platform
_PLAT = _platform.system()  # "Darwin", "Linux", "Windows"

def _find_font(candidates):
    """Return first existing path from candidates list.
    Each candidate is either a string path or a (path, subfontIndex) tuple."""
    for c in candidates:
        path = c[0] if isinstance(c, tuple) else c
        if os.path.exists(path):
            return c
    return None

# Font candidates per role — ordered by preference, first match wins.
# Each role lists candidates for macOS, Windows, Linux in one flat list.
_FONT_CANDIDATES = {
    "Sans": [
        "/System/Library/Fonts/Supplemental/Arial.ttf",                          # macOS
        "C:/Windows/Fonts/arial.ttf",                                            # Windows
        "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf",               # Linux Debian
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",                   # Linux Noto
        "/usr/share/fonts/noto/NotoSans-Regular.ttf",                            # Linux Fedora
    ],
    "SansBold": [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/noto/NotoSans-Bold.ttf",
    ],
    "SansIt": [
        "/System/Library/Fonts/Supplemental/Arial Italic.ttf",
        "C:/Windows/Fonts/ariali.ttf",
        "/usr/share/fonts/truetype/crosextra/Carlito-Italic.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Italic.ttf",
    ],
    "SansBI": [
        "/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf",
        "C:/Windows/Fonts/arialbi.ttf",
        "/usr/share/fonts/truetype/crosextra/Carlito-BoldItalic.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-BoldItalic.ttf",
    ],
    "Serif": [
        ("/System/Library/Fonts/Palatino.ttc", 0),                               # macOS Palatino
        "C:/Windows/Fonts/times.ttf",                                            # Windows TNR
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",     # Linux
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSerif-Regular.ttf",
        "/usr/share/fonts/noto/NotoSerif-Regular.ttf",
    ],
    "SerifBold": [
        ("/System/Library/Fonts/Palatino.ttc", 2),
        "C:/Windows/Fonts/timesbd.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSerif-Bold.ttf",
    ],
    "SerifIt": [
        ("/System/Library/Fonts/Palatino.ttc", 1),
        "C:/Windows/Fonts/timesi.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Italic.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
    ],
    "SerifBI": [
        ("/System/Library/Fonts/Palatino.ttc", 3),
        "C:/Windows/Fonts/timesbi.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-BoldItalic.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf",
    ],
    "CJK": [
        ("/System/Library/Fonts/Supplemental/Songti.ttc", 0),                   # macOS Songti SC
        "C:/Windows/Fonts/simsun.ttc",                                           # Windows SimSun (宋体)
        "C:/Windows/Fonts/msyh.ttc",                                             # Windows MSYH (微软雅黑)
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",              # Linux Noto CJK
        "/usr/share/fonts/noto-cjk/NotoSerifCJK-Regular.ttc",                   # Linux Fedora
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",            # Linux Droid
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",                  # macOS fallback
    ],
    "CJKBold": [
        ("/System/Library/Fonts/Supplemental/Songti.ttc", 1),
        "C:/Windows/Fonts/simsunb.ttf",
        "C:/Windows/Fonts/msyhbd.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
        "/usr/share/fonts/noto-cjk/NotoSerifCJK-Bold.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    ],
    "Mono": [
        ("/System/Library/Fonts/Menlo.ttc", 0),                                  # macOS
        "C:/Windows/Fonts/consola.ttf",                                          # Windows Consolas
        "C:/Windows/Fonts/cour.ttf",                                             # Windows Courier New
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",                  # Linux
        "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",
    ],
    "MonoBold": [
        ("/System/Library/Fonts/Menlo.ttc", 1),
        "C:/Windows/Fonts/consolab.ttf",
        "C:/Windows/Fonts/courbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansMono-Bold.ttf",
    ],
}

def register_fonts():
    missing = []
    for name, candidates in _FONT_CANDIDATES.items():
        spec = _find_font(candidates)
        if spec is None:
            missing.append(name)
            continue
        try:
            if isinstance(spec, tuple):
                pdfmetrics.registerFont(TTFont(name, spec[0], subfontIndex=spec[1]))
            else:
                pdfmetrics.registerFont(TTFont(name, spec))
        except Exception as e:
            missing.append(name)
            print(f"Warning: Font {name} — {e}", file=sys.stderr)
    if missing:
        print(f"Warning: Missing fonts: {', '.join(missing)}. PDF may have □ characters.", file=sys.stderr)
        if _PLAT == "Linux":
            print("  Fix: sudo apt install fonts-noto fonts-noto-cjk fonts-dejavu-core", file=sys.stderr)
        elif _PLAT == "Windows":
            print("  Fix: Install Noto fonts from https://fonts.google.com/noto", file=sys.stderr)
    pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="SansBold",
                                  italic="SansIt", boldItalic="SansBI")
    pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="SerifBold",
                                  italic="SerifIt", boldItalic="SerifBI")

# ═══════════════════════════════════════════════════════════════════════
# THEMES — each theme has colors + layout for real typographic difference
# ═══════════════════════════════════════════════════════════════════════
# Layout keys:
#   margins: (left, right, top, bottom) in mm
#   body_font: "Serif" or "Sans"
#   body_size / body_leading: body text dimensions
#   h1_size / h2_size / h3_size: heading sizes
#   heading_align: TA_CENTER or TA_LEFT
#   heading_decoration: "rules" | "underline" | "dot" | "none"
#   header_style: "full" | "minimal" | "none"
#   code_style: "bg" (background fill) | "border" (left border only)
#   cover_style: "centered" | "left-aligned" | "minimal" | "proposal-integrated" | "pricing-integrated" | "research-integrated"
#   page_decoration: "none" | "top-bar" | "left-stripe" | "side-rule" | "corner-marks"
#   first_top_margin: first-page top margin in mm for integrated cover blueprints

_DEFAULT_LAYOUT = {
    "margins": (25, 22, 28, 25),
    "body_font": "Serif", "body_size": 10.5, "body_leading": 17,
    "h1_size": 26, "h2_size": 18, "h3_size": 12,
    "heading_align": "center", "heading_decoration": "rules",
    "header_style": "full", "code_style": "bg", "cover_style": "centered",
    "page_decoration": "none", "first_top_margin": None,
}

THEMES = {
    "warm-academic": {
        "canvas":"#F9F9F7","canvas_sec":"#F0EEE6","ink":"#181818","ink_faded":"#87867F",
        "accent":"#CC785C","accent_light":"#D99A82","border":"#E8E6DC",
        "watermark_rgba":(0.82,0.80,0.76,0.12),
        "layout": {
            "body_font":"Serif","body_size":10.5,"body_leading":17,
            "heading_align":"center","heading_decoration":"rules",
            "header_style":"full","code_style":"bg","cover_style":"centered",
            "page_decoration":"top-bar",
        }
    },
    "nord-frost": {
        "canvas":"#ECEFF4","canvas_sec":"#E5E9F0","ink":"#2E3440","ink_faded":"#4C566A",
        "accent":"#5E81AC","accent_light":"#81A1C1","border":"#D8DEE9",
        "watermark_rgba":(0.74,0.78,0.85,0.10),
        "layout": {
            "body_font":"Sans","body_size":10,"body_leading":16,
            "h3_size":11,"heading_align":"left","heading_decoration":"underline",
            "header_style":"minimal","code_style":"border","cover_style":"left-aligned",
            "page_decoration":"left-stripe",
        }
    },
    "github-light": {
        "canvas":"#FFFFFF","canvas_sec":"#F6F8FA","ink":"#1F2328","ink_faded":"#656D76",
        "accent":"#0969DA","accent_light":"#218BFF","border":"#D0D7DE",
        "watermark_rgba":(0.80,0.82,0.85,0.08),
        "layout": {
            "body_font":"Sans","body_size":10,"body_leading":16.5,
            "heading_align":"left","heading_decoration":"none",
            "header_style":"minimal","code_style":"bg","cover_style":"left-aligned",
            "page_decoration":"left-stripe",
        }
    },
    "solarized-light": {
        "canvas":"#FDF6E3","canvas_sec":"#EEE8D5","ink":"#657B83","ink_faded":"#93A1A1",
        "accent":"#CB4B16","accent_light":"#DC322F","border":"#EEE8D5",
        "watermark_rgba":(0.85,0.82,0.72,0.10),
    },
    "paper-classic": {
        "canvas":"#FFFFFF","canvas_sec":"#FAFAFA","ink":"#000000","ink_faded":"#666666",
        "accent":"#CC0000","accent_light":"#FF3333","border":"#DDDDDD",
        "watermark_rgba":(0.85,0.85,0.85,0.08),
    },
    "ocean-breeze": {
        "canvas":"#F0F7F4","canvas_sec":"#E0EDE8","ink":"#1A2E35","ink_faded":"#5A7D7C",
        "accent":"#2A9D8F","accent_light":"#64CCBF","border":"#C8DDD6",
        "watermark_rgba":(0.75,0.85,0.80,0.10),
        "layout": {
            "body_font":"Sans","body_size":10.5,"body_leading":17,
            "heading_align":"left","heading_decoration":"underline",
            "header_style":"full","code_style":"bg","cover_style":"centered",
            "page_decoration":"top-bar",
        }
    },
    "monokai-warm": {
        "canvas":"#272822","canvas_sec":"#1E1F1C","ink":"#F8F8F2","ink_faded":"#75715E",
        "accent":"#F92672","accent_light":"#FD971F","border":"#49483E",
        "watermark_rgba":(0.30,0.30,0.28,0.08),
    },
    "dracula-soft": {
        "canvas":"#282A36","canvas_sec":"#21222C","ink":"#F8F8F2","ink_faded":"#6272A4",
        "accent":"#BD93F9","accent_light":"#FF79C6","border":"#44475A",
        "watermark_rgba":(0.35,0.30,0.45,0.08),
    },
    # --- Inspired by classic LaTeX templates ---
    "tufte": {
        "canvas":"#FFFFF8","canvas_sec":"#F7F7F0","ink":"#111111","ink_faded":"#999988",
        "accent":"#980000","accent_light":"#C04040","border":"#E0DDD0",
        "watermark_rgba":(0.88,0.87,0.82,0.08),
        "layout": {
            "margins":(30, 55, 25, 25),  # wide right margin (Tufte sidenote style)
            "body_font":"Serif","body_size":11,"body_leading":18,
            "h1_size":24,"h2_size":16,"h3_size":11,
            "heading_align":"left","heading_decoration":"none",
            "header_style":"none","code_style":"border","cover_style":"minimal",
            "page_decoration":"side-rule",
        }
    },
    "classic-thesis": {
        "canvas":"#FEFEFE","canvas_sec":"#F5F2EB","ink":"#2B2B2B","ink_faded":"#7A7568",
        "accent":"#8B4513","accent_light":"#A0522D","border":"#D6CFC2",
        "watermark_rgba":(0.82,0.78,0.72,0.10),
        "layout": {
            "body_font":"Serif","body_size":10.5,"body_leading":17,
            "h1_size":28,"h2_size":20,
            "heading_align":"center","heading_decoration":"rules",
            "header_style":"full","code_style":"bg","cover_style":"centered",
            "page_decoration":"corner-marks",
        }
    },
    "ieee-journal": {
        "canvas":"#FFFFFF","canvas_sec":"#F5F5F5","ink":"#000000","ink_faded":"#555555",
        "accent":"#003366","accent_light":"#336699","border":"#CCCCCC",
        "watermark_rgba":(0.82,0.82,0.82,0.08),
        "layout": {
            "margins":(20, 20, 22, 20),  # tight margins like journal papers
            "body_font":"Serif","body_size":9.5,"body_leading":14,
            "h1_size":22,"h2_size":14,"h3_size":11,
            "heading_align":"left","heading_decoration":"underline",
            "header_style":"minimal","code_style":"border","cover_style":"left-aligned",
            "page_decoration":"top-band",
        }
    },
    "elegant-book": {
        "canvas":"#FBF9F1","canvas_sec":"#F0ECE0","ink":"#1A1A1A","ink_faded":"#6E6B5E",
        "accent":"#5B3A29","accent_light":"#7D5642","border":"#DDD8C8",
        "watermark_rgba":(0.85,0.82,0.75,0.10),
        "layout": {
            "margins":(28, 24, 30, 28),  # generous margins for book feel
            "body_font":"Serif","body_size":10.5,"body_leading":18,
            "h1_size":28,"h2_size":20,
            "heading_align":"center","heading_decoration":"dot",
            "header_style":"full","code_style":"bg","cover_style":"centered",
            "page_decoration":"double-rule",
        }
    },
    "chinese-red": {
        "canvas":"#FFFDF5","canvas_sec":"#F8F0E0","ink":"#1A1009","ink_faded":"#8C7A5E",
        "accent":"#B22222","accent_light":"#D44040","border":"#E8DCC8",
        "watermark_rgba":(0.88,0.82,0.72,0.10),
        "layout": {
            "body_font":"Serif","body_size":11,"body_leading":18,
            "h1_size":28,"h2_size":20,
            "heading_align":"center","heading_decoration":"rules",
            "header_style":"full","code_style":"bg","cover_style":"centered",
            "page_decoration":"top-bar",
        }
    },
    "ink-wash": {
        "canvas":"#F8F6F0","canvas_sec":"#EEEAE0","ink":"#2C2C2C","ink_faded":"#8A8A80",
        "accent":"#404040","accent_light":"#666660","border":"#D8D4C8",
        "watermark_rgba":(0.80,0.80,0.76,0.10),
        "layout": {
            "margins":(30, 30, 30, 28),  # symmetric, generous whitespace
            "body_font":"Serif","body_size":10.5,"body_leading":18,
            "h1_size":24,"h2_size":16,"h3_size":11,
            "heading_align":"center","heading_decoration":"dot",
            "header_style":"none","code_style":"border","cover_style":"minimal",
            "page_decoration":"none",
        }
    },
    "alan-proposal": {
        "canvas":"#FFFFFF","canvas_sec":"#F5F8FB","ink":"#1B3A5C","ink_faded":"#667085",
        "accent":"#2E75B6","accent_light":"#A9C3DD","border":"#D0D5DD",
        "success":"#4EA72E","callout_bg":"#F5F8FB",
        "watermark_rgba":(0.85,0.89,0.94,0.07),
        "layout": {
            "margins":(24, 20, 24, 20),
            "body_font":"Sans","body_size":10,"body_leading":16,
            "h1_size":18,"h2_size":18,"h3_size":14,
            "heading_align":"left","heading_decoration":"underline",
            "header_style":"full","code_style":"bg","cover_style":"proposal-integrated",
            "page_decoration":"none","first_top_margin":145,
        }
    },
    "alan-pricing": {
        "canvas":"#FFFFFF","canvas_sec":"#F5F8FB","ink":"#1B3A5C","ink_faded":"#667085",
        "accent":"#2E75B6","accent_light":"#A9C3DD","border":"#D0D5DD",
        "success":"#4EA72E","callout_bg":"#F7FAFC",
        "watermark_rgba":(0.85,0.89,0.94,0.05),
        "layout": {
            "margins":(24, 20, 24, 20),
            "body_font":"Sans","body_size":10,"body_leading":16,
            "h1_size":18,"h2_size":18,"h3_size":14,
            "heading_align":"left","heading_decoration":"underline",
            "header_style":"minimal","code_style":"bg","cover_style":"pricing-integrated",
            "page_decoration":"none","first_top_margin":132,
        }
    },
    "alan-research": {
        "canvas":"#FFFFFF","canvas_sec":"#F6F8FB","ink":"#142B4D","ink_faded":"#5B667A",
        "accent":"#255C99","accent_light":"#B2C7E0","border":"#D7DFEA",
        "success":"#3A7A5E","callout_bg":"#F4F7FB",
        "watermark_rgba":(0.84,0.88,0.94,0.05),
        "layout": {
            "margins":(22, 20, 22, 18),
            "body_font":"Sans","body_size":9.6,"body_leading":15.5,
            "h1_size":18,"h2_size":18,"h3_size":13.5,
            "heading_align":"left","heading_decoration":"underline",
            "header_style":"minimal","code_style":"bg","cover_style":"research-integrated",
            "page_decoration":"none","first_top_margin":118,
        }
    },
}

def load_theme(name, theme_file=None):
    if theme_file and os.path.exists(theme_file):
        with open(theme_file) as f:
            t = json.load(f)
    elif name in THEMES:
        t = THEMES[name]
    else:
        print(f"Unknown theme '{name}', falling back to warm-academic", file=sys.stderr)
        t = THEMES["warm-academic"]
    # Merge layout with defaults
    layout = dict(_DEFAULT_LAYOUT)
    layout.update(t.get("layout", {}))
    return {
        "canvas":    HexColor(t["canvas"]),
        "canvas_sec":HexColor(t["canvas_sec"]),
        "ink":       HexColor(t["ink"]),
        "ink_faded": HexColor(t["ink_faded"]),
        "accent":    HexColor(t["accent"]),
        "accent_light":HexColor(t.get("accent_light", t["accent"])),
        "border":    HexColor(t["border"]),
        "success":   HexColor(t.get("success", t.get("accent_light", t["accent"]))),
        "danger":    HexColor(t.get("danger", "#B42318")),
        "danger_bg": HexColor(t.get("danger_bg", "#FEF3F2")),
        "callout_bg":HexColor(t.get("callout_bg", t["canvas_sec"])),
        "wm_color":  Color(*t.get("watermark_rgba", (0.82,0.80,0.76,0.12))),
        "layout":    layout,
    }

BLUEPRINTS = {
    "proposal": {
        "theme": "alan-proposal",
        "style": "navy-consulting",
        "toc": False,
        "header_title_mode": "meta",
        "meta_label": "产品策划方案",
        "doc_label": "产品策划方案 · 实现思路 · 预算规划",
        "confidentiality": "保密文件",
    },
    "pricing-memo": {
        "theme": "alan-pricing",
        "style": "navy-consulting",
        "toc": False,
        "header_title_mode": "meta",
        "meta_label": "项目费用说明",
        "doc_label": "项目费用构成说明",
        "confidentiality": "",
    },
    "equity-report": {
        "theme": "alan-research",
        "style": "broker-classic",
        "density": "standard",
        "toc": False,
        "header_title_mode": "meta",
        "meta_label": "证券研究报告",
        "doc_label": "行业/个股跟踪简报",
        "confidentiality": "仅供机构客户参考",
    },
}

TOTAL_ROW_MARKERS = (
    "合计", "总计", "费用合计", "项目总费用", "总费用", "总报价", "总额"
)
EMPHASIS_ROW_MARKERS = ("合作打包价", "推荐方案", "推荐", "建议方案")
FOCUS_ROW_MARKERS = ("本公司", "覆盖标的", "目标公司", "研究标的")
BLOCK_ROLES = ("key-takeaway", "thesis", "risk-disclosure", "rating-box", "disclaimer")
PUBLIC_BLUEPRINTS = ("proposal", "pricing-memo", "equity-report")

STYLE_PRESETS = {
    "navy-consulting": {
        "canvas": "#FFFFFF",
        "canvas_sec": "#F5F8FB",
        "ink": "#1B3A5C",
        "ink_faded": "#667085",
        "accent": "#2E75B6",
        "accent_light": "#A9C3DD",
        "border": "#D0D5DD",
        "success": "#4EA72E",
        "danger": "#B42318",
        "danger_bg": "#FEF3F2",
        "callout_bg": "#F5F8FB",
        "watermark_rgba": (0.85, 0.89, 0.94, 0.06),
    },
    "emerald-executive": {
        "canvas": "#FCFFFE",
        "canvas_sec": "#F1F8F6",
        "ink": "#163A37",
        "ink_faded": "#5F766E",
        "accent": "#0F8A70",
        "accent_light": "#9FD6C7",
        "border": "#C9DDD7",
        "success": "#2D9D78",
        "danger": "#B54708",
        "danger_bg": "#FFF7ED",
        "callout_bg": "#F1F8F6",
        "watermark_rgba": (0.78, 0.88, 0.85, 0.06),
    },
    "charcoal-minimal": {
        "canvas": "#FFFFFF",
        "canvas_sec": "#F6F7F9",
        "ink": "#232B35",
        "ink_faded": "#6B7280",
        "accent": "#48576A",
        "accent_light": "#B8C0CA",
        "border": "#D9DEE5",
        "success": "#64748B",
        "danger": "#B42318",
        "danger_bg": "#F8F1F1",
        "callout_bg": "#F6F7F9",
        "watermark_rgba": (0.82, 0.84, 0.87, 0.05),
    },
    "warm-whitepaper": {
        "canvas": "#FFFCF7",
        "canvas_sec": "#F7F2EA",
        "ink": "#3B312A",
        "ink_faded": "#7A6E63",
        "accent": "#A86A3B",
        "accent_light": "#D8B89A",
        "border": "#E3D5C6",
        "success": "#8A9465",
        "danger": "#B24A3A",
        "danger_bg": "#FDF3EF",
        "callout_bg": "#FBF6EE",
        "watermark_rgba": (0.89, 0.84, 0.77, 0.06),
    },
    "broker-classic": {
        "canvas": "#FFFFFF",
        "canvas_sec": "#F3F7FC",
        "ink": "#0F2747",
        "ink_faded": "#62748A",
        "accent": "#0B5CAD",
        "accent_light": "#B8D1EA",
        "border": "#D1D9E6",
        "success": "#2F855A",
        "danger": "#C53030",
        "danger_bg": "#FFF5F5",
        "callout_bg": "#F3F7FC",
        "watermark_rgba": (0.82, 0.88, 0.95, 0.05),
    },
    "sellside-slate": {
        "canvas": "#FFFFFF",
        "canvas_sec": "#F4F6F8",
        "ink": "#1E293B",
        "ink_faded": "#64748B",
        "accent": "#334155",
        "accent_light": "#CBD5E1",
        "border": "#D7DEE7",
        "success": "#3F7D58",
        "danger": "#B91C1C",
        "danger_bg": "#FEF2F2",
        "callout_bg": "#F4F6F8",
        "watermark_rgba": (0.84, 0.86, 0.90, 0.05),
    },
    "ir-clean": {
        "canvas": "#FFFFFF",
        "canvas_sec": "#F2FAFA",
        "ink": "#163043",
        "ink_faded": "#5E7282",
        "accent": "#0E7490",
        "accent_light": "#B6E0E6",
        "border": "#D2E4E8",
        "success": "#1F8A70",
        "danger": "#B54708",
        "danger_bg": "#FFF7ED",
        "callout_bg": "#F2FAFA",
        "watermark_rgba": (0.82, 0.92, 0.92, 0.05),
    },
}

SUPPORTED_BLUEPRINT_CHOICES = PUBLIC_BLUEPRINTS
SUPPORTED_STYLE_CHOICES = tuple(STYLE_PRESETS.keys())

DENSITY_PRESETS = {
    "brief": {
        "layout": {
            "body_size": 10.4,
            "body_leading": 16.8,
            "h1_size": 19,
            "h2_size": 18.5,
            "h3_size": 14.2,
        }
    },
    "standard": {
        "layout": {}
    },
    "detailed": {
        "layout": {
            "body_size": 9.4,
            "body_leading": 14.8,
            "h1_size": 17.5,
            "h2_size": 17,
            "h3_size": 13,
        }
    },
}

SUPPORTED_DENSITY_CHOICES = tuple(DENSITY_PRESETS.keys())


def apply_style(theme, style_name):
    if not style_name:
        return theme
    style = STYLE_PRESETS.get(style_name)
    if not style:
        print(f"Unknown style '{style_name}', keeping base theme", file=sys.stderr)
        return theme

    styled = dict(theme)
    styled["layout"] = dict(theme["layout"])
    for key, value in style.items():
        if key == "watermark_rgba":
            styled["wm_color"] = Color(*value)
        elif key == "layout":
            styled["layout"].update(value)
        else:
            styled_key = {
                "canvas": "canvas",
                "canvas_sec": "canvas_sec",
                "ink": "ink",
                "ink_faded": "ink_faded",
                "accent": "accent",
                "accent_light": "accent_light",
                "border": "border",
                "success": "success",
                "danger": "danger",
                "danger_bg": "danger_bg",
                "callout_bg": "callout_bg",
            }.get(key)
            if styled_key:
                styled[styled_key] = HexColor(value)
    return styled


def apply_density(theme, density_name):
    density = DENSITY_PRESETS.get(density_name)
    if not density or density_name == "standard":
        return theme

    resolved = dict(theme)
    resolved["layout"] = dict(theme["layout"])
    resolved["layout"].update(density.get("layout", {}))
    return resolved


def parse_frontmatter(md_text):
    if not md_text.startswith("---\n"):
        return {}, md_text
    match = re.match(r"^---\n(.*?)\n---\n?", md_text, re.DOTALL)
    if not match:
        return {}, md_text
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except Exception:
        return {}, md_text
    if not isinstance(data, dict):
        return {}, md_text
    body = md_text[match.end():]
    return data, body


def _coerce_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("1", "true", "yes", "y", "on"):
            return True
        if lowered in ("0", "false", "no", "n", "off"):
            return False
    return default


def _normalize_string_list(value):
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    parts = re.split(r'(?:\r?\n)+|[；;]+', text)
    return [part.strip(" -•\t") for part in parts if part.strip(" -•\t")]


def _parse_alanpdf_directive(text):
    match = re.match(r'^<!--\s*alanpdf:\s*(.+?)\s*-->$', text)
    if not match:
        return None
    directive = {}
    try:
        tokens = shlex.split(match.group(1))
    except Exception:
        tokens = match.group(1).split()
    for token in tokens:
        if '=' in token:
            key, value = token.split('=', 1)
            directive[key.strip()] = value.strip()
        else:
            directive[token.strip()] = True
    return directive or None

# ═══════════════════════════════════════════════════════════════════════
# CJK DETECTION + FONT WRAPPING
# ═══════════════════════════════════════════════════════════════════════
_CJK_RANGES = [
    (0x4E00,0x9FFF),(0x3400,0x4DBF),(0xF900,0xFAFF),(0x3000,0x303F),
    (0xFF00,0xFFEF),(0x2E80,0x2EFF),(0x2F00,0x2FDF),(0xFE30,0xFE4F),
    (0x20000,0x2A6DF),(0x2A700,0x2B73F),(0x2B740,0x2B81F),
]

def _is_cjk(ch):
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in _CJK_RANGES)

def _font_wrap(text):
    """Wrap CJK runs in <font name='CJK'> tags for reportlab Paragraph."""
    out, buf, in_cjk = [], [], False
    for ch in text:
        c = _is_cjk(ch)
        if c != in_cjk and buf:
            seg = ''.join(buf)
            out.append(f"<font name='CJK'>{seg}</font>" if in_cjk else seg)
            buf = []
        buf.append(ch); in_cjk = c
    if buf:
        seg = ''.join(buf)
        out.append(f"<font name='CJK'>{seg}</font>" if in_cjk else seg)
    return ''.join(out)

def _mixed_segments(text, latin_font="Sans", cjk_font="CJK"):
    segs, buf, in_cjk = [], [], False
    for ch in text:
        cj = _is_cjk(ch)
        if cj != in_cjk and buf:
            segs.append((cjk_font if in_cjk else latin_font, ''.join(buf)))
            buf = []
        buf.append(ch)
        in_cjk = cj
    if buf:
        segs.append((cjk_font if in_cjk else latin_font, ''.join(buf)))
    return segs

def _mixed_width(c, text, size, latin_font="Sans", cjk_font="CJK"):
    return sum(c.stringWidth(txt, font, size) for font, txt in _mixed_segments(text, latin_font, cjk_font))

def _draw_mixed(c, x, y, text, size, anchor="left"):
    """Draw mixed CJK/Latin text on canvas with font switching."""
    segs = _mixed_segments(text)
    total_w = sum(c.stringWidth(t, f, size) for f, t in segs)
    if anchor == "right": x -= total_w
    elif anchor == "center": x -= total_w / 2
    for font, txt in segs:
        c.setFont(font, size); c.drawString(x, y, txt)
        x += c.stringWidth(txt, font, size)

def _draw_label_chip(c, x, y, text, fill, text_color=white, stroke=None, anchor="left",
                     size=7.2, pad_x=3.0*mm, height=6.0*mm):
    width = _mixed_width(c, text, size) + pad_x * 2
    x0 = x
    if anchor == "right":
        x0 = x - width
    elif anchor == "center":
        x0 = x - width / 2
    c.saveState()
    c.setFillColor(fill)
    if stroke:
        c.setStrokeColor(stroke)
        c.setLineWidth(0.5)
        c.roundRect(x0, y, width, height, 1.6*mm, fill=1, stroke=1)
    else:
        c.roundRect(x0, y, width, height, 1.6*mm, fill=1, stroke=0)
    c.setFillColor(text_color)
    _draw_mixed(c, x0 + pad_x, y + 1.7*mm, text, size, anchor="left")
    c.restoreState()
    return x0 + width

def _draw_chip_row(c, x, y, items, fill, text_color=white, stroke=None, gap=2.2*mm, anchor="left", size=7.2):
    labels = [item for item in items if item]
    if not labels:
        return x
    widths = [_mixed_width(c, item, size) + 3.0*mm * 2 for item in labels]
    total = sum(widths) + gap * (len(widths) - 1)
    cursor = x
    if anchor == "right":
        cursor = x - total
    elif anchor == "center":
        cursor = x - total / 2
    for item in labels:
        cursor = _draw_label_chip(c, cursor, y, item, fill=fill, text_color=text_color,
                                  stroke=stroke, anchor="left", size=size)
        cursor += gap
    return cursor

def _draw_mixed_segs(c, x, y, segs):
    """Draw pre-defined (font, text, size) segments on canvas.
    Used for mixed-font subtitle rendering."""
    total_w = sum(c.stringWidth(txt, font, sz) for font, txt, sz in segs)
    x = x - total_w / 2  # always centered
    for font, txt, sz in segs:
        c.setFont(font, sz)
        c.drawString(x, y, txt)
        x += c.stringWidth(txt, font, sz)

# ═══════════════════════════════════════════════════════════════════════
# INLINE MARKDOWN + ESCAPING
# ═══════════════════════════════════════════════════════════════════════
def esc(text):
    return text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def esc_code(text):
    """Escape for code blocks: preserve indentation and newlines."""
    out = []
    for line in text.split('\n'):
        e = esc(line)
        stripped = e.lstrip(' ')
        indent = len(e) - len(stripped)
        out.append('&nbsp;' * indent + stripped)
    return '<br/>'.join(out)

def md_inline(text, accent_hex="#CC785C"):
    text = esc(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'`(.+?)`',
        rf"<font name='Mono' size='8' color='{accent_hex}'>\1</font>", text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'<u>\1</u>', text)
    return _font_wrap(text)


def _clean_cell_text(text):
    return re.sub(r'\s+', '', text or "")


def _looks_numeric(text):
    cleaned = _clean_cell_text(text).replace("¥", "").replace("￥", "").replace(",", "")
    cleaned = cleaned.replace("元", "").replace("%", "").replace("h", "").replace("H", "")
    cleaned = cleaned.replace("天", "").replace("小时", "").replace("个月", "").replace("次", "")
    if cleaned in ("", "—", "-", "N/A", "n/a"):
        return False
    return bool(re.fullmatch(r"-?\d+(?:\.\d+)?", cleaned))


def _is_total_row(row):
    joined = " ".join(row)
    return any(marker in joined for marker in TOTAL_ROW_MARKERS)


def _is_emphasis_row(row):
    joined = " ".join(row)
    return any(marker in joined for marker in EMPHASIS_ROW_MARKERS)


def _is_focus_row(row):
    lead = row[0] if row else ""
    return any(marker in lead for marker in FOCUS_ROW_MARKERS)


def _weighted_col_widths(avail, weights, min_w=16*mm):
    if not weights:
        return []
    total = sum(weights) or 1
    widths = [avail * w / total for w in weights]
    for idx in range(len(widths)):
        if widths[idx] < min_w:
            deficit = min_w - widths[idx]
            widths[idx] = min_w
            donors = sorted(range(len(widths)), key=lambda i: -widths[i])
            for donor in donors:
                if donor != idx and widths[donor] - deficit > min_w:
                    widths[donor] -= deficit
                    break
    return widths


def _table_col_widths(role, nc, header, data, avail):
    if nc <= 0:
        return []
    if role == "pricing":
        presets = {
            3: [0.34, 0.42, 0.24],
            4: [0.20, 0.44, 0.14, 0.22],
            5: [0.18, 0.34, 0.14, 0.14, 0.20],
        }
        if nc in presets:
            return _weighted_col_widths(avail, presets[nc])
    if role == "comparison":
        if nc == 3:
            return _weighted_col_widths(avail, [0.24, 0.38, 0.38])
        if nc >= 4:
            return _weighted_col_widths(avail, [0.22] + [0.78 / (nc - 1)] * (nc - 1))
    if role == "valuation":
        if nc == 3:
            return _weighted_col_widths(avail, [0.22, 0.50, 0.28])
    if role == "forecast":
        return _weighted_col_widths(avail, [0.34] + [0.66 / (nc - 1)] * (nc - 1))
    if role == "peer-comparison":
        return _weighted_col_widths(avail, [0.34] + [0.66 / (nc - 1)] * (nc - 1))
    if role == "rating-history":
        if nc >= 4:
            return _weighted_col_widths(avail, [0.16, 0.16, 0.30] + [0.38 / (nc - 3)] * (nc - 3))

    max_lens = [max((len(r[ci]) if ci < len(r) else 0) for r in [header] + data) for ci in range(nc)]
    max_lens = [max(m, 2) for m in max_lens]
    if nc > 1:
        max_lens[0] = int(max_lens[0] * 1.18)
    return _weighted_col_widths(avail, max_lens, min_w=18*mm)

# ═══════════════════════════════════════════════════════════════════════
# CUSTOM FLOWABLES
# ═══════════════════════════════════════════════════════════════════════
_anchor_counter = [0]
_outline_level = [-1]
_cur_chapter = [""]

class ChapterMark(Flowable):
    width = height = 0
    def __init__(self, t, level=0):
        Flowable.__init__(self); self.title = t; self.level = level
        _anchor_counter[0] += 1; self.key = f"anchor_{_anchor_counter[0]}"
    def draw(self):
        _cur_chapter[0] = self.title
        self.canv.bookmarkPage(self.key)
        target = min(self.level, _outline_level[0] + 1)
        _outline_level[0] = target
        self.canv.addOutlineEntry(self.title, self.key, level=target, closed=(target==0))

class HRule(Flowable):
    def __init__(self, w, thick=0.5, clr=None):
        Flowable.__init__(self)
        self.width = w; self.height = 4*mm; self._t = thick; self._c = clr or HexColor("#E8E6DC")
    def draw(self):
        self.canv.setStrokeColor(self._c); self.canv.setLineWidth(self._t)
        self.canv.line(0, 2*mm, self.width, 2*mm)

class HRuleCentered(Flowable):
    """Horizontally centered rule within the frame width."""
    def __init__(self, frame_w, rule_w, thick=0.5, clr=None):
        Flowable.__init__(self)
        self.width = frame_w; self.height = 4*mm
        self._rw = rule_w; self._t = thick; self._c = clr or HexColor("#E8E6DC")
    def draw(self):
        self.canv.setStrokeColor(self._c); self.canv.setLineWidth(self._t)
        x0 = (self.width - self._rw) / 2
        self.canv.line(x0, 2*mm, x0 + self._rw, 2*mm)

class ClayDot(Flowable):
    """Small accent-colored dot separator."""
    def __init__(self, w, clr=None):
        Flowable.__init__(self)
        self.width = w; self.height = 6*mm
        self._c = clr or HexColor("#CC785C")
    def draw(self):
        self.canv.setFillColor(self._c)
        cx = self.width / 2
        self.canv.circle(cx, 3*mm, 1.5*mm, fill=1, stroke=0)

class LeftBorderParagraph(Flowable):
    """Paragraph with a left accent border line (for code blocks in 'border' style)."""
    def __init__(self, para, border_color, border_width=2):
        Flowable.__init__(self)
        self._para = para
        self._bc = border_color; self._bw = border_width
    def wrap(self, aw, ah):
        w, h = self._para.wrap(aw, ah)
        self.width = w; self.height = h
        return w, h
    def draw(self):
        self._para.drawOn(self.canv, 0, 0)
        self.canv.setStrokeColor(self._bc); self.canv.setLineWidth(self._bw)
        self.canv.line(2, -2, 2, self.height + 2)

# ═══════════════════════════════════════════════════════════════════════
# PDF BUILDER
# ═══════════════════════════════════════════════════════════════════════
class PDFBuilder:
    def __init__(self, config):
        self.cfg = config
        self.T = config["theme"]  # resolved theme colors
        self.L = self.T["layout"]  # layout parameters
        self.page_w, self.page_h = config["page_size"]
        lm, rm, tm, bm = self.L["margins"]
        self.lm, self.rm, self.tm, self.bm = lm*mm, rm*mm, tm*mm, bm*mm
        self.body_w = self.page_w - self.lm - self.rm
        self.body_h = self.page_h - self.tm - self.bm
        self.accent_hex = config.get("accent_hex", "#CC785C")
        self.ST = self._build_styles()

    def _build_styles(self):
        T = self.T; L = self.L
        s = {}
        bf = L["body_font"]  # "Serif" or "Sans"
        bs, bl = L["body_size"], L["body_leading"]
        h_align = TA_CENTER if L["heading_align"] == "center" else TA_LEFT
        s['part'] = ParagraphStyle('Part', fontName="Serif", fontSize=L["h1_size"],
            leading=L["h1_size"]+10, textColor=T["ink"], alignment=h_align,
            spaceBefore=0, spaceAfter=0)
        s['chapter'] = ParagraphStyle('Ch', fontName="Serif", fontSize=L["h2_size"],
            leading=L["h2_size"]+8, textColor=T["ink"], alignment=h_align,
            spaceBefore=0, spaceAfter=0)
        s['h3'] = ParagraphStyle('H3', fontName="SansBold", fontSize=L["h3_size"],
            leading=L["h3_size"]+5, textColor=T["accent"], alignment=TA_LEFT,
            spaceBefore=10, spaceAfter=4)
        s['body'] = ParagraphStyle('Body', fontName=bf, fontSize=bs, leading=bl,
            textColor=T["ink"], alignment=TA_LEFT, spaceBefore=2, spaceAfter=5,
            wordWrap='CJK')
        s['body_indent'] = ParagraphStyle('BI', parent=s['body'],
            leftIndent=14, rightIndent=14, textColor=T["ink_faded"],
            borderColor=T["accent"], borderWidth=0, borderPadding=4)
        s['bullet'] = ParagraphStyle('Bul', fontName=bf, fontSize=bs, leading=bl,
            textColor=T["ink"], alignment=TA_LEFT, spaceBefore=1, spaceAfter=1,
            leftIndent=18, bulletIndent=6, wordWrap='CJK')
        # Code block: "bg" = background fill, "border" = left accent line (no bg)
        self._code_style_type = L["code_style"]
        if L["code_style"] == "border":
            s['code'] = ParagraphStyle('Code', fontName="Mono", fontSize=7.5, leading=10.5,
                textColor=HexColor("#3D3D3A"), alignment=TA_LEFT, spaceBefore=4, spaceAfter=4,
                leftIndent=14, rightIndent=8, backColor=None,
                borderColor=None, borderWidth=0, borderPadding=6)
        else:
            s['code'] = ParagraphStyle('Code', fontName="Mono", fontSize=7.5, leading=10.5,
                textColor=HexColor("#3D3D3A"), alignment=TA_LEFT, spaceBefore=4, spaceAfter=4,
                leftIndent=8, rightIndent=8, backColor=T["canvas_sec"],
                borderColor=T["border"], borderWidth=0.5, borderPadding=6)
        s['toc1'] = ParagraphStyle('T1', fontName="Serif", fontSize=12, leading=20,
            textColor=T["ink"], leftIndent=0, spaceBefore=6, spaceAfter=2)
        s['toc2'] = ParagraphStyle('T2', fontName="Sans", fontSize=10, leading=16,
            textColor=T["ink_faded"], leftIndent=16, spaceBefore=1, spaceAfter=1)
        s['th'] = ParagraphStyle('TH', fontName="SansBold", fontSize=8.7, leading=12,
            textColor=white, alignment=TA_CENTER)
        s['tc'] = ParagraphStyle('TC', fontName="Sans", fontSize=8.2, leading=11.4,
            textColor=T["ink"], alignment=TA_LEFT)
        s['tc_num'] = ParagraphStyle('TCN', parent=s['tc'], alignment=TA_RIGHT)
        s['tc_center'] = ParagraphStyle('TCC', parent=s['tc'], alignment=TA_CENTER)
        s['callout'] = ParagraphStyle('Callout', parent=s['body'], textColor=T["ink"],
            alignment=TA_LEFT, spaceBefore=0, spaceAfter=0, leading=bl)
        s['block_label'] = ParagraphStyle('BlockLabel', fontName="SansBold", fontSize=7.5,
            leading=9, textColor=T["ink_faded"], alignment=TA_LEFT, spaceBefore=0, spaceAfter=4)
        s['block_label_danger'] = ParagraphStyle('BlockLabelDanger', parent=s['block_label'],
            textColor=T["danger"])
        s['body_small'] = ParagraphStyle('BodySmall', parent=s['body'],
            fontSize=max(bs - 0.6, 8.6), leading=max(bl - 1.5, 12),
            textColor=T["ink_faded"])
        s['body_strong'] = ParagraphStyle('BodyStrong', parent=s['body'],
            fontName="SansBold", alignment=TA_LEFT)
        s['figure_caption'] = ParagraphStyle('FigureCaption', parent=s['body_small'],
            textColor=T["ink"], fontName="SansBold", spaceBefore=3, spaceAfter=1.5)
        s['figure_source'] = ParagraphStyle('FigureSource', parent=s['body_small'],
            textColor=T["ink_faded"], spaceBefore=0, spaceAfter=0.5)
        s['figure_note'] = ParagraphStyle('FigureNote', parent=s['body_small'],
            textColor=T["ink_faded"], spaceBefore=0.5, spaceAfter=0)
        s['metric_label'] = ParagraphStyle('MetricLabel', parent=s['body_small'],
            fontSize=max(bs - 1.0, 8.0), leading=max(bl - 2.6, 11),
            textColor=T["ink_faded"], spaceBefore=0, spaceAfter=1)
        s['metric_value'] = ParagraphStyle('MetricValue', parent=s['body_strong'],
            fontSize=max(bs + 0.7, 10.2), leading=max(bl - 1.0, 13.5),
            textColor=T["ink"], spaceBefore=0, spaceAfter=0)
        s['nav_title'] = ParagraphStyle('NavTitle', parent=s['h3'],
            fontName="SansBold", fontSize=max(L["h3_size"] - 0.8, 12.4),
            leading=max(L["h3_size"] + 3.2, 15.5), textColor=T["ink"],
            spaceBefore=0, spaceAfter=2)
        s['nav_note'] = ParagraphStyle('NavNote', parent=s['body_small'],
            spaceBefore=0.5, spaceAfter=0)
        s['nav_index'] = ParagraphStyle('NavIndex', parent=s['body_small'],
            fontName="SansBold", textColor=T["accent"], alignment=TA_LEFT,
            spaceBefore=0, spaceAfter=0)
        s['nav_entry'] = ParagraphStyle('NavEntry', parent=s['body_small'],
            fontName="SansBold", textColor=T["ink"], leading=max(bl - 1.0, 13))
        s['nav_entry_minor'] = ParagraphStyle('NavEntryMinor', parent=s['body_small'],
            textColor=T["ink_faded"], leading=max(bl - 1.4, 12.5))
        return s

    def _block_spec(self, role):
        specs = {
            "key-takeaway": {
                "label": "核心结论",
                "bg": self.T["callout_bg"],
                "line": self.T["accent"],
                "label_style": self.ST["block_label"],
            },
            "thesis": {
                "label": "投资要点",
                "bg": self.T["callout_bg"],
                "line": self.T["accent"],
                "label_style": self.ST["block_label"],
            },
            "rating-box": {
                "label": "评级观点",
                "bg": self.T["canvas_sec"],
                "line": self.T["accent"],
                "label_style": self.ST["block_label"],
            },
            "risk-disclosure": {
                "label": "风险提示",
                "bg": self.T["danger_bg"],
                "line": self.T["danger"],
                "label_style": self.ST["block_label_danger"],
            },
            "disclaimer": {
                "label": "免责声明",
                "bg": self.T["danger_bg"],
                "line": self.T["danger"],
                "label_style": self.ST["block_label_danger"],
            },
        }
        return specs.get(role)

    def _plain_text_from_flowable(self, flowable):
        getter = getattr(flowable, "getPlainText", None)
        if callable(getter):
            try:
                return getter() or ""
            except Exception:
                return ""
        return ""

    def _extract_rating_box_metrics(self, flowables):
        metrics = []
        residual = []
        for flow in flowables:
            text = self._plain_text_from_flowable(flow).strip()
            if not text:
                residual.append(flow)
                continue
            cleaned = re.sub(r'^[\u2022\-\*\d\.\)\s]+', '', text).strip()
            match = re.match(r'^([^:：]{1,24})[:：]\s*(.+)$', cleaned)
            if match:
                metrics.append((match.group(1).strip(), match.group(2).strip()))
            else:
                residual.append(flow)
        return metrics, residual

    def _build_metric_grid(self, metrics):
        if not metrics:
            return None
        cols = 2 if len(metrics) > 4 else min(max(len(metrics), 1), 4)
        gap = 3*mm
        col_w = (self.body_w - 2*mm - gap * (cols - 1)) / cols
        rows = []
        current = []
        for label, value in metrics:
            content = [
                Paragraph(md_inline(label, self.accent_hex), self.ST['metric_label']),
                Paragraph(md_inline(value, self.accent_hex), self.ST['metric_value']),
            ]
            cell = Table([[content]], colWidths=[col_w])
            cell.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), white),
                ('BOX', (0, 0), (-1, -1), 0.55, self.T["border"]),
                ('LEFTPADDING', (0, 0), (-1, -1), 7),
                ('RIGHTPADDING', (0, 0), (-1, -1), 7),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            current.append(cell)
            if len(current) == cols:
                rows.append(current)
                current = []
        if current:
            while len(current) < cols:
                current.append("")
            rows.append(current)
        grid = Table(rows, colWidths=[col_w] * cols, hAlign='LEFT')
        grid.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), gap),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        return grid

    def _build_compact_nav(self, toc):
        entries = toc[:max(int(self.cfg.get("nav_max_items", 8) or 8), 1)]
        if not entries:
            return []

        parts = [Spacer(1, 2*mm)]
        summary_title = self.cfg.get("summary_title", "执行摘要")
        summary_points = self.cfg.get("summary_points", [])
        summary_note = self.cfg.get("summary_note", "")
        if summary_points:
            summary_flows = [Paragraph(_font_wrap(esc(summary_title)), self.ST['block_label'])]
            summary_flows.extend(
                Paragraph(f"\u2022  {md_inline(item, self.accent_hex)}", self.ST['bullet'])
                for item in summary_points
            )
            if summary_note:
                summary_flows.append(Paragraph(md_inline(summary_note, self.accent_hex), self.ST['nav_note']))
            summary_box = Table([[summary_flows]], colWidths=[self.body_w - 2*mm])
            summary_box.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), self.T["callout_bg"]),
                ('BOX', (0, 0), (-1, -1), 0.8, self.T["border"]),
                ('LINEBEFORE', (0, 0), (0, -1), 2.0, self.T["accent"]),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            parts.extend([summary_box, Spacer(1, 3*mm)])

        parts.append(Paragraph(_font_wrap(esc(self.cfg.get("nav_title", "内容导览"))), self.ST['nav_title']))
        parts.append(HRule(self.body_w * 0.1, 0.9, self.T["accent"]))
        parts.append(Spacer(1, 2.2*mm))

        ink = self.T["ink"]
        ink_hex = f"#{int(ink.red*255):02x}{int(ink.green*255):02x}{int(ink.blue*255):02x}" if hasattr(ink, 'red') else "#181818"
        rows = []
        for idx, (etype, title, key) in enumerate(entries, start=1):
            style = self.ST['nav_entry'] if etype == 'part' else self.ST['nav_entry_minor']
            linked = f"<a href=\"#{key}\" color=\"{ink_hex}\">{_font_wrap(esc(title))}</a>"
            rows.append([
                Paragraph(f"{idx:02d}", self.ST['nav_index']),
                Paragraph(linked, style),
            ])
        nav_table = Table(rows, colWidths=[12*mm, self.body_w - 12*mm], hAlign='LEFT')
        nav_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        parts.append(nav_table)

        if len(toc) > len(entries):
            remaining = len(toc) - len(entries)
            parts.extend([
                Spacer(1, 1.5*mm),
                Paragraph(md_inline(f"其余 {remaining} 个章节请在正文中继续阅读。", self.accent_hex), self.ST['nav_note']),
            ])

        return [CondPageBreak(38*mm)] + parts + [Spacer(1, 3*mm)]

    def _wrap_semantic_block(self, role, flowables):
        spec = self._block_spec(role)
        if not spec:
            return flowables
        content = list(flowables)
        if role == "rating-box":
            metrics, residual = self._extract_rating_box_metrics(flowables)
            if metrics:
                content = list(residual)
                metric_grid = self._build_metric_grid(metrics)
                if metric_grid:
                    if content:
                        content.append(Spacer(1, 2*mm))
                    content.append(metric_grid)
        label = Paragraph(_font_wrap(esc(spec["label"])), spec["label_style"])
        content = [label] + content
        box = Table([[content]], colWidths=[self.body_w - 2*mm])
        box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), spec["bg"]),
            ('BOX', (0, 0), (-1, -1), 0.8, self.T["border"]),
            ('LINEBEFORE', (0, 0), (0, -1), 2.0, spec["line"]),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        return [CondPageBreak(22*mm), Spacer(1, 2*mm), box, Spacer(1, 2*mm)]

    def _resolve_asset_path(self, path):
        if not path:
            return ""
        if os.path.isabs(path):
            return path
        base_dir = self.cfg.get("base_dir", "")
        if base_dir:
            return os.path.normpath(os.path.join(base_dir, path))
        return path

    def _build_figure_flowables(self, directive):
        src = directive.get("path") or directive.get("src")
        if not src:
            return []

        resolved = self._resolve_asset_path(str(src))
        if not os.path.exists(resolved):
            print(f"Warning: Figure asset not found: {resolved}", file=sys.stderr)
            return []

        fit = str(directive.get("fit", "wide")).lower()
        max_width = {
            "full": self.body_w,
            "wide": self.body_w * 0.96,
            "standard": self.body_w * 0.84,
            "narrow": self.body_w * 0.68,
        }.get(fit, self.body_w * 0.96)
        max_height = {
            "full": 98*mm,
            "wide": 90*mm,
            "standard": 78*mm,
            "narrow": 64*mm,
        }.get(fit, 90*mm)
        align = str(directive.get("align", "center")).lower()

        img = Image(resolved)
        iw = float(getattr(img, "imageWidth", 0) or 0)
        ih = float(getattr(img, "imageHeight", 0) or 0)
        if iw <= 0 or ih <= 0:
            return []
        scale = min(max_width / iw, max_height / ih, 1.0)
        img.drawWidth = iw * scale
        img.drawHeight = ih * scale
        img.hAlign = "CENTER" if align == "center" else "LEFT"

        caption = str(directive.get("caption", "")).strip()
        source = str(directive.get("source", "")).strip()
        note = str(directive.get("note", "")).strip()
        if source and not re.match(r'^(资料来源|来源|Source)\s*[:：]', source, re.IGNORECASE):
            source = f"资料来源：{source}"

        flows = [CondPageBreak(max_height + 20*mm), Spacer(1, 2*mm), img]
        if caption:
            flows.append(Spacer(1, 1.5*mm))
            flows.append(Paragraph(md_inline(caption, self.accent_hex), self.ST['figure_caption']))
        if source:
            flows.append(Paragraph(md_inline(source, self.accent_hex), self.ST['figure_source']))
        if note:
            flows.append(Paragraph(md_inline(note, self.accent_hex), self.ST['figure_note']))
        flows.append(Spacer(1, 2*mm))
        return [KeepTogether(flows)]

    # ── Page callbacks ──
    def _draw_bg(self, c):
        c.setFillColor(self.T["canvas"])
        c.rect(0, 0, self.page_w, self.page_h, fill=1, stroke=0)

    def _cover_page(self, c, doc):
        c.saveState(); self._draw_bg(c)
        T = self.T; cx = self.page_w / 2
        cover = self.L["cover_style"]

        if cover == "proposal-integrated":
            self._cover_embedded_proposal(c, T)
        elif cover == "pricing-integrated":
            self._cover_embedded_pricing(c, T)
        elif cover == "research-integrated":
            self._cover_embedded_research(c, T)
        elif cover == "left-aligned":
            self._cover_left_aligned(c, T, cx)
        elif cover == "minimal":
            self._cover_minimal(c, T, cx)
        else:
            self._cover_centered(c, T, cx)

        c.restoreState()

    def _cover_centered(self, c, T, cx):
        """Classic centered cover with accent bars and rule."""
        # Top accent bar
        c.setFillColor(T["accent"])
        c.rect(0, self.page_h - 3*mm, self.page_w, 3*mm, fill=1, stroke=0)

        title_y = self.page_h * 0.62
        c.setFillColor(T["ink"])
        _draw_mixed(c, cx, title_y, self.cfg.get("title", "Document"), 38, anchor="center")

        ver = self.cfg.get("version", "")
        if ver:
            c.setFillColor(T["accent"]); c.setFont("Sans", 13)
            c.drawCentredString(cx, title_y - 30, ver)

        rule_y = title_y - 52
        c.setStrokeColor(T["accent"]); c.setLineWidth(1.5)
        c.line(cx - 17*mm, rule_y, cx + 17*mm, rule_y)

        sub = self.cfg.get("subtitle", "")
        sub_segs = self.cfg.get("subtitle_segs")
        if sub_segs:
            c.setFillColor(T["ink_faded"]); _draw_mixed_segs(c, cx, rule_y - 32, sub_segs)
        elif sub:
            c.setFillColor(T["ink"]); _draw_mixed(c, cx, rule_y - 32, sub, 20, anchor="center")

        stats = self.cfg.get("stats_line", "")
        stats2 = self.cfg.get("stats_line2", "")
        if stats or stats2:
            c.setFillColor(T["ink_faded"]); stats_y = rule_y - 72
            if stats: _draw_mixed(c, cx, stats_y, stats, 9.5, anchor="center")
            if stats2: _draw_mixed(c, cx, stats_y - 18, stats2, 9.5, anchor="center")

        c.setStrokeColor(T["border"]); c.setLineWidth(0.5)
        c.line(self.lm + 20*mm, 52*mm, self.page_w - self.rm - 20*mm, 52*mm)

        author = self.cfg.get("author", "")
        if author:
            c.setFillColor(T["ink_faded"]); _draw_mixed(c, cx, 38*mm, author, 10, anchor="center")

        dt = self.cfg.get("date", str(date.today()))
        c.setFillColor(T["ink_faded"]); _draw_mixed(c, cx, 28*mm, dt, 9, anchor="center")

        edition = self.cfg.get("edition_line", "")
        if edition:
            c.setFillColor(T["ink_faded"]); _draw_mixed(c, cx, 20*mm, edition, 7.5, anchor="center")

        c.setFillColor(T["accent"])
        c.rect(0, 0, self.page_w, 3*mm, fill=1, stroke=0)

    def _cover_left_aligned(self, c, T, cx):
        """Modern left-aligned cover (GitHub/IEEE style)."""
        # Thick left accent stripe
        c.setFillColor(T["accent"])
        c.rect(0, 0, 6*mm, self.page_h, fill=1, stroke=0)

        lx = 25*mm  # left text x
        title_y = self.page_h * 0.58
        c.setFillColor(T["ink"])
        _draw_mixed(c, lx, title_y, self.cfg.get("title", "Document"), 34, anchor="left")

        ver = self.cfg.get("version", "")
        if ver:
            c.setFillColor(T["accent"]); c.setFont("Sans", 12)
            c.drawString(lx, title_y - 28, ver)

        # Accent underline
        c.setStrokeColor(T["accent"]); c.setLineWidth(2)
        c.line(lx, title_y - 42, lx + 50*mm, title_y - 42)

        sub = self.cfg.get("subtitle", "")
        sub_segs = self.cfg.get("subtitle_segs")
        if sub_segs:
            c.setFillColor(T["ink_faded"]); _draw_mixed_segs(c, lx + 40*mm, title_y - 62, sub_segs)
        elif sub:
            c.setFillColor(T["ink_faded"]); _draw_mixed(c, lx, title_y - 62, sub, 16, anchor="left")

        stats = self.cfg.get("stats_line", "")
        stats2 = self.cfg.get("stats_line2", "")
        if stats or stats2:
            c.setFillColor(T["ink_faded"]); stats_y = title_y - 100
            if stats: _draw_mixed(c, lx, stats_y, stats, 9, anchor="left")
            if stats2: _draw_mixed(c, lx, stats_y - 16, stats2, 9, anchor="left")

        # Bottom left info block
        author = self.cfg.get("author", "")
        if author:
            c.setFillColor(T["ink_faded"]); _draw_mixed(c, lx, 38*mm, author, 10, anchor="left")
        dt = self.cfg.get("date", str(date.today()))
        c.setFillColor(T["ink_faded"]); _draw_mixed(c, lx, 28*mm, dt, 9, anchor="left")

        edition = self.cfg.get("edition_line", "")
        if edition:
            c.setFillColor(T["ink_faded"]); _draw_mixed(c, lx, 20*mm, edition, 7.5, anchor="left")

    def _cover_minimal(self, c, T, cx):
        """Minimal cover (Tufte/ink-wash style) — lots of whitespace, no bars."""
        title_y = self.page_h * 0.50
        c.setFillColor(T["ink"])
        _draw_mixed(c, cx, title_y, self.cfg.get("title", "Document"), 32, anchor="center")

        sub = self.cfg.get("subtitle", "")
        sub_segs = self.cfg.get("subtitle_segs")
        if sub_segs:
            c.setFillColor(T["ink_faded"]); _draw_mixed_segs(c, cx, title_y - 36, sub_segs)
        elif sub:
            c.setFillColor(T["ink_faded"]); _draw_mixed(c, cx, title_y - 36, sub, 16, anchor="center")

        ver = self.cfg.get("version", "")
        if ver:
            c.setFillColor(T["ink_faded"]); c.setFont("Sans", 10)
            c.drawCentredString(cx, title_y - 60, ver)

        # Simple thin rule
        c.setStrokeColor(T["border"]); c.setLineWidth(0.3)
        c.line(cx - 25*mm, title_y - 75, cx + 25*mm, title_y - 75)

        author = self.cfg.get("author", "")
        if author:
            c.setFillColor(T["ink_faded"]); _draw_mixed(c, cx, 35*mm, author, 10, anchor="center")
        dt = self.cfg.get("date", str(date.today()))
        c.setFillColor(T["ink_faded"]); _draw_mixed(c, cx, 25*mm, dt, 9, anchor="center")

    def _cover_embedded_proposal(self, c, T):
        """Business proposal cover block that shares page 1 with content."""
        lx = self.lm
        rx = self.page_w - self.rm
        title_y = self.page_h - 78*mm
        meta_label = self.cfg.get("meta_label", "")
        if meta_label:
            _draw_label_chip(c, lx, self.page_h - 16*mm, meta_label, fill=T["accent"],
                             text_color=white, anchor="left", size=7.0)

        c.setFillColor(T["ink"])
        _draw_mixed(c, lx, title_y, self.cfg.get("title", "Document"), 26, anchor="left")

        subtitle = self.cfg.get("subtitle", "")
        if subtitle:
            c.setFillColor(T["accent"])
            _draw_mixed(c, lx, title_y - 12*mm, subtitle, 18, anchor="left")

        doc_label = self.cfg.get("doc_label", "")
        if doc_label:
            c.setFillColor(T["ink_faded"])
            _draw_mixed(c, lx, title_y - 26*mm, doc_label, 11.5, anchor="left")

        chips = [
            f"版本 {self.cfg.get('version', '')}" if self.cfg.get("version", "") else "",
            f"日期 {self.cfg.get('date', str(date.today()))}" if self.cfg.get("date", "") else "",
            self.cfg.get("confidentiality", ""),
        ]
        _draw_chip_row(c, lx, title_y - 40*mm, chips, fill=T["canvas_sec"], text_color=T["ink"],
                       stroke=T["border"], anchor="left", size=7.2)

        footer_bits = [part for part in (self.cfg.get("footer_left", ""), self.cfg.get("date", "")) if part]
        if footer_bits:
            c.setFillColor(T["ink_faded"])
            _draw_mixed(c, rx, 34*mm, " · ".join(footer_bits), 7.5, anchor="right")

        c.setStrokeColor(T["border"]); c.setLineWidth(0.7)
        rule_y = self.page_h - (self.L.get("first_top_margin") or 118) * mm + 3*mm
        c.line(self.lm, rule_y, self.page_w - self.rm, rule_y)

    def _cover_embedded_pricing(self, c, T):
        """Centered pricing memo cover block that shares page 1 with content."""
        cx = self.page_w / 2
        meta_label = self.cfg.get("meta_label", "")
        if meta_label:
            _draw_label_chip(c, self.page_w - self.rm, self.page_h - 16*mm, meta_label,
                             fill=T["accent"], text_color=white, anchor="right", size=7.0)

        top_y = self.page_h - 62*mm
        c.setFillColor(T["ink"])
        _draw_mixed(c, cx, top_y, self.cfg.get("title", "Document"), 24, anchor="center")

        subtitle = self.cfg.get("subtitle", "")
        if subtitle:
            c.setFillColor(T["accent"])
            _draw_mixed(c, cx, top_y - 12*mm, subtitle, 20, anchor="center")

        doc_label = self.cfg.get("doc_label", "")
        if doc_label:
            c.setFillColor(T["ink"])
            _draw_mixed(c, cx, top_y - 42*mm, doc_label, 18, anchor="center")

        author = self.cfg.get("author", "")
        chips = [
            f"负责人 {author}" if author else "",
            self.cfg.get("date", str(date.today())),
            self.cfg.get("confidentiality", ""),
        ]
        _draw_chip_row(c, cx, top_y - 88*mm, chips, fill=T["canvas_sec"], text_color=T["ink"],
                       stroke=T["border"], anchor="center", size=7.1)

    def _cover_embedded_research(self, c, T):
        """Research report cover block that shares page 1 with content."""
        lx = self.lm
        rx = self.page_w - self.rm
        top_y = self.page_h - 42*mm

        meta_label = self.cfg.get("meta_label", "")
        if meta_label:
            _draw_label_chip(c, rx, self.page_h - 16*mm, meta_label, fill=T["accent"],
                             text_color=white, anchor="right", size=7.0)

        title = self.cfg.get("title", "Document")
        subtitle = self.cfg.get("subtitle", "")
        doc_label = self.cfg.get("doc_label", "")
        ticker = self.cfg.get("ticker", "")
        industry = self.cfg.get("industry", "")
        rating = self.cfg.get("rating", "")
        target_price = self.cfg.get("target_price", "")
        price_upside = self.cfg.get("price_upside", "")
        analyst = self.cfg.get("analyst", "") or self.cfg.get("author", "")

        c.setFillColor(T["ink"])
        _draw_mixed(c, lx, top_y, title, 22, anchor="left")
        if subtitle:
            c.setFillColor(T["accent"])
            _draw_mixed(c, lx, top_y - 10*mm, subtitle, 15.5, anchor="left")

        id_line = " · ".join([part for part in (doc_label, ticker, industry) if part])
        if id_line:
            c.setFillColor(T["ink_faded"])
            _draw_mixed(c, lx, top_y - 18*mm, id_line, 9.5, anchor="left")

        strip_y = top_y - 36*mm
        strip_h = 22*mm
        c.setFillColor(T["canvas_sec"])
        c.roundRect(lx, strip_y, self.body_w, strip_h, 2*mm, fill=1, stroke=0)

        items = [
            ("评级", rating or "未评级"),
            ("目标价", target_price or "—"),
            ("空间", price_upside or "—"),
            ("分析师", analyst or "—"),
        ]
        col_w = self.body_w / len(items)
        for idx, (label, value) in enumerate(items):
            x0 = lx + idx * col_w
            if idx:
                c.setStrokeColor(T["border"])
                c.setLineWidth(0.4)
                c.line(x0, strip_y + 3*mm, x0, strip_y + strip_h - 3*mm)
            c.setFillColor(T["ink_faded"])
            _draw_mixed(c, x0 + 4*mm, strip_y + strip_h - 7*mm, label, 7.5, anchor="left")
            c.setFillColor(T["accent"] if idx < 3 else T["ink"])
            _draw_mixed(c, x0 + 4*mm, strip_y + 7*mm, value, 10.5, anchor="left")

        footer_bits = [part for part in (
            self.cfg.get("date", str(date.today())),
            self.cfg.get("confidentiality", ""),
        ) if part]
        if footer_bits:
            c.setFillColor(T["ink_faded"])
            _draw_mixed(c, lx, strip_y - 8*mm, " · ".join(footer_bits), 8.5, anchor="left")

        c.setStrokeColor(T["border"])
        c.setLineWidth(0.7)
        rule_y = self.page_h - (self.L.get("first_top_margin") or 118) * mm + 3*mm
        c.line(self.lm, rule_y, self.page_w - self.rm, rule_y)

    def _first_page(self, c, doc):
        self._draw_bg(c)
        c.saveState()
        c.setFillColor(self.T["accent"])
        c.rect(0, self.page_h - 2.2*mm, self.page_w, 2.2*mm, fill=1, stroke=0)
        cover = self.L["cover_style"]
        if cover == "proposal-integrated":
            self._cover_embedded_proposal(c, self.T)
        elif cover == "pricing-integrated":
            self._cover_embedded_pricing(c, self.T)
        elif cover == "research-integrated":
            self._cover_embedded_research(c, self.T)
        else:
            self._normal_page(c, doc)
            c.restoreState()
            return

        pg = c.getPageNumber()
        c.setFillColor(self.T["ink_faded"]); c.setFont("Sans", 8)
        c.drawCentredString(self.page_w/2, self.bm - 12*mm, str(pg))
        c.restoreState()

    def _frontispiece_page(self, c, doc):
        """Full-page image page after cover."""
        c.saveState(); self._draw_bg(c)
        fp = self.cfg.get("frontispiece", "")
        if fp and os.path.exists(fp):
            margin = 18*mm
            avail_w = self.page_w - 2 * margin
            avail_h = self.page_h - 2 * margin
            try:
                c.drawImage(fp, margin, margin, width=avail_w, height=avail_h,
                            preserveAspectRatio=True, anchor='c', mask='auto')
            except Exception:
                pass
        c.restoreState()

    def _backcover_page(self, c, doc):
        """Back cover with banner branding."""
        c.saveState(); self._draw_bg(c)
        T = self.T; cx = self.page_w / 2

        # Top accent
        c.setFillColor(T["accent"])
        c.rect(0, self.page_h - 3*mm, self.page_w, 3*mm, fill=1, stroke=0)

        # Banner image — centered
        banner = self.cfg.get("banner", "")
        if banner and os.path.exists(banner):
            cy = self.page_h / 2
            banner_w = 150*mm
            banner_h = banner_w / 2.57
            banner_x = (self.page_w - banner_w) / 2
            banner_y = cy - banner_h / 2 + 15*mm
            try:
                c.drawImage(banner, banner_x, banner_y, width=banner_w,
                            height=banner_h, preserveAspectRatio=True, mask='auto')
            except Exception:
                pass

        # Bottom disclaimer
        disclaimer = self.cfg.get("disclaimer", "")
        if disclaimer:
            c.setFillColor(T["ink_faded"])
            _draw_mixed(c, cx, 32*mm, disclaimer, 8.5, anchor="center")

        # Copyright
        copyright_text = self.cfg.get("copyright", "")
        if copyright_text:
            c.setFillColor(T["ink_faded"])
            _draw_mixed(c, cx, 20*mm, copyright_text, 8.5, anchor="center")

        # Bottom accent
        c.setFillColor(T["accent"])
        c.rect(0, 0, self.page_w, 3*mm, fill=1, stroke=0)

        c.restoreState()

    def _draw_page_decoration(self, c):
        """Draw theme-specific page decorations visible even at thumbnail size."""
        T = self.T; deco = self.L.get("page_decoration", "none")
        if deco == "top-bar":
            # Thin accent bar at very top of page
            c.setFillColor(T["accent"])
            c.rect(0, self.page_h - 2.5*mm, self.page_w, 2.5*mm, fill=1, stroke=0)
        elif deco == "left-stripe":
            # Thick colored stripe on left edge
            c.setFillColor(T["accent"])
            c.rect(0, 0, 5*mm, self.page_h, fill=1, stroke=0)
        elif deco == "side-rule":
            # Thin vertical rule on left side (Tufte-style margin line)
            c.setStrokeColor(T["border"]); c.setLineWidth(0.4)
            c.line(self.lm - 5*mm, self.bm, self.lm - 5*mm, self.page_h - self.tm + 5*mm)
        elif deco == "corner-marks":
            # Decorative corner brackets
            c.setStrokeColor(T["accent"]); c.setLineWidth(0.8)
            m = 12*mm; clen = 12*mm
            # Top-left
            c.line(m, self.page_h - m, m + clen, self.page_h - m)
            c.line(m, self.page_h - m, m, self.page_h - m - clen)
            # Top-right
            c.line(self.page_w - m, self.page_h - m, self.page_w - m - clen, self.page_h - m)
            c.line(self.page_w - m, self.page_h - m, self.page_w - m, self.page_h - m - clen)
            # Bottom-left
            c.line(m, m, m + clen, m)
            c.line(m, m, m, m + clen)
            # Bottom-right
            c.line(self.page_w - m, m, self.page_w - m - clen, m)
            c.line(self.page_w - m, m, self.page_w - m, m + clen)
        elif deco == "top-band":
            # Wide accent band at top (IEEE-style)
            c.setFillColor(T["accent"])
            c.rect(0, self.page_h - 8*mm, self.page_w, 8*mm, fill=1, stroke=0)
            # White text header inside band
            header_title = self.cfg.get("header_title", "")
            if header_title:
                c.setFillColor(white)
                _draw_mixed(c, self.lm, self.page_h - 6*mm, header_title, 7.5)
            ch = _cur_chapter[0]
            if ch:
                c.setFillColor(white)
                _draw_mixed(c, self.page_w - self.rm, self.page_h - 6*mm, ch[:40], 7.5, anchor="right")
        elif deco == "double-rule":
            # Double horizontal rules at top and bottom (elegant book style)
            c.setStrokeColor(T["accent"]); c.setLineWidth(0.6)
            y_top = self.page_h - 14*mm
            c.line(self.lm, y_top, self.page_w - self.rm, y_top)
            c.line(self.lm, y_top - 2*mm, self.page_w - self.rm, y_top - 2*mm)
            y_bot = self.bm - 4*mm
            c.line(self.lm, y_bot, self.page_w - self.rm, y_bot)
            c.line(self.lm, y_bot + 2*mm, self.page_w - self.rm, y_bot + 2*mm)

    def _normal_page(self, c, doc):
        self._draw_bg(c); pg = c.getPageNumber()
        c.saveState()
        T = self.T; hs = self.L["header_style"]

        # Page decoration (drawn first, behind content)
        self._draw_page_decoration(c)

        # Watermark
        wm = self.cfg.get("watermark", "")
        if wm:
            c.setFont("CJK", 52); c.setFillColor(T["wm_color"])
            c.translate(self.page_w/2, self.page_h/2); c.rotate(35)
            for dy in range(-300, 400, 160):
                for dx in range(-400, 500, 220):
                    c.drawCentredString(dx, dy, wm)
            c.rotate(-35); c.translate(-self.page_w/2, -self.page_h/2)

        # Header (skip if top-band decoration already drew header)
        deco = self.L.get("page_decoration", "none")
        if hs == "full" and deco != "top-band":
            c.setStrokeColor(T["border"]); c.setLineWidth(0.5)
            c.line(self.lm, self.page_h - 20*mm, self.page_w - self.rm, self.page_h - 20*mm)
            c.setFillColor(T["ink_faded"])
            header_title = self.cfg.get("header_title", "")
            if header_title:
                _draw_mixed(c, self.lm, self.page_h - 18*mm, header_title, 8)
            ch = _cur_chapter[0]
            if ch:
                _draw_mixed(c, self.page_w - self.rm, self.page_h - 18*mm, ch[:40], 8, anchor="right")
        elif hs == "minimal" and deco != "top-band":
            c.setFillColor(T["ink_faded"]); c.setFont("Sans", 8)
            c.drawRightString(self.page_w - self.rm, self.page_h - 16*mm, str(pg))

        # Footer (skip line if double-rule decoration already drew it)
        if hs != "none" and deco not in ("double-rule",):
            c.setStrokeColor(T["border"])
            c.line(self.lm, self.bm - 8*mm, self.page_w - self.rm, self.bm - 8*mm)

        # Footer center: page number
        if hs == "full":
            c.setFillColor(T["accent"]); c.setFont("Serif", 9)
            c.drawCentredString(self.page_w/2, self.bm - 16*mm, f"\u2014  {pg}  \u2014")
        elif hs == "minimal":
            c.setFillColor(T["ink_faded"]); c.setFont("Sans", 8)
            c.drawCentredString(self.page_w/2, self.bm - 14*mm, str(pg))
        elif hs == "none":
            c.setFillColor(T["ink_faded"]); c.setFont("Serif", 8)
            c.drawCentredString(self.page_w/2, self.bm - 10*mm, str(pg))

        # Footer left/right
        if hs == "full":
            footer_left = self.cfg.get("footer_left", self.cfg.get("author", ""))
            if footer_left:
                c.setFillColor(T["ink_faded"])
                _draw_mixed(c, self.lm, self.bm - 16*mm, footer_left, 8)
            c.setFillColor(T["ink_faded"])
            _draw_mixed(c, self.page_w - self.rm, self.bm - 16*mm,
                        self.cfg.get("date", str(date.today())), 8, anchor="right")
        c.restoreState()

    def _toc_page(self, c, doc):
        self._draw_bg(c); pg = c.getPageNumber()
        c.saveState()
        T = self.T

        # Header line
        c.setStrokeColor(T["border"]); c.setLineWidth(0.5)
        c.line(self.lm, self.page_h - 20*mm, self.page_w - self.rm, self.page_h - 20*mm)
        c.setFillColor(T["ink_faded"])

        # Header left: report title
        header_title = self.cfg.get("header_title", "")
        if header_title:
            _draw_mixed(c, self.lm, self.page_h - 18*mm, header_title, 8)

        # Header right: "目  录"
        c.setFont("CJK", 8)
        c.drawRightString(self.page_w - self.rm, self.page_h - 18*mm, "\u76ee  \u5f55")

        # Footer
        c.setStrokeColor(T["border"])
        c.line(self.lm, self.bm - 8*mm, self.page_w - self.rm, self.bm - 8*mm)
        c.setFillColor(T["accent"]); c.setFont("Serif", 9)
        c.drawCentredString(self.page_w/2, self.bm - 16*mm, f"\u2014  {pg}  \u2014")

        c.restoreState()

    # ── Table parser ──
    def parse_table(self, lines, role="auto"):
        rows = []
        for l in lines:
            l = l.strip().strip('|')
            rows.append([c.strip() for c in l.split('|')])
        if len(rows) < 2:
            return None
        header = rows[0]
        data = [r for r in rows[1:] if not all(set(c.strip()) <= set('-: ') for c in r)]
        if not data:
            return None
        nc = len(header)
        ST = self.ST
        td = [[Paragraph(md_inline(h, self.accent_hex), ST['th']) for h in header]]
        numeric_cols = []
        for ci in range(nc):
            non_empty = [r[ci] for r in data if ci < len(r) and r[ci].strip()]
            if non_empty and sum(1 for cell in non_empty if _looks_numeric(cell)) / len(non_empty) >= 0.6:
                numeric_cols.append(ci)

        role = role or "auto"
        research_role = role in ("valuation", "forecast", "peer-comparison", "rating-history")

        for r in data:
            while len(r) < nc:
                r.append("")
            is_focus = research_role and _is_focus_row(r)
            is_total = _is_total_row(r)
            is_emphasis = _is_emphasis_row(r)
            cells = []
            for ci, cell in enumerate(r[:nc]):
                style = ST['tc_num'] if ci in numeric_cols else ST['tc']
                if ci == 0 and not _looks_numeric(cell):
                    style = ST['tc']
                text = cell
                if is_focus or is_total or is_emphasis:
                    text = f"**{cell}**"
                cells.append(Paragraph(md_inline(text, self.accent_hex), style))
            td.append(cells)
        avail = self.body_w - 4*mm
        cw = _table_col_widths(role, nc, header, data, avail)
        T = self.T
        t = Table(td, colWidths=cw, repeatRows=1)
        cmds = [
            ('BACKGROUND',(0,0),(-1,0), T["accent"]),
            ('TEXTCOLOR',(0,0),(-1,0), white),
            ('BOX',(0,0),(-1,-1), 0.55, T["border"]),
            ('LINEBELOW',(0,0),(-1,0), 0.8, T["border"]),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
            ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ]
        for ridx, row in enumerate(data, start=1):
            is_total = _is_total_row(row)
            is_emphasis = _is_emphasis_row(row)
            is_focus = research_role and _is_focus_row(row)
            if is_emphasis:
                cmds.extend([
                    ('BACKGROUND', (0, ridx), (-1, ridx), T["success"]),
                    ('TEXTCOLOR', (0, ridx), (-1, ridx), white),
                ])
            elif is_total:
                cmds.extend([
                    ('BACKGROUND', (0, ridx), (-1, ridx), T["accent"]),
                    ('TEXTCOLOR', (0, ridx), (-1, ridx), white),
                ])
            elif is_focus:
                cmds.extend([
                    ('BACKGROUND', (0, ridx), (-1, ridx), T["accent_light"]),
                    ('TEXTCOLOR', (0, ridx), (-1, ridx), T["ink"]),
                ])
            else:
                bg = white if ridx % 2 == 1 else T["canvas_sec"]
                if role in ("comparison", "peer-comparison") and ridx == 1:
                    bg = white
                if role in ("valuation", "forecast") and ridx == 1:
                    bg = T["callout_bg"]
                cmds.append(('BACKGROUND', (0, ridx), (-1, ridx), bg))
            if ridx < len(data):
                cmds.append(('LINEBELOW', (0, ridx), (-1, ridx), 0.35, T["border"]))
        t.setStyle(TableStyle(cmds))
        return t

    # ── Markdown → Story ──
    @staticmethod
    def _preprocess_md(md):
        """Normalize markdown: split merged headings like '# Part## Chapter'."""
        lines = md.split('\n')
        out = []
        in_code = False
        for line in lines:
            if line.strip().startswith('```'):
                in_code = not in_code
            if in_code:
                out.append(line); continue
            # Split where a non-# char is followed by ## (heading marker)
            # e.g. "# 第一部分：背景与概览## 第1章" or "---## 第2章"
            parts = re.split(r'(?<=[^#\s])\s*(?=#{1,3}\s)', line)
            if len(parts) > 1:
                for p in parts:
                    p = p.strip()
                    if p:
                        out.append(p)
            else:
                out.append(line)
        return '\n'.join(out)

    def parse_md(self, md):
        story, toc = [], []
        md = self._preprocess_md(md)
        lines = md.split('\n')
        i, in_code, code_buf = 0, False, []
        next_table_role = "auto"
        next_block_role = ""
        ST = self.ST; ah = self.accent_hex
        code_max = self.cfg.get("code_max_lines", 30)
        business_mode = self.cfg.get("blueprint") in PUBLIC_BLUEPRINTS

        while i < len(lines):
            line = lines[i]; stripped = line.strip()
            # Code blocks
            if stripped.startswith('```'):
                if in_code:
                    ct = '\n'.join(code_buf)
                    if ct.strip():
                        cl = ct.split('\n')
                        if len(cl) > code_max:
                            cl = cl[:code_max - 2] + ['  // ... (truncated)']
                            ct = '\n'.join(cl)
                        para = Paragraph(_font_wrap(esc_code(ct)), ST['code'])
                        flows = [LeftBorderParagraph(para, self.T["accent"])] if self._code_style_type == "border" else [para]
                        if next_block_role:
                            story.extend(self._wrap_semantic_block(next_block_role, flows))
                            next_block_role = ""
                        else:
                            story.extend(flows)
                    code_buf = []; in_code = False
                else: in_code = True; code_buf = []
                i += 1; continue
            if in_code: code_buf.append(line); i += 1; continue
            if stripped in ('---','\\newpage','') or stripped.startswith(('title:','subtitle:','author:','date:')):
                i += 1; continue

            directive = _parse_alanpdf_directive(stripped)
            if directive:
                if "figure" in directive:
                    story.extend(self._build_figure_flowables(directive))
                    i += 1
                    continue
                if "table" in directive:
                    next_table_role = directive["table"]
                if "block" in directive and directive["block"] in BLOCK_ROLES:
                    next_block_role = directive["block"]
                i += 1; continue

            # H1 — Part heading: full divider page
            if re.match(r'^# (第.+部分|附录)', stripped) or \
               (re.match(r'^# .+', stripped) and not stripped.startswith('## ')):
                if re.match(r'^# .+', stripped):
                    title = stripped.lstrip('#').strip()
                    hdeco = self.L["heading_decoration"]
                    if business_mode:
                        block = [
                            ChapterMark(title, level=0),
                            Spacer(1, 5*mm),
                            Paragraph(md_inline(title, ah), ST['chapter']),
                            Spacer(1, 2*mm),
                            HRule(self.body_w, 0.8, self.T["accent"]),
                            Spacer(1, 2*mm),
                        ]
                        story.append(CondPageBreak(28*mm))
                        story.append(KeepTogether(block))
                    else:
                        story.append(PageBreak())
                        cm = ChapterMark(title, level=0); story.append(cm)
                        story.append(Spacer(1, self.body_h * 0.35))
                        if hdeco == "rules":
                            story.append(HRuleCentered(self.body_w, 40*mm, 0.8, self.T["accent"]))
                            story.append(Spacer(1, 8*mm))
                        story.append(Paragraph(md_inline(title, ah), ST['part']))
                        if hdeco == "rules":
                            story.append(Spacer(1, 8*mm))
                            story.append(HRuleCentered(self.body_w, 25*mm, 0.8, self.T["accent"]))
                        elif hdeco == "underline":
                            story.append(Spacer(1, 4*mm))
                            story.append(HRule(self.body_w, 1.0, self.T["accent"]))
                        elif hdeco == "dot":
                            story.append(Spacer(1, 6*mm))
                            story.append(ClayDot(self.body_w, self.T["accent"]))
                    # "none" = no decoration
                    cm = block[0] if business_mode else cm
                    toc.append(('part', title, cm.key))
                    i += 1; continue

            # H2 — Chapter heading
            if stripped.startswith('## '):
                title = stripped[3:].strip()
                hdeco = self.L["heading_decoration"]
                if business_mode:
                    block = [
                        ChapterMark(title, level=1),
                        Spacer(1, 4*mm),
                        Paragraph(md_inline(title, ah), ST['h3']),
                        Spacer(1, 1*mm),
                    ]
                    story.append(CondPageBreak(22*mm))
                    story.append(KeepTogether(block))
                else:
                    story.append(PageBreak())
                    cm = ChapterMark(title, level=1); story.append(cm)
                    story.append(Spacer(1, self.body_h * 0.30))
                    story.append(Paragraph(md_inline(title, ah), ST['chapter']))
                    if hdeco == "rules":
                        story.append(Spacer(1, 5*mm))
                        story.append(HRuleCentered(self.body_w, 35*mm, 1.2, self.T["accent"]))
                    elif hdeco == "underline":
                        story.append(Spacer(1, 3*mm))
                        story.append(HRule(self.body_w, 0.8, self.T["accent"]))
                    elif hdeco == "dot":
                        story.append(Spacer(1, 5*mm))
                        story.append(ClayDot(self.body_w, self.T["accent"]))
                cm = block[0] if business_mode else cm
                toc.append(('chapter', title, cm.key))
                i += 1; continue

            # H3 = Section
            if stripped.startswith('### '):
                block = [
                    Spacer(1, 3*mm),
                    Paragraph(md_inline(stripped[4:].strip(), ah), ST['h3']),
                    Spacer(1, 1*mm),
                ]
                story.append(CondPageBreak(16*mm))
                story.append(KeepTogether(block))
                i += 1; continue

            # Tables
            if stripped.startswith('|'):
                tl = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    tl.append(lines[i]); i += 1
                t = self.parse_table(tl, next_table_role)
                next_table_role = "auto"
                if t:
                    if next_block_role:
                        story.extend(self._wrap_semantic_block(next_block_role, [t]))
                        next_block_role = ""
                    else:
                        story.extend([Spacer(1,2*mm), CondPageBreak(26*mm), t, Spacer(1,2*mm)])
                continue

            # Bullets
            if stripped.startswith('- ') or stripped.startswith('* '):
                bullet_lines = []
                while i < len(lines):
                    l = lines[i].strip()
                    if l.startswith('- ') or l.startswith('* '):
                        bullet_lines.append(l[2:].strip())
                        i += 1
                        continue
                    break
                flows = [Paragraph(f"\u2022  {md_inline(item, ah)}", ST['bullet']) for item in bullet_lines]
                if next_block_role:
                    story.extend(self._wrap_semantic_block(next_block_role, flows))
                    next_block_role = ""
                else:
                    story.extend(flows)
                continue

            # Numbered list
            m = re.match(r'^(\d+)\.\s+(.+)', stripped)
            if m:
                numbered = []
                while i < len(lines):
                    l = lines[i].strip()
                    m2 = re.match(r'^(\d+)\.\s+(.+)', l)
                    if not m2:
                        break
                    numbered.append((m2.group(1), m2.group(2)))
                    i += 1
                flows = [Paragraph(f"{n}.  {md_inline(text, ah)}", ST['bullet']) for n, text in numbered]
                if next_block_role:
                    story.extend(self._wrap_semantic_block(next_block_role, flows))
                    next_block_role = ""
                else:
                    story.extend(flows)
                continue

            # Blockquote
            if stripped.startswith('> '):
                qlines = []
                while i < len(lines) and lines[i].strip().startswith('> '):
                    qlines.append(lines[i].strip()[2:].strip())
                    i += 1
                para = Paragraph(md_inline(" ".join(qlines), ah), ST['callout'])
                box = Table([[para]], colWidths=[self.body_w - 2*mm])
                box.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), self.T["callout_bg"]),
                    ('BOX', (0, 0), (-1, -1), 0.8, self.T["border"]),
                    ('LINEBEFORE', (0, 0), (0, -1), 2.0, self.T["accent"]),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ]))
                flows = [Spacer(1, 2*mm), box, Spacer(1, 2*mm)]
                if next_block_role:
                    story.extend(self._wrap_semantic_block(next_block_role, flows))
                    next_block_role = ""
                else:
                    story.extend(flows)
                continue

            # Paragraph — join consecutive lines; skip space between CJK characters
            plines = []
            while i < len(lines):
                l = lines[i].strip()
                if not l or l.startswith('#') or l.startswith('```') or l.startswith('|') or \
                   l.startswith('- ') or l.startswith('* ') or l.startswith('> ') or re.match(r'^\d+\.\s', l):
                    break
                plines.append(l); i += 1
            if plines:
                merged = plines[0]
                for pl in plines[1:]:
                    # If prev line ends with CJK and next starts with CJK, join directly (no space)
                    if merged and pl and _is_cjk(merged[-1]) and _is_cjk(pl[0]):
                        merged += pl
                    else:
                        merged += ' ' + pl
                flows = [Paragraph(md_inline(merged, ah), ST['body'])]
                if next_block_role:
                    story.extend(self._wrap_semantic_block(next_block_role, flows))
                    next_block_role = ""
                else:
                    story.extend(flows)
            continue

        return story, toc

    def build_toc(self, toc):
        ST = self.ST; ah = self.accent_hex; ink = self.T["ink"]
        s = [Spacer(1, 15*mm)]
        s.append(Paragraph(md_inline("\u76ee    \u5f55", ah), ST['part']))
        s.append(HRule(self.body_w * 0.12, 1, self.T["accent"]))
        s.append(Spacer(1, 8*mm))
        ink_hex = f"#{int(ink.red*255):02x}{int(ink.green*255):02x}{int(ink.blue*255):02x}" if hasattr(ink,'red') else "#181818"
        for etype, title, key in toc:
            style = ST['toc1'] if etype == 'part' else ST['toc2']
            linked = f"<a href=\"#{key}\" color=\"{ink_hex}\">{_font_wrap(esc(title))}</a>"
            s.append(Paragraph(linked, style))
        return s

    # ── Build PDF ──
    def build(self, md_text, output_path):
        register_fonts()
        print("Parsing markdown...")
        story_content, toc = self.parse_md(md_text)
        print(f"  {len(story_content)} elements, {len(toc)} TOC entries")

        body_frame = Frame(self.lm, self.bm, self.body_w, self.body_h, id='body')
        first_top_margin = self.L.get("first_top_margin")
        integrated_cover = self.L.get("cover_style") in ("proposal-integrated", "pricing-integrated", "research-integrated")
        first_frame = body_frame
        if integrated_cover and first_top_margin:
            first_tm = first_top_margin * mm
            first_h = self.page_h - first_tm - self.bm
            first_frame = Frame(self.lm, self.bm, self.body_w, first_h, id='first')
        full_frame = Frame(0, 0, self.page_w, self.page_h, leftPadding=0,
                           rightPadding=0, topPadding=0, bottomPadding=0, id='full')

        doc = BaseDocTemplate(output_path, pagesize=(self.page_w, self.page_h),
                              leftMargin=self.lm, rightMargin=self.rm,
                              topMargin=self.tm, bottomMargin=self.bm,
                              title=self.cfg.get("title", ""),
                              author=self.cfg.get("author", ""))

        templates = [
            PageTemplate(id='normal', frames=[body_frame], onPage=self._normal_page),
        ]
        if integrated_cover:
            templates.insert(0, PageTemplate(id='first', frames=[first_frame], onPage=self._first_page))

        story = []
        has_frontis = self.cfg.get("frontispiece") and os.path.exists(self.cfg["frontispiece"])
        has_banner = self.cfg.get("banner") and os.path.exists(self.cfg["banner"])
        has_toc = self.cfg.get("toc", True) and toc
        use_compact_nav = integrated_cover and has_toc

        # Cover page
        if integrated_cover:
            story.append(NextPageTemplate('normal'))
        elif self.cfg.get("cover", True):
            templates.insert(0, PageTemplate(id='cover', frames=[full_frame], onPage=self._cover_page))
            story.append(Spacer(1, self.page_h))

            # Determine next page after cover
            if has_frontis:
                templates.append(PageTemplate(id='frontis', frames=[full_frame], onPage=self._frontispiece_page))
                story.append(NextPageTemplate('frontis'))
                story.append(PageBreak())
                story.append(Spacer(1, self.page_h))
                # After frontispiece, go to toc or normal
                if has_toc:
                    templates.append(PageTemplate(id='toc', frames=[body_frame], onPage=self._toc_page))
                    story.append(NextPageTemplate('toc'))
                else:
                    story.append(NextPageTemplate('normal'))
                story.append(PageBreak())
            elif has_toc:
                templates.append(PageTemplate(id='toc', frames=[body_frame], onPage=self._toc_page))
                story.append(NextPageTemplate('toc'))
                story.append(PageBreak())
            else:
                story.append(NextPageTemplate('normal'))
                story.append(PageBreak())
        elif has_toc:
            templates.append(PageTemplate(id='toc', frames=[body_frame], onPage=self._toc_page))
            story.append(NextPageTemplate('toc'))

        # TOC
        if use_compact_nav:
            story.extend(self._build_compact_nav(toc))
        elif has_toc:
            story.extend(self.build_toc(toc))
            story.append(NextPageTemplate('normal'))
            story.append(PageBreak())

        # Strip leading PageBreak from body content to avoid blank page
        while story_content and isinstance(story_content[0], (PageBreak, Spacer)):
            if isinstance(story_content[0], PageBreak):
                story_content.pop(0)
                break
            story_content.pop(0)

        story.extend(story_content)

        # Back cover
        if has_banner:
            templates.append(PageTemplate(id='backcover', frames=[full_frame], onPage=self._backcover_page))
            story.append(NextPageTemplate('backcover'))
            story.append(PageBreak())
            story.append(Spacer(1, 1))

        doc.addPageTemplates(templates)
        print("Building PDF...")
        doc.build(story)
        size = os.path.getsize(output_path)
        print(f"Done! {output_path} ({size/1024/1024:.1f} MB)")

# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="alanpdf \u2014 Markdown to Business PDF")
    parser.add_argument("--input", "-i", required=True, help="Input markdown file")
    parser.add_argument("--output", "-o", default="output.pdf", help="Output PDF path")
    parser.add_argument("--blueprint", default="", choices=SUPPORTED_BLUEPRINT_CHOICES,
                        help="Business document blueprint")
    parser.add_argument("--style", default="", choices=SUPPORTED_STYLE_CHOICES,
                        help="Visual style preset layered on top of the blueprint")
    parser.add_argument("--density", default="standard", choices=SUPPORTED_DENSITY_CHOICES,
                        help="Layout density preset")
    parser.add_argument("--title", default="", help="Cover page title")
    parser.add_argument("--subtitle", default="", help="Cover page subtitle")
    parser.add_argument("--doc-label", default="", help="Third title line or document label")
    parser.add_argument("--meta-label", default="", help="Small running label used in cover/header")
    parser.add_argument("--author", default="", help="Author name")
    parser.add_argument("--analyst", default="", help="Analyst name for research reports")
    parser.add_argument("--ticker", default="", help="Ticker or stock code")
    parser.add_argument("--industry", default="", help="Industry or coverage label")
    parser.add_argument("--rating", default="", help="Investment rating")
    parser.add_argument("--target-price", default="", help="Target price label")
    parser.add_argument("--price-upside", default="", help="Expected upside/downside label")
    parser.add_argument("--date", default=str(date.today()), help="Date string")
    parser.add_argument("--version", default="", help="Version string on cover")
    parser.add_argument("--confidentiality", default="", help="Confidentiality label on cover/footer")
    parser.add_argument("--watermark", default="", help="Watermark text (empty = none)")
    parser.add_argument("--theme", default="warm-academic", help="Theme name")
    parser.add_argument("--theme-file", default=None, help="Custom theme JSON file path")
    parser.add_argument("--cover", default=True, type=lambda x: x.lower() != 'false', help="Generate cover page")
    parser.add_argument("--toc", default=True, type=lambda x: x.lower() != 'false', help="Generate TOC")
    parser.add_argument("--page-size", default="A4", choices=["A4","Letter"], help="Page size")
    parser.add_argument("--frontispiece", default="", help="Path to full-page image after cover")
    parser.add_argument("--banner", default="", help="Path to back cover banner image")
    parser.add_argument("--header-title", default="", help="Report title shown in page header (left)")
    parser.add_argument("--footer-left", default="", help="Brand/author text in footer (left)")
    parser.add_argument("--stats-line", default="", help="Stats line on cover (e.g. '1,884 files ...')")
    parser.add_argument("--stats-line2", default="", help="Second stats line on cover")
    parser.add_argument("--edition-line", default="", help="Edition line at cover bottom")
    parser.add_argument("--disclaimer", default="", help="Back cover disclaimer text")
    parser.add_argument("--copyright", default="", help="Back cover copyright text")
    parser.add_argument("--code-max-lines", default=30, type=int, help="Max lines per code block before truncation")
    args = parser.parse_args()

    with open(args.input, encoding='utf-8') as f:
        raw_md_text = f.read()

    frontmatter, md_text = parse_frontmatter(raw_md_text)

    def cli_has(flag):
        return any(opt == flag or opt.startswith(f"{flag}=") for opt in sys.argv[1:])

    def meta_pick_raw(*keys):
        for key in keys:
            if key in frontmatter:
                return frontmatter.get(key)
        return None

    def meta_pick(*keys, default=""):
        for key in keys:
            if key in frontmatter and frontmatter.get(key) not in (None, ""):
                return str(frontmatter.get(key))
        return default

    def pick_arg(cli_value, flag, *meta_keys, default=""):
        if cli_has(flag):
            return cli_value
        meta_value = meta_pick(*meta_keys)
        if meta_value != "":
            return meta_value
        if cli_value not in (None, ""):
            return cli_value
        return default

    blueprint_name = pick_arg(args.blueprint, "--blueprint", "blueprint")
    if blueprint_name and blueprint_name not in SUPPORTED_BLUEPRINT_CHOICES:
        print(f"Warning: Unknown blueprint '{blueprint_name}', ignoring frontmatter value", file=sys.stderr)
        blueprint_name = ""

    style_input = pick_arg(args.style, "--style", "style")
    if style_input and style_input not in SUPPORTED_STYLE_CHOICES:
        print(f"Warning: Unknown style '{style_input}', ignoring frontmatter value", file=sys.stderr)
        style_input = ""

    density_name = pick_arg(args.density, "--density", "density", default=args.density)
    if density_name not in SUPPORTED_DENSITY_CHOICES:
        print(f"Warning: Unknown density '{density_name}', falling back to standard", file=sys.stderr)
        density_name = "standard"

    # Extract title from first H1 if not provided
    title = pick_arg(args.title, "--title", "title")
    if not title:
        m = re.search(r'^# (.+)$', md_text, re.MULTILINE)
        title = m.group(1).strip() if m else "Document"

    blueprint = BLUEPRINTS.get(blueprint_name, {})
    theme_name = pick_arg(args.theme, "--theme", "theme", default=args.theme)
    if blueprint_name and not args.theme_file:
        theme_name = blueprint["theme"]

    theme = load_theme(theme_name, args.theme_file)
    style_name = style_input or blueprint.get("style", "")
    theme = apply_style(theme, style_name)
    if not cli_has("--density") and not meta_pick("density"):
        density_name = blueprint.get("density", density_name)
    theme = apply_density(theme, density_name)
    a = theme['accent']
    accent_hex = f"#{int(a.red*255):02x}{int(a.green*255):02x}{int(a.blue*255):02x}" \
        if hasattr(a, 'red') else "#CC785C"

    header_title = pick_arg(args.header_title, "--header-title", "header_title", "header-title")
    if not header_title and blueprint.get("header_title_mode") == "meta":
        header_title = pick_arg(args.meta_label, "--meta-label", "meta_label", "meta-label") or blueprint.get("meta_label", "")

    toc_enabled = args.toc
    if not cli_has("--toc"):
        meta_toc = meta_pick_raw("toc")
        if meta_toc is not None:
            toc_enabled = _coerce_bool(meta_toc, args.toc)
        elif blueprint_name:
            toc_enabled = blueprint.get("toc", args.toc)

    cover_enabled = args.cover
    if not cli_has("--cover"):
        meta_cover = meta_pick_raw("cover")
        if meta_cover is not None:
            cover_enabled = _coerce_bool(meta_cover, args.cover)

    summary_points = _normalize_string_list(meta_pick_raw("summary_points", "summary"))
    nav_max_items = meta_pick_raw("nav_max_items", "nav-max-items")
    try:
        nav_max_items = min(max(int(nav_max_items), 4), 14) if nav_max_items not in (None, "") else 8
    except Exception:
        nav_max_items = 8

    author = pick_arg(args.author, "--author", "author")
    analyst = pick_arg(args.analyst, "--analyst", "analyst")
    footer_left = pick_arg(args.footer_left, "--footer-left", "footer_left", "footer-left")
    if not footer_left:
        footer_left = analyst or author

    config = {
        "title": title,
        "subtitle": pick_arg(args.subtitle, "--subtitle", "subtitle"),
        "doc_label": pick_arg(args.doc_label, "--doc-label", "doc_label", "doc-label") or blueprint.get("doc_label", ""),
        "meta_label": pick_arg(args.meta_label, "--meta-label", "meta_label", "meta-label") or blueprint.get("meta_label", ""),
        "author": author,
        "analyst": analyst,
        "ticker": pick_arg(args.ticker, "--ticker", "ticker"),
        "industry": pick_arg(args.industry, "--industry", "industry"),
        "rating": pick_arg(args.rating, "--rating", "rating"),
        "target_price": pick_arg(args.target_price, "--target-price", "target_price", "target-price"),
        "price_upside": pick_arg(args.price_upside, "--price-upside", "price_upside", "price-upside"),
        "date": pick_arg(args.date, "--date", "date", default=args.date),
        "version": pick_arg(args.version, "--version", "version"),
        "confidentiality": pick_arg(args.confidentiality, "--confidentiality", "confidentiality") or blueprint.get("confidentiality", ""),
        "watermark": pick_arg(args.watermark, "--watermark", "watermark"),
        "theme": theme,
        "accent_hex": accent_hex,
        "cover": cover_enabled,
        "toc": toc_enabled,
        "page_size": A4 if args.page_size == "A4" else LETTER,
        "frontispiece": pick_arg(args.frontispiece, "--frontispiece", "frontispiece"),
        "banner": pick_arg(args.banner, "--banner", "banner"),
        "header_title": header_title,
        "footer_left": footer_left,
        "stats_line": pick_arg(args.stats_line, "--stats-line", "stats_line", "stats-line"),
        "stats_line2": pick_arg(args.stats_line2, "--stats-line2", "stats_line2", "stats-line2"),
        "edition_line": pick_arg(args.edition_line, "--edition-line", "edition_line", "edition-line"),
        "disclaimer": pick_arg(args.disclaimer, "--disclaimer", "disclaimer"),
        "copyright": pick_arg(args.copyright, "--copyright", "copyright"),
        "code_max_lines": args.code_max_lines,
        "blueprint": blueprint_name,
        "style": style_name,
        "density": density_name,
        "base_dir": os.path.dirname(os.path.abspath(args.input)),
        "summary_title": meta_pick("summary_title", "summary-title", default="执行摘要"),
        "summary_note": meta_pick("summary_note", "summary-note"),
        "summary_points": summary_points,
        "nav_title": meta_pick("nav_title", "nav-title", "toc_title", "toc-title", default="内容导览"),
        "nav_max_items": nav_max_items,
    }

    builder = PDFBuilder(config)
    builder.build(md_text, args.output)

if __name__ == "__main__":
    main()
