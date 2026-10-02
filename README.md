# mathbank — 전국연합 학력평가 문제은행

체크한 문제만 모아 **한 쪽에 2문제(또는 4문제)** 씩 배치하고, **해설은 미주**로 붙인 PDF 를 만드는 정적 웹앱입니다.
서버 없이 브라우저에서 `pdf-lib` 로 PDF 를 조립합니다 (원본 PDF 를 문제 단위로 잘라 벡터 그대로 붙이므로 확대해도 깨지지 않습니다).

## 구조
```
index.html, js/            웹앱 (js/layout.js = 쪽 배치 계산, js/app.js = 화면 + PDF 조립)
vendor/pdf-lib.min.js      PDF 조립 라이브러리 (오프라인에서도 동작하도록 동봉)
pdf/<연도>/                원본 시험지 PDF  (예: pdf/2021/2021_1학년_6월_문제.pdf, ..._해설.pdf)
data/problems.json         문제별 위치(좌표)·단원·성취기준·배점·정답  ← 웹앱이 읽는 데이터
data/classification_*.xlsx 단원 분류 원본(사람이 검토하는 표)
data/answers_*.json        정답표 입력본
tools/                     좌표 자동 검출·데이터 생성 스크립트 (Python)
```

## 로컬에서 실행
브라우저는 `file://` 로 연 페이지에서 PDF 를 읽지 못하므로 간단한 서버가 필요합니다.
```
python -m http.server 8000     # 저장소 폴더에서
# 브라우저에서 http://localhost:8000
```
GitHub Pages 로 배포하면 그대로 동작합니다.

## 새 시험 추가 절차
1. `pdf/<연도>/` 에 `<연도>_<n>학년_<월>월_문제.pdf`, `..._해설.pdf` 를 넣는다.
2. 단원 분류 xlsx 와 정답 json 을 `data/` 에 준비한다.
3. `python tools/build_data.py` 로 `data/problems.json` 을 다시 만든다 (문제·해설 영역 자동 검출).
4. `tools/overlay.py` 로 잘린 영역을 눈으로 확인한다.

## 알려진 한계
- 정답은 현재 해설 정답표를 눈으로 옮긴 값입니다 (6월 3회분). 대량 입력 시 OCR 검증이 필요합니다.
- 저작권: 시험지 저작권은 출제 기관에 있으므로 저장소를 비공개로 두거나 교내 사용 범위를 지키세요.
