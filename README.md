# 인천·안산 행사판

인천과 안산에서 **지금 신청하거나 보러 갈 수 있는 행사**를 모아서, **참가비별로** 갈라 보여주는 페이지.

## 보는 곳

- 폰·PC 어디서나: GitHub Pages 주소 (저장소 Settings → Pages 에서 확인)
- 6시간마다 자동으로 다시 긁는다. 페이지 맨 위에 마지막 수집 시각이 찍힌다.

## PC에서 지금 당장 새로 긁기

`행사찾기.bat` 더블클릭. `index.html` 을 새로 만들고 브라우저로 연다.

파이썬만 있으면 되고 따로 설치할 라이브러리는 없다.

## 어디서 긁어오나

| 출처 | 주소 |
|---|---|
| 인천문화포털 IQ — 문화행사 | https://ifac.or.kr/culturalInfo/cuturalEvents/performanceSrch/list.do?key=m2501152621396 |
| 안산문화재단 — 공연안내 | https://www.ansanart.com/lay2/program/S1T10C334/show/intro.do |
| 안산문화재단 — 기획전시 | https://www.ansanart.com/lay1/program/S1T200C28/exhibit/intro.do |
| 안산문화재단 — 교육/행사 | https://www.ansanart.com/lay2/program/S1T32C336/np_edu/intro.do |

## 걸러내는 기준

- **끝난 행사는 뺀다** (종료일이 오늘보다 이전이면 제외)
- 일반인이 참여하는 게 아닌 것도 뺀다 — 채용, 대관 공고, 작가 공모, 심사 결과 등
- 참가비는 원문에 적힌 **첫 금액을 정가**로 잡는다. 할인가가 따로 있으면 "할인 시 N원부터" 로 따로 표시.
  (할인가를 기준으로 잡으면 2만원짜리가 "1만원 이하"로 잘못 분류된다.)
- 원문에 값이 아예 없으면 `확인필요` 로 둔다. 지어내지 않는다.

## 손볼 만한 곳 (run.py)

| 무엇 | 어디 |
|---|---|
| 가격 구간 나누기 | `bucket()` |
| 제외할 제목 | `SKIP` 정규식 |
| 수집처 추가 | `collect_incheon()` / `collect_ansan()` |
| 페이지 디자인 | `TEMPLATE` |

## 알아둘 것

공개 저장소의 예약 실행은 **60일 동안 저장소에 아무 활동이 없으면 깃허브가 자동으로 꺼버린다.**
([GitHub 문서](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) —
"scheduled workflows are automatically disabled when no repository activity has occurred in 60 days")
두 달에 한 번쯤 Actions 탭에서 **Run workflow** 를 눌러주면 된다.
