# API 계약

> 현재 가격 경로는 공공데이터포털 `perRegion/price`입니다. 인증·단위는 [포털 연동](portal-integration.md)을 참고하세요.

| 경로 | 동작 |
|---|---|
| `GET /api/health` | 앱 버전, KAMIS·AI 설정 여부, 예측 모델 미연결 상태 |
| `GET /api/examples/scenario` | 배추 합성 시나리오 전체 입력 |
| `POST /api/simulation` | 현재 배분의 판매대금·항목별 비용·수취액 |
| `POST /api/strategies/compare` | 현재·단일·격자 후보 및 스트레스 결과 비교 |
| `POST /api/ai/ask` | 선택적으로 연결한 AI의 현재 화면 설명 |
| `GET /api/kamis/prices` | 조건별 KAMIS 조회·정규화·분석 |

시뮬레이션 입력 전체 예제는 [합성 시나리오](../examples/cabbage.synthetic.json)입니다. 단위는 kg·원·원/kg·백분율이며, 상품화율과 수수료율은 0~100입니다. 총 물량은 정수 0~100,000kg, 시장은 2~3개입니다. 알 수 없는 필드는 거부합니다.

비율 합 100% 불일치·음수·비정상 숫자·범위 초과·차량 용량 0·비용률 합 초과·현재 배분의 물량 제약 위반은 HTTP 422입니다. 현재 배분이 성립하지 않으면 결과를 성공으로 반환하지 않습니다.

계산 응답의 `gross`는 판매대금, `cost`는 기타 비용 포함 전체 비용, `net`은 예상 순수취액입니다. `routes`는 항목별 계산을 포함합니다. 비교 응답의 `best`는 기본 수취액 최대, `conservative`는 입력된 스트레스 조건에서 수취액 최대, `lowest_transport`는 운송비 최소 후보입니다. 통계적으로 검증된 위험·보수성 순위가 아닙니다.

KAMIS 요청 예시: `/api/kamis/prices?start=2026-10-01&end=2026-10-27&region=1101&kind=03&rank=04`.

KAMIS의 `status`는 `not_configured`, `upstream_error`, `empty`, `live` 중 하나입니다. `live`는 실제 인증 API 응답의 가격·단위를 검증한 경우에만 사용합니다. `live`가 실시간 경매 가격이라는 의미는 아닙니다. 코드 테스트에서는 합성 응답을 주입하므로 테스트 통과가 실제 조회 성공을 증명하지 않습니다.

가격 조회는 시작일·종료일 필수, 최대 31일 간격, KST 오늘까지입니다. 응답 실패 상세나 인증값은 브라우저 응답에 포함하지 않습니다. 서버 재시작 시 메모리 캐시는 사라집니다.


## 조회 근거 메타데이터

각 시계열의 `analysis`는 전체 관측 건수 `observations`, 첫 조사일 `first_date`, 변화율 비교의 실제 달력 일수 `reference_gap_days`를 포함합니다. 정확히 7일 전이 없으면 더 이전 조사값을 사용하므로 화면과 저장 자료에서 실제 비교일·간격을 확인해야 합니다.

조회 실패의 `error_kind`는 `authentication`, `parameters`, `connection`, `format`, `schema`, `upstream`입니다. 현재 포털 어댑터는 `00`/`000`/`0`을 정상 코드로, `20`/`30`/`31`을 인증 오류로, 다른 비정상 코드를 `upstream`으로 분류합니다. 원문 메시지·HTTP 예외 URL·인증값은 돌려주지 않습니다.

프론트엔드의 별도 근거 JSON은 선택 시계열과 조회 조건·분석·출처를, CSV는 선택 가격표를 저장합니다. 조건·결과 JSON의 `decision_context`는 사용자가 KAMIS 참고 비교 버튼을 누른 경우의 자료와 −10% 가정을 보존합니다. 이후 변경한 하락률은 `current_price_drop_pct`와 `assumption_has_changed`로 구분합니다. −10%는 조사 변화율에서 추정한 경매 하락률이 아닙니다.

관측 변화율이 음수이면 **관측 하락률을 같은 하락 가정으로 비교**하는 추가 버튼을 제공합니다. 조사 가격의 실제 과거 하락률을 경매가에도 동일하게 가정하는 스트레스이며, 두 가격 사이의 전이 관계나 미래 경매 하락률을 검증한 값은 아닙니다. 저장 자료의 `assumption.basis`는 이 경우 `observed_change_scenario`, 별도 −10% 검토는 `manual_review`로 구분합니다.

## 선택적 AI 설명

`GET /api/health`의 `ai_configured`는 서버 환경변수 `OPENAI_API_KEY`와 `OPENAI_MODEL`의 설정 여부입니다. 실제 제공자 인증·모델 이용 성공을 보장하지 않습니다. 기존 시뮬레이션과 KAMIS 인증 설정에 영향을 주지 않습니다.

`POST /api/ai/ask`는 `question`(1~500자), `history`(최대 12개 user/assistant 기록), `sheet_context`(화면 입력·계산 결과·KAMIS 분석 요약)를 받습니다. 요청 크기는 32KiB이며, 성공 응답은 `answer`, `sources`(최대 5개 탭/라벨), `disclaimer`입니다. 근거 탭 값은 `simulator`, `map`, `detail`, `kamis`, `basis`로 제한됩니다.

HTTP 413은 요청 크기 초과, 422는 잘못된 입력, 429는 분당 제한(프로세스별 IP당 10회), 503은 AI 미설정, 502는 제공자 실패·시간 초과·잘못된 응답입니다. 예외 원문·인증키는 반환하지 않습니다. 제한 정보는 메모리에서만 유지되며 재시작하면 초기화됩니다.

OpenAI Responses API에 `store=false`와 구조화된 JSON 응답 형식을 사용합니다. 서버 제한 시간은 30초입니다. 모델은 환경변수로 명시하고, 자동으로 선택하거나 유료 키를 발급하지 않습니다. 질문 전송 시 화면 요약이 제공자에게 전달됨을 UI에 표시하며 서버의 대화 저장 DB는 없습니다. 브라우저 탭 세션에 최근 대화를 보관하고 사용자가 지울 수 있습니다. 계산 결과·새 가격 예측을 AI로 대체하지 않습니다.
