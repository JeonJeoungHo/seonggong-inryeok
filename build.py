# -*- coding: utf-8 -*-
"""성공인력 지역별 사이트 빌드.

    python build.py

`regions/*.json` 한 장이 사무소 한 곳이다. 화면(템플릿·CSS)은 `templates/`에 **한 벌만**
있고, 지역마다 다른 값(상호·등록번호·전화·커버지역·시세)만 JSON에서 온다.
그래서 화면을 고치면 전 지역이 같이 고쳐지고, 사무소가 늘어도 JSON 한 장이면 된다.

출력 위치:
    site.json의 root_region 과 같은 slug  ->  ./index.html          (기존 유입이 들어오는 자리)
    그 외 지역                            ->  ./<slug>/index.html
    사이트맵                              ->  ./sitemap.xml

⚠️ 출력 파일(index.html, <slug>/index.html, sitemap.xml)을 **직접 고치지 말 것.**
   다음 빌드가 덮어쓴다. 고칠 곳은 `templates/`(전 지역 공통) 아니면 `regions/`(그 지역만)다.

빌드 결과도 git에 커밋한다 — GitHub Pages는 저장소에 들어 있는 파일을 그대로 서빙하기
때문에, 산출물이 저장소에 없으면 사이트가 비어 버린다.

필요 패키지: jinja2  (pip install jinja2)
"""
import io
import json
import os
import sys

from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = os.path.dirname(os.path.abspath(__file__))
REGIONS_DIR = os.path.join(ROOT, 'regions')
TEMPLATES_DIR = os.path.join(ROOT, 'templates')


def load_json(path):
    with io.open(path, encoding='utf-8') as f:
        return json.load(f)


def load_regions():
    """regions/*.json 을 slug 순서로 읽는다. "_" 로 시작하는 키는 주석이라 그대로 둔다."""
    if not os.path.isdir(REGIONS_DIR):
        sys.exit('regions/ 폴더가 없습니다.')
    regions = []
    for name in sorted(os.listdir(REGIONS_DIR)):
        if not name.endswith('.json'):
            continue
        region = load_json(os.path.join(REGIONS_DIR, name))
        if region.get('slug') != os.path.splitext(name)[0]:
            sys.exit('%s: 파일 이름과 slug 가 다릅니다 (slug=%r).' % (name, region.get('slug')))
        regions.append(region)
    if not regions:
        sys.exit('regions/ 에 지역 파일이 없습니다.')
    return regions


def build_jsonld(site, region, page_url):
    """검색엔진·지도가 읽는 구조화 데이터.

    `EmploymentAgency` = schema.org 의 직업소개소 타입(LocalBusiness 의 하위).
    지역 검색 노출에 가장 크게 작용하는 항목인데 지금까지 없었다.

    ⚠️ **모르는 값은 넣지 않는다.** 영업시간·좌표를 지어내면 그게 그대로 검색결과에
       나가서 방문자가 헛걸음한다. 값이 생기면 그때 필드를 늘린다.
    """
    ascii_base = 'https://%s' % site['domain_ascii']
    data = {
        '@context': 'https://schema.org',
        '@type': 'EmploymentAgency',
        'name': region['name'],
        'description': region['seo']['description'],
        'url': page_url,
        'telephone': region['phones'][0]['number'],
        'address': {
            '@type': 'PostalAddress',
            'streetAddress': region['address'],
            'addressLocality': region['address_locality'],
            'addressRegion': region['address_region'],
            'addressCountry': 'KR',
        },
        'areaServed': [{'@type': 'City', 'name': a} for a in region['cover_areas']],
    }
    if region.get('office_name') and region['office_name'] != region['name']:
        data['alternateName'] = region['office_name']
    if region.get('og_image'):
        data['image'] = ascii_base + region['og_image']
    if region.get('opened_on'):
        data['foundingDate'] = region['opened_on']
    if region.get('latitude') and region.get('longitude'):
        data['geo'] = {
            '@type': 'GeoCoordinates',
            'latitude': region['latitude'],
            'longitude': region['longitude'],
        }
    sameas = [region.get('naver_place'), region.get('naver_blog')]
    sameas = [u for u in sameas if u]
    if sameas:
        data['sameAs'] = sameas
    out = json.dumps(data, ensure_ascii=False, indent=2)
    # <script> 안에 그대로 들어가므로 </script> 같은 조각이 태그를 끊지 못하게 막는다.
    # 아래 셋은 정상적인 JSON 이스케이프라 읽는 쪽에서는 원래 글자로 돌아온다.
    return out.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def make_asset(depth):
    """`/ganpan.jpg` 같은 루트 기준 경로를 그 페이지에서의 상대경로로 바꾼다.

    상대경로로 내보내는 이유: 빌드한 index.html 을 그냥 더블클릭해서(file://) 열어도
    이미지가 보여야 올리기 전에 눈으로 확인할 수 있다. 루트 기준(`/...`)으로 두면
    file:// 에서는 C 드라이브 최상단을 찾아가서 전부 깨진다.
    """
    prefix = '../' * depth

    def asset(path):
        return prefix + path.lstrip('/')

    return asset


def main():
    site = load_json(os.path.join(ROOT, 'site.json'))
    regions = load_regions()

    slugs = [r['slug'] for r in regions]
    if site['root_region'] not in slugs:
        sys.exit('site.json 의 root_region=%r 에 해당하는 지역 파일이 없습니다. (있는 것: %s)'
                 % (site['root_region'], ', '.join(slugs)))

    # 퓨니코드가 아니라 한글 도메인을 그대로 쓴다 — 기존 canonical/og:url 과 같은 모양을 유지한다.
    base_url = 'https://%s' % site['domain']

    # autoescape=True — 사무소명·주소에 &, < 같은 글자가 들어와도 페이지가 깨지지 않는다.
    # 줄바꿈용 <br> 은 JSON이 아니라 템플릿 안에 있으므로 이스케이프 대상이 아니다.
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        undefined=StrictUndefined,   # 오타난 변수는 조용히 빈칸이 되지 않고 바로 터진다.
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    page_tpl = env.get_template('index.html.j2')
    sitemap_tpl = env.get_template('sitemap.xml.j2')

    pages = []
    for region in regions:
        is_root = region['slug'] == site['root_region']
        url_path = '/' if is_root else '/%s/' % region['slug']
        page_url = base_url + url_path
        out_dir = ROOT if is_root else os.path.join(ROOT, region['slug'])
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        out_path = os.path.join(out_dir, 'index.html')

        html = page_tpl.render(
            site=site, region=region, page_url=page_url, is_root=is_root,
            asset=make_asset(0 if is_root else 1),
            ascii_base='https://%s' % site['domain_ascii'],
            jsonld=build_jsonld(site, region, page_url),
        )
        with io.open(out_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(html)

        pages.append({
            'url': page_url,
            'updated': region.get('updated', ''),
            'priority': '1.0' if is_root else '0.8',
        })
        print('  %-10s -> %s' % (region['slug'], os.path.relpath(out_path, ROOT)))

    sitemap = sitemap_tpl.render(site=site, pages=pages)
    with io.open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(sitemap)
    print('  %-10s -> sitemap.xml' % 'sitemap')

    # robots.txt — 지금까지 404였다. 사이트맵 위치를 여기서 알려준다.
    robots = 'User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n' % base_url
    with io.open(os.path.join(ROOT, 'robots.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(robots)
    print('  %-10s -> robots.txt' % 'robots')

    print('빌드 완료: 지역 %d곳' % len(regions))


if __name__ == '__main__':
    main()
