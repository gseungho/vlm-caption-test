# 진짜 사진에 틀린 캡션이 붙으면 VLM은 알아차리는가

VLM(이미지와 글을 함께 읽는 언어 모델)인 Claude Haiku 5.5, Sonnet 5.5, Opus 5.5에게 진짜 사진 한 장과 캡션(사진 아래 붙는 한두 문장의 설명) 하나를 보여 주고 물은 실험의 기록이다. 사진에 맞는 캡션과, 사건이나 장소나 날짜 가운데 하나를 바꾼 틀린 캡션을 쓴다. 맞는 캡션에 다른 사건의 사진을 붙인 쌍도 묻는다. 묻는 말은 두 가지다.

- QM: "Does the photo show what the caption describes?" (사진이 캡션이 말하는 것을 보여 주는가?)
- QA: "Is the caption accurate?" (캡션이 사실인가?)

사진은 2026년 7~11월에 찍어 Wikimedia Commons에 올린 행사 사진이고 캡션은 우리가 붙였다. 모델이 학습한 자료에는 없을 사건이라 기억으로 풀기 어렵다. 다만 해마다 열리는 행사의 일정처럼 미리 알 수 있는 사실은 예외다(E-011). 팩트체크 기사에서 모은 VERITE 자료로도 물었지만 그 설정과 답은 이 저장소에 없다(아래 "빠진 것").

설계, 판정 규칙, 결과, 해석은 모두 한국어로 썼다. 처음 읽는다면 `docs/EVIDENCE.md`의 "기사 실험 읽는 법"부터 보면 된다.

## 무엇이 나왔는가

확인 실험(E-013): 탐색에 쓰지 않은 새 Commons 63문항으로 주장 네 개(판정 16개)를 판정했고 모두 확인됐다. 구간은 Bonferroni로 보정한 99.69% 구간이다.

- C1, C2: 틀린 캡션이나 다른 사건의 사진이 붙으면 세 모델 모두 "아니다"가 늘었다. 늘어난 폭은 틀린 캡션에서 +54.0~+60.3%p, 다른 사진에서 +65.1~+74.6%p다. 늘어난 "아니다"는 대부분 사진으로 확인할 수 있는 문항에서 나왔다.
- C3: Haiku와 Sonnet은 맞는 캡션을 "그렇다"보다 "알 수 없다"로 더 많이 두었다. "알 수 없다" 비율에서 "그렇다" 비율을 뺀 값이 Haiku +90.5%p, Sonnet +41.3%p다. 그래서 "그렇다"로 세면 알아차림이 작아 보인다.
- C4: 사진으로 확인할 수 없는 사실이면 Haiku와 Sonnet은 "사실인가"에 "알 수 없다"를 30%보다 많이 골랐다(75.0%, 64.3%).

탐색(확인된 결과로 쓰지 않음):

- E-015: 같은 문항에 "Does anything in the photo contradict the caption?"(사진에 캡션과 어긋나는 것이 있는가?)으로 물으면 맞는 캡션의 "알 수 없다"가 크게 줄었다. 사진과 어긋나는 틀린 캡션은 여전히 걸렀지만, 사진으로 확인할 수 없는 틀린 캡션은 33~53%가 통과했다(QM에서는 4~12%).
- E-014: 우리가 "사진으로 확인할 수 없음"으로 표시한 장소 문항에서도 Sonnet과 Opus는 틀린 캡션을 82% 걸렀다. 읽은 생각 요약에서 Opus는 사진 속 광고나 선수의 소속 구단을 근거로 들었다.
- E-009~E-012: 탐색 실행의 결과다. VERITE에서 Opus는 사진 없이 두 캡션만 주어도 맞는 쪽을 골라, VERITE의 값은 기억의 몫이 컸다.

## 순서 기록

- 확인 실험의 설계서 `docs/specs/2026-11-08-caption-confirm.md`는 모델을 부르기 전에 이 저장소의 첫 커밋 `96996f2`로 올렸다(push 2026-11-09T03:05:58Z, 모델 호출 2026-11-09T03:07:11Z). 설계서 맨 위의 공개본 안내에 "링크가 열리지 않는다"고 적었지만, 이제 그 링크가 가리키는 파일 대부분이 이 저장소에 있다.
- 묻는 말 탐색(E-015)의 설계서 `docs/specs/2026-11-09-caption-wording.md`는 탐색이라 미리 공개하지 않았다. 비공개 저장소에 커밋한 뒤 그 커밋에서 실행했다(`results/caption_wording/manifest.json`의 revision).
- 탐색 실행은 시험 실행을 본 뒤 설계를 두 번 고쳤다(r1, r2). 고친 근거가 된 시험 문항은 본 실행에서 뺐다. 경위는 `docs/specs/2026-11-04-caption-pilot.md`에 있다.

## 무엇이 있는가

| 경로 | 내용 |
| --- | --- |
| `docs/specs/` | 설계서. 탐색(`2026-11-04-caption-pilot.md`), 확인(`2026-11-08-caption-confirm.md`), 묻는 말 탐색(`2026-11-09-caption-wording.md`) |
| `docs/EVIDENCE.md` | 결과와 해석(E-009~E-015). 비공개 연구 기록에서 그대로 옮겼다 |
| `docs/literature/RELATED_WORK.md` | 선행연구와 데이터를 확인한 기록 |
| `configs/` | 문항, 캡션, 사진 해시, 보기 순서를 고정한 Commons 설정. `caption_v1_commons.json`, `caption_v1r1_commons.json`(시험 실행), `caption_v1r2_commons.json`(탐색 본 실행), `caption_confirm_v1.json`(확인), `caption_wording_v1.json`(묻는 말 탐색) |
| `results/` | 모델의 답(`*.jsonl`, 받은 메시지 그대로), 표(`report.md`), 실행 기록(`manifest.json`). `caption_smoke_commons/`와 `caption_r1_smoke_commons/`는 시험 실행, `caption_r2_commons/`는 탐색, `caption_confirm/`은 확인, `caption_wording/`은 묻는 말 탐색 |
| `data/captions/` | Commons 문항 목록(`items.json`)과 사진 출처(`credits.json`: 만든 사람, 라이선스, 링크) |
| `src/vtrust/`, `tests/` | 요청을 만들고 보내고 분석하는 코드와 테스트 |
| `tools/pick_captions.py` | Commons 범주를 훑어 행사와 사진 후보를 모으는 도구. 모델 API를 부르지 않는다 |
| `prompts/agent_prompts.md` | 행사와 사진을 고르고 1000픽셀 사진으로 다시 확인한 에이전트(Claude Fable 5.1, 실험 대상 아님)에게 준 지시 |

같은 코드 묶음(`vtrust`)에 앞선 실험인 같은 상품 판정 실험 코드도 들어 있다. 그 실험의 기록은 https://github.com/gseungho/vlm-same-item-test 에 있다.

## 다시 계산하기

표는 저장된 답에서 다시 만들 수 있다. API를 부르지 않는다.

```
python -m venv .venv
.venv/bin/pip install -e ".[dev,sample]"   # Windows는 .venv\Scripts\pip. sample은 테스트가 쓰는 Pillow
.venv/bin/python -m pytest
.venv/bin/python -m vtrust.caption_run report main --config configs/caption_v1r2_commons.json
.venv/bin/python -m vtrust.caption_run report main --config configs/caption_confirm_v1.json
.venv/bin/python -m vtrust.caption_run report main --config configs/caption_wording_v1.json
```

묻는 말 탐색의 표는 다시 물은 답을 비교하려고 `results/caption_r2_commons/`와 `results/caption_confirm/`의 답도 읽는다.

모델에게 다시 물으려면(유료) 사진이 `data/captions/photos/<사진 ID>.jpg`에 있어야 한다. 사진 ID는 `c` 뒤에 Commons 페이지 번호를 붙인 것이고 `credits.json`에 원본 링크가 있다. 원본의 긴 변을 1000픽셀로 줄인 파일이라, 코드가 확인하는 SHA-256이 이미지 라이브러리 버전에 따라 달라질 수 있다. API 키는 환경 변수 `KSYCO_ANTHROPIC_API_KEY`에서 읽는다. 모델이 바뀌었을 수 있으므로 같은 답이 나온다는 보장은 없다.

## 빠진 것

- VERITE의 설정, 답, 이미지. VERITE 이미지는 연구용 승인을 받아서만 썼고, 설정과 답에는 VERITE의 캡션 문장이 들어 있어 올리지 않았다. VERITE의 수치와 해석은 `docs/EVIDENCE.md`에 있다.
- Commons 사진 파일. 출처와 라이선스는 `data/captions/*/credits.json`에 있다.
- 에이전트가 읽은 중간 파일(범주 목록, 사진 시트, 고르기 결과). 지시는 `prompts/agent_prompts.md`에 있다.
- 연구 진행 기록(작업 일지, 현재 상태, 결정 기록). `docs/EVIDENCE.md`에 나오는 `RESEARCH_PLAN.md`, `LOG.md`가 그것이다.

## 함께 밝힐 점

- 각 조건을 한 번씩만 물었다. 묻는 말 탐색에서 QM을 다시 물었더니 문항마다 앞선 실행과 같은 답이 나온 비율은 74~98%였다. 평균의 차이는 점추정으로 -3.9~+9.4%p였고, 작다고 판정한 것은 Haiku의 틀린 캡션 값 하나뿐이다. 평균이 다시 물어도 같은지는 판정하지 못했다(E-015 재해석).
- "사진으로 확인할 수 있는가" 표시는 실험 대상이 아닌 에이전트가 사진만 보고 정했다. 모델이 사진 속 글자나 행사 일정 같은 지식을 쓰면 이 표시와 맞지 않는다(E-011, E-014).
- 확인 실험은 목표 90문항보다 적은 63문항이다(하한 60).
- Sonnet은 거의 생각하지 않고 답했다.

## 라이선스

- 코드(`src/`, `tests/`, `tools/`): MIT. `LICENSE`를 보라.
- 문서, 설정, 결과, 캡션(`docs/`, `configs/`, `results/`, `data/`, `prompts/`, 이 README): CC BY 4.0(https://creativecommons.org/licenses/by/4.0/).
- Commons 사진은 각 사진의 라이선스(CC BY, CC BY-SA, CC0, 공유 저작물)를 따른다. `credits.json`을 보라. 사진 파일은 이 저장소에 없다.
