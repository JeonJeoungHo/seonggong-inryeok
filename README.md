# 성공인력 홈페이지

지역별 인력사무소 사이트. **사무소 한 곳 = `regions/` 안의 JSON 한 장.**

화면(템플릿·CSS)은 `templates/`에 한 벌만 있다. 그래서 화면을 고치면 전 지역이 같이
고쳐지고, 사무소가 늘어도 JSON 한 장만 추가하면 된다.

## 고치고 올리는 법

```bash
python build.py          # regions/*.json + templates/ -> 정적 HTML
git add -A && git commit -m "..." && git push
```

푸시하면 GitHub Pages가 몇 분 안에 https://성공인력.kr 에 반영한다.

> 처음 한 번만: `pip install jinja2`

## 폴더

```
site.json                사이트 전체 설정 (브랜드명·도메인·루트 지역)
regions/<slug>.json      사무소 한 곳의 정보   <- 지역마다 다른 것
templates/               화면 한 벌            <- 전 지역 공통인 것
build.py                 빌드 스크립트

index.html               <- 빌드 결과 (루트 지역 = site.json의 root_region)
<slug>/index.html        <- 빌드 결과 (그 외 지역)
sitemap.xml              <- 빌드 결과
ganpan.jpg               간판 이미지
CNAME                    도메인 연결 (건드리지 말 것)
naver*.html              네이버 사이트 소유확인 (건드리지 말 것)
```

**주의: `index.html` · `<slug>/index.html` · `sitemap.xml` 을 직접 고치지 말 것.**
다음 빌드가 덮어쓴다. 고칠 곳은 `templates/`(전 지역) 아니면 `regions/`(그 지역만)다.

## 지역 사무소 추가하기

1. `regions/paju.json` 을 복사해 `regions/<slug>.json` 으로 저장 (파일명 = 안의 `slug` 값)
2. 값을 그 사무소 것으로 바꾼다
3. `python build.py` -> `<slug>/index.html` 과 사이트맵 한 줄이 자동으로 생긴다

### 지역 페이지에 꼭 들어가야 하는 것

직업소개사업 등록은 **사무소 단위**라, 각 지역 페이지에는 **그 사무소의**
`license_number`(직업소개사업 등록번호) · `owner_name` · `address` · `phones` 가 들어가야 한다.
다른 지역 것을 돌려 쓰면 안 된다 — 사고가 났을 때 누가 계약 주체인지가 흐려진다.

### 내용 없는 지역 페이지는 만들지 말 것

지역명만 바꿔 찍어낸 페이지는 검색엔진이 낮게 평가한다(doorway page).
그 지역만의 실제 내용 — 시세, 커버 지역, 대표 인사말, 현장 사진 — 을 채울 수 있는
지역만 공개한다. 내용 있는 2곳이 빈 10곳보다 낫다.

## 지역 JSON 필드

필드 이름은 바로장비 `labor.LaborOffice` 모델에 맞춰뒀다. 나중에 앱과 연동할 때
변환 없이 그대로 붙이기 위해서다.

| 필드 | 뜻 |
|---|---|
| `slug` | URL 조각. 파일명과 같아야 한다 |
| `name` / `office_name` | 화면에 쓰는 상호 / 앱에 등록된 사무소명 |
| `region` / `area_name` | 시·도 + 시군구 / 짧은 지역 이름 |
| `owner_name` · `business_number` · `license_number` · `address` | 사업자 정보 |
| `relation` | `origin` 원조 / `branch` 직영지점 / `affiliate` 이름을 빌려 쓰는 제휴 / `independent` 자기 상호 유지 |
| `phones` | `[{label, number}]` — 순서대로 노출. 첫 번째가 플로팅 전화 버튼 |
| `cover_areas` | 커버 지역. 앱 `branches.Territory` 와 같은 시군구 단위 |
| `app_linked` | 바로장비 인력 기능 사용 여부. `false` 면 앱 버튼 없이 전화·카톡만 |
| `rates_verified` | 시세를 **숫자로** 공개할 직종. 검수 통과분만 |
| `updated` | 사이트맵 `lastmod`. 내용을 고친 날로 직접 갱신 |

### `rates_verified` 를 비워 두는 이유

공개된 단가는 나중에 분쟁의 근거로 인용된다. 바로장비의
`labor/fixtures/job_roles_seed.json` 에 33개 직종의 구간이 있지만 실거래로 확인된 것은
일부뿐이고 나머지는 인접 직종에서 추정한 값이다. **검수를 통과한 직종만** 여기에 넣고,
나머지는 "상담"으로 둔다.
