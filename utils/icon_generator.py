from PIL import Image, ImageDraw

def generate_fallback_icon() -> Image.Image:
    img = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([2, 2, 62, 62], radius=14, fill=(15, 23, 42), outline=(59, 130, 246), width=3)
    draw.rectangle([18, 14, 46, 50], fill=(241, 245, 249))
    draw.polygon([(36, 14), (46, 24), (36, 24)], fill=(148, 163, 184))
    draw.line([(24, 28), (38, 28)], fill=(71, 85, 105), width=2)
    draw.line([(24, 34), (40, 34)], fill=(71, 85, 105), width=2)
    draw.polygon([(32, 48), (26, 42), (38, 42)], fill=(37, 99, 235))
    draw.line([(32, 38), (32, 44)], fill=(37, 99, 235), width=3)
    return img
