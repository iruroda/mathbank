# mathbank — 전국연합 학력평가 문제은행

체크한 문제만 모아 **한 쪽에 2문제(또는 4문제)** 씩 배치하고, **해설은 미주**로 붙인 PDF 를 만드는 정적 웹앱입니다.
서버 없이 브라우저에서 `pdf-lib` 로 PDF 를 조립합니다 (원본 PDF 를 문제 단위로 잘라 벡터 그대로 붙이므로 확대해도 깨지지 않습니다).

## 구조
```
index.html, js/            웹앱 (js/layout.js = 쪽 배치 계산, js/app.js = 화면 + PDF 조립)
vendor/pdf-lib.min.js      PDF 조립 라이브러리 (오프라인에서도 동작하도록 동봉)
pdf/<연도>/                원본 시험지 PDF  (예: pdf/2021/2021_1학년_6월_문제.pdf, ..._해설.pdf)
data/problems.json         문제별 위치(좌표)·단원·성취기준·배점·정답  ← 웹앱이 읽는 데이터
data/classification_2021_06.xlsx, data/classification/*.json  단원 분류 원본 (시험 1회 = 파일 1개)
data/classification_2021_all.xlsx  2021년 전체 분류표 (tools/make_xlsx.py 로 생성)
data/standards_codes.json  성취기준 코드 → 과목·단원·문장 사전
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
2. 단원 분류 json(`data/classification/`)과 정답 json(`data/answers_*.json`)을 준비한다.
3. `tools/build_all.py` 의 `EXAMS` 목록에 시험을 추가하고 `python tools/build_all.py` 로 `data/problems.json` 을 다시 만든다 (문제·해설 영역 자동 검출).
4. `tools/overlay.py` 로 잘린 영역을 눈으로 확인한다. 전체 분류표는 `python tools/make_xlsx.py` 로 만든다.

## 알려진 한계
- 정답은 해설 정답표를 눈으로 옮기고 해설 PDF 텍스트와 대조한 값입니다.
- 2021학년도 3학년 7월 해설은 새 파일로 교체되어 확률과 통계·미적분·기하 해설이 모두 포함됩니다.
- 저작권: 시험지 저작권은 출제 기관에 있으므로 저장소를 비공개로 두거나 교내 사용 범위를 지키세요.
