# 외부 패키지와 시각 자산: 출처 및 이용조건

이 문서는 HarvestNav 저장소의 코드·서비스 화면에 사용한 주요 자료 및 시각 자산의 출처와 이용조건을 기록합니다. 관련 문서에 별도로 사용하는 이미지·로고·글꼴의 이용조건은 각 자산의 원출처에서 확인합니다.

## 자료 및 시각 자산 출처

| 구분 | 출처·저작권자 | 사용 범위·이용조건 |
|---|---|---|
| 농산물 가격 자료 | [한국농수산식품유통공사(aT) KAMIS, 공공데이터포털](https://www.data.go.kr/data/15156062/openapi.do) | 지역별 품목별 도·소매 가격정보 API. 상세 페이지에 이용허락범위 제한 없음·무료로 표시. 호출 한도 준수 |
| 지도 지형 | [Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/) | Admin 0 Countries 1:50m, Public Domain. [world-atlas](https://github.com/topojson/world-atlas) 데이터 경유, [topojson-client](https://github.com/topojson/topojson-client)로 변환 |
| 웹 글꼴 | [IBM Plex Sans KR, IBM Plex Mono](https://github.com/IBM/plex) | SIL Open Font License 1.1. Google Fonts를 통해 불러옴 |
| 웹 UI 아이콘 | [Lucide Icons, lucide-react](https://github.com/lucide-icons/lucide/blob/main/LICENSE) | ISC, 일부 Feather 유래 아이콘에 MIT 고지 포함 |
| 그래프·배분선·차량 이동 | 프로젝트의 React/SVG 구현 | 외부 지도 데이터와 아이콘을 사용한 부분은 위 권리조건을 따르며, 이동 경로와 물량은 예시 시뮬레이션 |

앱은 별도 사진·지도 타일을 다운로드하지 않습니다. 물량 흐름과 가격 차트는 앱 SVG로 그립니다. 지도는 Natural Earth 1:50m 지형을 사용하며 표시 지점과 차량 이동은 예시 시뮬레이션입니다. IBM Plex Sans KR와 IBM Plex Mono는 Google Fonts 스타일시트로 불러옵니다. 네트워크 연결이 없으면 시스템 글꼴로 대체합니다. 두 글꼴은 SIL Open Font License 1.1이며 [IBM Plex 공식 저장소](https://github.com/IBM/plex)에 원본·라이선스가 있습니다.

| 패키지 | 용도 | 패키지 표기 라이선스 |
|---|---|---|
| React, React DOM | UI | MIT |
| Vite, React Vite plugin | 개발·빌드 | MIT |
| TypeScript | 타입 검사 | Apache-2.0 |
| lucide-react | 아이콘 | ISC (일부 Feather 유래 아이콘 MIT 고지 포함) |
| FastAPI | API | MIT |
| Uvicorn | ASGI 서버 | BSD-3-Clause |
| HTTPX | KAMIS 및 선택적 AI 호출 | BSD-3-Clause |
| Pydantic | 입력 검증 | MIT |
| pytest | 검증 | MIT |

전체 전이 의존성의 저작권·라이선스 고지는 각 설치 패키지에 포함됩니다. 배포 패키징 시 해당 고지를 유지해야 합니다. 위 코드 패키지의 라이선스는 KAMIS·경매·외부 데이터의 재배포 허가를 대신하지 않습니다.


## 지도 데이터

Natural Earth Admin 0 countries 1:50m, world-atlas@2.0.2 `countries-50m.json`을 topojson-client@3.1.0으로 GeoJSON 변환했습니다. 대한민국·북한·중국·일본 지형을 포함하고 출처 메타데이터를 함께 보존합니다. 데이터는 Public Domain이며 [공식 이용조건](https://www.naturalearthdata.com/about/terms-of-use/)을 2026-10-27 확인했습니다. world-atlas 및 topojson-client는 ISC입니다. 변환 도구는 개발용으로만 사용했으며 앱 런타임 의존성을 추가하지 않았습니다.

지도는 오프라인 렌더링 가능한 간략 지형 데이터입니다. WGS84 예시 좌표를 투영하며, 지역을 참고한 예시 출발점·시장 지점은 시설의 정확한 위치로 검증한 좌표가 아닙니다. 이동은 지점 간 직선 연결로 실제 도로·차량 GPS·도착 시간을 나타내지 않습니다. 지도 출발점 좌표는 지도에서 별도로 조절하며 출발지 텍스트를 자동 지오코딩하지 않습니다.

## 관련 문서와 아키텍처 구성도의 자산

관련 문서나 아키텍처 구성도에 기업 또는 제품 로고를 사용하는 경우, 각 권리자의 공식 로고·브랜드 가이드에 따라 허용된 사용 범위와 수정 여부를 확인해야 합니다. 소프트웨어 오픈소스 라이선스는 기업 상표·로고의 사용허락과 별개입니다. 권리를 확인하지 못한 로고는 일반 도형과 기술명 텍스트로 대체할 수 있습니다.

이 저장소의 서비스 UI에는 별도 인물 사진이 포함되지 않습니다. 관련 문서의 사진·이미지·스크린샷에 사람이나 제3자 저작물이 포함되는 경우 초상권과 해당 자산의 이용조건을 확인해야 합니다. 문서에 사용한 글꼴 역시 웹서비스 글꼴과 구분하여 실제 사용한 글꼴의 조건을 확인해야 합니다.

위 출처 고지의 범위는 저장소와 서비스 화면의 구성 요소입니다. 관련 문서에 별도로 추가하는 이미지·글꼴·로고는 해당 자산별 이용조건을 따릅니다.

## AI 설명 서비스

AI 설명 기능은 OpenAI Responses API를 사용하도록 구성되어 있습니다. AI는 Python 계산 엔진이 산출한 결과를 설명하며, 출하 수취액 계산이나 가격 예측을 수행하지 않습니다. 서버는 HTTPX로 API를 호출합니다. 모델 설정·사용료·데이터 전송 범위는 [배포 안내](deployment.md), 요청·응답 형식은 [API 계약](api.md)을 참고하세요.
