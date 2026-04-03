#!/usr/bin/env python3

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "hero" / "alanpdf-hero.png"
PREVIEWS = {
    "proposal": ROOT / "assets" / "previews" / "proposal-harborgrid.png",
    "pricing": ROOT / "assets" / "previews" / "pricing-astera.png",
    "equity": ROOT / "assets" / "previews" / "equity-novaforge.png",
}


def pick_font(candidates, size):
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT_SANS = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
FONT_SANS_BOLD = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return mask


def add_card(canvas, image_path, box, border, shadow_color, angle=0):
    x, y, w, h = box
    preview = Image.open(image_path).convert("RGB")
    preview = preview.resize((w, h), Image.Resampling.LANCZOS)

    card = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    card.paste(preview, (0, 0))

    mask = rounded_mask((w, h), 28)
    shadow = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((30, 26, 30 + w, 26 + h), radius=32, fill=shadow_color)
    shadow = shadow.filter(ImageFilter.GaussianBlur(20))

    if angle:
        shadow = shadow.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
        card = card.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
        mask = mask.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)

    canvas.alpha_composite(shadow, (x - 34, y - 30))

    border_layer = Image.new("RGBA", card.size, (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border_layer)
    border_draw.rounded_rectangle((0, 0, card.size[0] - 1, card.size[1] - 1), radius=28, outline=border, width=2)
    card.alpha_composite(border_layer)

    holder = Image.new("RGBA", card.size, (0, 0, 0, 0))
    holder.paste(card, (0, 0), mask)
    canvas.alpha_composite(holder, (x, y))


def draw_chip(draw, xy, text, fill, text_fill, font):
    x, y = xy
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0] + 26
    h = bbox[3] - bbox[1] + 14
    draw.rounded_rectangle((x, y, x + w, y + h), radius=16, fill=fill)
    draw.text((x + 13, y + 6), text, font=font, fill=text_fill)
    return w


def main():
    W, H = 1600, 900
    canvas = Image.new("RGBA", (W, H), "#F7F9FC")
    draw = ImageDraw.Draw(canvas)

    # Background gradients and quiet structure.
    for y in range(H):
        t = y / H
        r = int(247 * (1 - t) + 240 * t)
        g = int(249 * (1 - t) + 244 * t)
        b = int(252 * (1 - t) + 248 * t)
        draw.line((0, y, W, y), fill=(r, g, b))

    draw.rectangle((0, 0, W, 10), fill="#1F5EA8")
    draw.rounded_rectangle((70, 70, 760, 810), radius=36, outline="#D7E0EB", width=2)
    draw.rounded_rectangle((1040, 110, 1480, 770), radius=44, outline="#DDE5EE", width=2)

    # Decorative measured accents.
    draw.ellipse((118, 118, 210, 210), outline="#C7D7EA", width=2)
    draw.ellipse((140, 140, 188, 188), fill="#EAF1F8")
    draw.line((118, 256, 700, 256), fill="#DEE6EF", width=2)
    draw.line((118, 652, 700, 652), fill="#DEE6EF", width=2)
    draw.line((920, 150, 920, 760), fill="#E3E9F1", width=2)

    title_font = pick_font(FONT_SANS_BOLD, 88)
    sub_font = pick_font(FONT_SANS, 34)
    meta_font = pick_font(FONT_SANS_BOLD, 20)
    body_font = pick_font(FONT_SANS, 24)
    label_font = pick_font(FONT_SANS_BOLD, 18)

    draw.text((118, 298), "AlanPDF Skill", font=title_font, fill="#173B63")
    draw.text(
        (118, 406),
        "Business PDFs with consulting-grade structure,\npricing clarity, and research-report discipline.",
        font=sub_font,
        fill="#4D6179",
        spacing=12,
    )

    cx = 118
    cx += draw_chip(draw, (cx, 540), "proposal", "#E7F0FB", "#1F5EA8", meta_font) + 14
    cx += draw_chip(draw, (cx, 540), "pricing-memo", "#E8F6F2", "#147A63", meta_font) + 14
    draw_chip(draw, (cx, 540), "equity-report", "#FBEFF0", "#9C3340", meta_font)

    draw.text((118, 694), "Deterministic renderer. Scenario-first blueprints. Public demo assets only.", font=body_font, fill="#627489")

    # Layered document cards.
    add_card(canvas, PREVIEWS["proposal"], (975, 162, 345, 488), "#C8D8EA", (37, 79, 130, 28), angle=-8)
    add_card(canvas, PREVIEWS["pricing"], (1138, 120, 348, 492), "#CBE3DB", (24, 91, 76, 34), angle=3)
    add_card(canvas, PREVIEWS["equity"], (1088, 318, 350, 496), "#D8DEEB", (38, 57, 92, 34), angle=-2)

    # Small annotation labels.
    tag_font = pick_font(FONT_SANS_BOLD, 18)
    draw_chip(draw, (1048, 762), "integrated covers", "#173B63", "#FFFFFF", tag_font)
    draw_chip(draw, (1236, 762), "semantic tables", "#147A63", "#FFFFFF", tag_font)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(OUT, quality=95)
    print(OUT)


if __name__ == "__main__":
    main()
