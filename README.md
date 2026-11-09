# 진짜 사진에 틀린 캡션이 붙으면 VLM은 알아차리는가

VLM은 이미지와 글을 함께 읽는 언어 모델이다. 이 저장소는 Claude Haiku 5.5, Sonnet 5.5, Opus 5.5로 한 실험의 기록이다. 모델에게 실제 사진 한 장과 캡션(사진 아래 붙는 한두 문장의 설명) 하나를 보여 주고 캡션이 사진과 맞는지 물었다. 캡션은 사진에 맞는 것과, 사건이나 장소나 날짜 가운데 하나만 바꾼 틀린 것을 썼다. 맞는 캡션에 다른 사건의 사진을 붙인 경우도 물었다. 묻는 말은 두 가지다.

- QM: "Does the photo show what the caption describes?" (사진이 캡션이 말하는 것을 보여 주는가?)
- QA: "Is the caption accurate?" (캡션이 사실인가?)

QM과 QA는 이 실험에서 두 질문에 붙인 이름이다. 처음 질문의 match(맞는가)와 accurate(사실인가)에서 땄다.

사진은 2026년 7월부터 11월 초까지 찍어 Wikimedia Commons에 올린 행사 사진이고 캡션은 우리가 붙였다. 모델이 학습한 자료에는 없을 사건이라 기억만으로 맞히기 어렵다. 다만 해마다 열리는 행사의 일정처럼 미리 알 수 있는 사실은 예외다(E-011). 팩트체크 기사에서 모은 VERITE 자료로도 물었지만 그 설정과 답은 이 저장소에 없다(아래 "공개하지 않은 자료").

설계, 판정 규칙, 결과, 해석은 모두 한국어로 썼다. 처음 읽는다면 `docs/EVIDENCE.md`의 "기사 실험 읽는 법"부터 보면 된다.

## 주요 결과

확인 실험(E-013): 탐색에 쓰지 않은 Commons 문항 63개로 주장 네 개를 다시 판정했다. 문항 하나는 사진 한 장, 맞는 캡션, 틀린 캡션, 다른 사건의 사진으로 이루어진다. 미리 정한 판정 16개가 모두 "확인"으로 나왔다. 여러 항목을 함께 판정하면 그중 하나가 우연히 확인될 확률이 커진다. 그래서 Bonferroni 보정으로 넓힌 99.69% 구간을 썼다. 아래에서 %p(퍼센트포인트)는 두 백분율의 차이다.

- C1, C2: 맞는 캡션을 붙였을 때보다 틀린 캡션이나 다른 사건의 사진을 붙였을 때, 세 모델 모두 "아니다"라고 답한 비율이 늘었다. 늘어난 폭은 틀린 캡션에서 54.0%p에서 60.3%p까지, 다른 사진에서 65.1%p에서 74.6%p까지다. 늘어난 몫은 대부분 사진으로 확인할 수 있는 문항에서 나왔다.
- C3: QM으로 물었을 때 Haiku와 Sonnet은 맞는 캡션에도 "그렇다"보다 "알 수 없다"를 더 많이 골랐다. "알 수 없다" 비율에서 "그렇다" 비율을 뺀 값은 Haiku 90.5%p, Sonnet 41.3%p다. 그래서 맞는 캡션과 틀린 캡션의 "그렇다" 비율 차이만 보면, 두 모델이 틀린 캡션을 잘 가려내지 못하는 것처럼 보인다.
- C4: 날짜처럼 사진에 단서가 적은 사실을 바꾼 캡션이면 Haiku와 Sonnet은 "사실인가"에 "알 수 없다"를 30%보다 많이 골랐다(Haiku 75.0%, Sonnet 64.3%). 판정은 우리가 "사진으로 확인할 수 없음"으로 표시한 문항으로 했다. 장소 문항에서는 이 표시가 모델의 판단과 잘 맞지 않았다(E-014).

탐색(확인된 결과로 쓰지 않음):

- E-015: 같은 문항을 "Does anything in the photo contradict the caption?"(사진에 캡션과 어긋나는 것이 있는가?)으로도 물었다. 그러자 맞는 캡션에 "알 수 없다"라고 한 비율이 크게 줄고 "어긋나는 것이 없다"는 답이 늘었다. 사진과 어긋나는 틀린 캡션은 여전히 걸렀다. 대신 사진으로 확인할 수 없는 틀린 캡션에도 33%에서 53%는 "어긋나는 것이 없다"고 답했다. QM으로 물었을 때 이런 캡션을 받아들인 비율은 4%에서 12%였다. "어긋나는 것이 없다"는 캡션이 사실이라고 확인했다는 뜻이 아니다.
- E-014: 우리가 "사진으로 확인할 수 없음"으로 표시한 장소 문항에서도 Sonnet과 Opus는 틀린 캡션을 82% 걸렀다. 읽어 본 Opus의 생각 요약 두 개는 사진 속 광고의 회사 이름과 선수의 소속 구단을 근거로 들었다.
- E-009부터 E-012: 탐색 실행의 결과다. VERITE에서 Opus는 사진 없이 두 캡션만 주어도 맞는 쪽을 골랐다. 그래서 VERITE 결과에는 사진을 보고 판단한 몫 말고도 팩트체크 기사를 기억해 맞힌 몫이 컸다고 본다.

## 설계서를 먼저 공개한 기록

- 확인 실험의 설계서 `docs/specs/2026-11-08-caption-confirm.md`는 모델을 부르기 전에 이 저장소의 첫 커밋 `96996f2`로 올렸다(push 2026-11-09T03:05:58Z, 모델 호출 2026-11-09T03:07:11Z). 설계서 맨 위의 안내는 설계서만 먼저 올렸을 때 쓴 것이어서, 그 아래에 날짜를 붙인 한 줄을 더했다.
- 묻는 말 탐색(E-015)의 설계서 `docs/specs/2026-11-09-caption-wording.md`는 탐색이라 미리 공개하지 않았다. 비공개 저장소에 커밋한 뒤 그 커밋에서 실행했다(`results/caption_wording/manifest.json`의 revision).
- 탐색 실행은 시험 실행을 본 뒤 설계를 두 번 고쳤다(r1, r2). 고친 근거가 된 시험 문항은 본 실행에서 뺐다. 경위는 `docs/specs/2026-11-04-caption-pilot.md`에 있다.

## 저장소 구성

| 경로 | 내용 |
| --- | --- |
| `docs/specs/` | 설계서. 탐색(`2026-11-04-caption-pilot.md`), 확인(`2026-11-08-caption-confirm.md`), 묻는 말 탐색(`2026-11-09-caption-wording.md`) |
| `docs/EVIDENCE.md` | 결과와 해석(E-009부터 E-015). 비공개 연구 기록에서 옮겼다 |
| `docs/literature/RELATED_WORK.md` | 선행연구와 데이터를 확인한 기록 |
| `configs/` | 문항, 캡션, 사진 해시, 보기 순서를 고정한 Commons 설정. `caption_v1_commons.json`, `caption_v1r1_commons.json`(시험 실행), `caption_v1r2_commons.json`(탐색 본 실행), `caption_confirm_v1.json`(확인), `caption_wording_v1.json`(묻는 말 탐색) |
| `results/` | 모델의 답(`*.jsonl`, 받은 메시지 그대로), 결과 표(`report.md`), 실행 기록(`manifest.json`). `caption_smoke_commons/`와 `caption_r1_smoke_commons/`는 시험 실행, `caption_r2_commons/`는 탐색, `caption_confirm/`은 확인, `caption_wording/`은 묻는 말 탐색 |
| `data/captions/` | Commons 문항 목록(`items.json`)과 사진 출처(`credits.json`: 만든 사람, 라이선스, 링크) |
| `src/vtrust/`, `tests/` | 요청을 만들고 보내고 분석하는 코드와 테스트 |
| `tools/pick_captions.py` | Commons 범주를 훑어 행사와 사진 후보를 모으는 도구. 모델 API를 부르지 않는다 |
| `prompts/agent_prompts.md` | 행사와 사진을 고르고 1000픽셀 사진으로 다시 확인한 에이전트(Claude Fable 5.1, 실험 대상 아님)에게 준 지시 |

같은 코드 묶음(`vtrust`)에 앞선 실험인 같은 상품 판정 실험 코드도 들어 있다. 그 실험의 기록은 https://github.com/gseungho/vlm-same-item-test 에 있다.

## 결과 표 다시 만들기

저장된 답으로 결과 표(`report.md`)를 다시 만들 수 있다. API를 부르지 않는다.

```
python -m venv .venv
.venv/bin/pip install -e ".[dev,sample]"   # Windows는 .venv\Scripts\pip. sample은 테스트가 쓰는 Pillow
.venv/bin/python -m pytest
.venv/bin/python -m vtrust.caption_run report main --config configs/caption_v1r2_commons.json
.venv/bin/python -m vtrust.caption_run report main --config configs/caption_confirm_v1.json
.venv/bin/python -m vtrust.caption_run report main --config configs/caption_wording_v1.json
```

묻는 말 탐색의 표는 다시 물은 답을 앞선 실행과 비교하려고 `results/caption_r2_commons/`와 `results/caption_confirm/`의 답도 읽는다.

모델에게 다시 물으려면(유료) 사진이 `data/captions/photos/<사진 ID>.jpg`에 있어야 한다. 사진 ID는 `c` 뒤에 Commons 페이지 번호를 붙인 것이고 `credits.json`에 원본 링크가 있다. 원본의 긴 변을 1000픽셀로 줄인 파일이라, 코드가 확인하는 SHA-256이 이미지 라이브러리 버전에 따라 달라질 수 있다. API 키는 환경 변수 `KSYCO_ANTHROPIC_API_KEY`에서 읽는다. 모델이 바뀌었을 수 있으므로 같은 답이 나온다는 보장은 없다.

## 공개하지 않은 자료

- VERITE의 설정, 답, 이미지. VERITE 이미지는 연구용 승인을 받아서만 썼고, 설정과 답에는 VERITE의 캡션 문장이 들어 있어 올리지 않았다. VERITE의 수치와 해석은 `docs/EVIDENCE.md`에 있다.
- Commons 사진 파일. 출처와 라이선스는 `data/captions/*/credits.json`에 있다.
- 에이전트가 읽은 중간 파일(범주 목록, 사진 시트, 고르기 결과). 지시는 `prompts/agent_prompts.md`에 있다.
- 연구 진행 기록(작업 일지, 현재 상태, 결정 기록, 교차 검토 기록). `docs/EVIDENCE.md`와 설계서에 나오는 `RESEARCH_PLAN.md`, `LOG.md`, `STATUS.md`가 그것이고, 이 파일로 가는 링크는 열리지 않는다.

## 결과를 읽을 때 주의할 점

- 각 조건을 한 번씩만 물었다. 묻는 말 탐색에서 QM을 한 번 더 물었더니, 앞선 실행과 같은 답이 나온 문항이 74%에서 98%였다. 두 실행 사이에 두 지표를 모델마다 비교했다. 하나는 맞는 캡션의 "알 수 없다" 비율에서 "그렇다" 비율을 뺀 값이고, 다른 하나는 틀린 캡션과 맞는 캡션의 "아니다" 비율 차이다. 달라진 폭은 점추정으로 -3.9%p에서 +9.4%p였다. 변화가 작다고 판정한 것은 Haiku의 두 번째 지표뿐이고, 나머지는 판정하지 못했다(E-015 재해석).
- "사진으로 확인할 수 있는가" 표시는 실험 대상이 아닌 에이전트가 사진만 보고 정했다. 모델이 사진 속 글자나 행사 일정 같은 지식을 쓰면 이 표시와 맞지 않는다(E-011, E-014).
- 확인 실험은 목표 90문항보다 적은 63문항이다(미리 정한 하한은 60문항).
- 세 모델 모두 adaptive thinking(답하기 전에 생각할지와 얼마나 생각할지를 모델이 정하는 설정)을 켜고 생각 요약을 받았다. Sonnet은 생각을 거의 쓰지 않고 답했다.

## 라이선스

- 코드(`src/`, `tests/`, `tools/`): MIT. `LICENSE`를 보라.
- 문서, 설정, 결과, 캡션(`docs/`, `configs/`, `results/`, `data/`, `prompts/`, 이 README): CC BY 4.0(https://creativecommons.org/licenses/by/4.0/).
- Commons 사진은 각 사진의 라이선스(CC BY, CC BY-SA, CC0, 공유 저작물)를 따른다. `credits.json`을 보라. 사진 파일은 이 저장소에 없다.
