import os
from PIL import Image, ImageDraw

def generate_icons(res_dir):
    sizes = {
        'mipmap-mdpi': 48,
        'mipmap-hdpi': 72,
        'mipmap-xhdpi': 96,
        'mipmap-xxhdpi': 144,
        'mipmap-xxxhdpi': 192
    }

    for folder, size in sizes.items():
        out_dir = os.path.join(res_dir, folder)
        os.makedirs(out_dir, exist_ok=True)
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw green circle
        margin = int(size * 0.05)
        draw.ellipse([margin, margin, size - margin, size - margin], fill=(30, 215, 96, 255))

        # Draw 3 black arcs
        cx, cy = size // 2, size // 2
        r1 = size * 0.32
        r2 = size * 0.24
        r3 = size * 0.16
        w1 = max(2, int(size * 0.065))
        w2 = max(2, int(size * 0.055))
        w3 = max(2, int(size * 0.045))

        # Arc 1
        bbox1 = [cx - r1, cy - r1 + int(size * 0.02), cx + r1, cy + r1 + int(size * 0.02)]
        draw.arc(bbox1, start=205, end=335, fill=(0, 0, 0, 255), width=w1)

        # Arc 2
        bbox2 = [cx - r2, cy - r2 + int(size * 0.08), cx + r2, cy + r2 + int(size * 0.08)]
        draw.arc(bbox2, start=205, end=335, fill=(0, 0, 0, 255), width=w2)

        # Arc 3
        bbox3 = [cx - r3, cy - r3 + int(size * 0.14), cx + r3, cy + r3 + int(size * 0.14)]
        draw.arc(bbox3, start=205, end=335, fill=(0, 0, 0, 255), width=w3)

        out_path = os.path.join(out_dir, 'ic_launcher.png')
        img.save(out_path, 'PNG')
        print(f"Generated {out_path} ({size}x{size})")

if __name__ == '__main__':
    root = os.path.dirname(os.path.abspath(__file__))
    res_dir = os.path.join(root, 'res')
    generate_icons(res_dir)
