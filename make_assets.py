# -*- coding: utf-8 -*-
"""공유 이미지(og:image)와 파비콘 생성.

    python make_assets.py

간판 사진 한 장에서 만들어낸다. 지역이 늘면 그 지역 간판으로 og 이미지가 같이 생긴다.

    regions/<slug>.json 의 signboard  ->  assets/og-<slug>.jpg   (1200x630)
    site.json 의 logo_source + logo_crop -> favicon.ico, apple-touch-icon.png

빌드(build.py)와 분리해 둔 이유: 이미지는 간판을 바꿀 때나 새로 만들면 되고,
매 빌드마다 다시 그릴 필요가 없다.

필요 패키지: pillow  (pip install pillow)

⚠️ og:image 가 없으면 카카오톡으로 링크를 보냈을 때 **빈 카드**로 간다.
   인력사무소는 링크를 카톡으로 돌리는 일이 많아서 이게 생각보다 크게 작용한다.
"""
import io
import json
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, 'assets')

OG_W, OG_H = 1200, 630
NAVY_TOP = (27, 58, 107)      # #1B3A6B
NAVY_BOTTOM = (42, 82, 152)   # #2a5298
AMBER = (245, 166, 35)        # #F5A623

FONT_BOLD = r'C:\Windows\Fonts\malgunbd.ttf'
FONT_REGULAR = r'C:\Windows\Fonts\malgun.ttf'


def load_json(path):
    with io.open(path, encoding='utf-8') as f:
        return json.load(f)


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except IOError:
        # 윈도우가 아닌 곳에서 돌릴 때를 대비한 최후 수단(모양은 나빠도 터지지는 않는다).
        return ImageFont.load_default()


def draw_center(draw, y, text, fnt, fill):
    left, top, right, bottom = draw.textbbox((0, 0), text, font=fnt)
    draw.text(((OG_W - (right - left)) / 2 - left, y), text, font=fnt, fill=fill)
    return bottom - top


def make_og(region):
    """공유 카드 — 간판을 위에 깔고 그 아래 한 줄 설명 + 전화번호."""
    img = Image.new('RGB', (OG_W, OG_H), NAVY_TOP)
    draw = ImageDraw.Draw(img)

    # 세로 그라데이션 (사이트 헤더와 같은 네이비)
    for y in range(OG_H):
        t = y / float(OG_H - 1)
        draw.line(
            [(0, y), (OG_W, y)],
            fill=tuple(int(NAVY_TOP[i] + (NAVY_BOTTOM[i] - NAVY_TOP[i]) * t) for i in range(3)),
        )

    sign_path = os.path.join(ROOT, region['signboard'].lstrip('/'))
    sign = Image.open(sign_path).convert('RGB')
    target_w = 1000
    target_h = int(round(sign.height * target_w / float(sign.width)))
    sign = sign.resize((target_w, target_h), Image.LANCZOS)
    img.paste(sign, ((OG_W - target_w) // 2, 110))

    line1 = region['tagline_lines'][0]
    numbers = ' · '.join(p['number'] for p in region['phones'])

    y = 110 + target_h + 70
    y += draw_center(draw, y, line1, font(FONT_BOLD, 52), (255, 255, 255)) + 40
    draw_center(draw, y, numbers, font(FONT_BOLD, 46), AMBER)

    out = os.path.join(ASSETS, 'og-%s.jpg' % region['slug'])
    img.save(out, 'JPEG', quality=88, optimize=True)
    return out


def make_favicons(site):
    """간판 속 로고를 그대로 떼어 쓴다 — 새로 그린 것보다 알아보기 쉽다."""
    src = Image.open(os.path.join(ROOT, site['logo_source'].lstrip('/'))).convert('RGB')
    logo = src.crop(tuple(site['logo_crop']))

    ico = os.path.join(ROOT, 'favicon.ico')
    logo.resize((64, 64), Image.LANCZOS).save(
        ico, sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])

    touch = os.path.join(ROOT, 'apple-touch-icon.png')
    logo.resize((180, 180), Image.LANCZOS).save(touch)
    return ico, touch


def main():
    site = load_json(os.path.join(ROOT, 'site.json'))
    if not os.path.isdir(ASSETS):
        os.makedirs(ASSETS)

    regions_dir = os.path.join(ROOT, 'regions')
    for name in sorted(os.listdir(regions_dir)):
        if name.endswith('.json'):
            region = load_json(os.path.join(regions_dir, name))
            print('  og   -> %s' % os.path.relpath(make_og(region), ROOT))

    for path in make_favicons(site):
        print('  icon -> %s' % os.path.relpath(path, ROOT))


if __name__ == '__main__':
    main()
