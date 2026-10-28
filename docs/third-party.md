# 외부 패키지와 시각 자산

앱은 별도 사진·지도 타일을 다운로드하지 않습니다. 물량 흐름과 가격 차트는 앱 SVG로 그립니다. 지도는 Natural Earth 1:50m 지형을 사용하며 표시 지점과 차량 이동은 예시 시뮬레이션입니다. IBM Plex Sans KR와 IBM Plex Mono는 Google Fonts 스타일시트로 불러옵니다. 네트워크 연결이 없으면 시스템 글꼴로 대체합니다. 두 글꼴은 SIL Open Font License 1.1이며 [IBM Plex 공식 저장소](https://github.com/IBM/plex)에 원본·라이선스가 있습니다.

| 패키지 | 용도 | 패키지 표기 라이선스 |
|---|---|---|
| React, React DOM | UI | MIT |
| Vite, React Vite plugin | 개발·빌드 | MIT |
| TypeScript | 타입 검사 | Apache-2.0 |
| lucide-react | 아이콘 | ISC |
| FastAPI | API | MIT |
| Uvicorn | ASGI 서버 | BSD-3-Clause |
| HTTPX | KAMIS 및 선택적 AI 호출 | BSD-3-Clause |
| Pydantic | 입력 검증 | MIT |
| pytest | 검증 | MIT |

전체 전이 의존성의 저작권·라이선스 고지는 각 설치 패키지에 포함됩니다. 배포 패키징 시 해당 고지를 유지해야 합니다. 위 코드 패키지의 라이선스는 KAMIS·경매·외부 데이터의 재배포 허가를 대신하지 않습니다.


## 지도 데이터

Natural Earth Admin 0 countries 1:50m, world-atlas@2.0.2 `countries-50m.json`을 topojson-client@3.1.0으로 GeoJSON 변환했습니다. 대한민국·북한·중국·일본 지형을 포함하고 출처 메타데이터를 함께 보존합니다. 데이터는 Public Domain이며 [공식 이용조건](https://www.naturalearthdata.com/about/terms-of-use/)을 2026-10-27 확인했습니다. world-atlas 및 topojson-client는 ISC입니다. 변환 도구는 개발용으로만 사용했으며 앱 런타임 의존성을 추가하지 않았습니다.

지도는 오프라인 렌더링 가능한 간략 지형 데이터입니다. WGS84 예시 좌표를 투영하며, 지역을 참고한 예시 출발점·시장 지점은 시설의 정확한 위치로 검증한 좌표가 아닙니다. 이동은 지점 간 직선 연결로 실제 도로·차량 GPS·도착 시간을 나타내지 않습니다. 지도 출발점 좌표는 지도에서 별도로 조절하며 출발지 텍스트를 자동 지오코딩하지 않습니다.

## 선택적 AI 연결

OpenAI Responses API는 서버에서만 호출하며 브라우저에 API 키를 전달하지 않습니다. 계산 결과는 기존 Python 엔진이 산출하며 AI는 화면 문맥 설명에만 사용합니다. 별도 AI SDK나 가격 예측 모델을 추가하지 않았습니다. 설정·전송 범위는 [배포 안내](deployment.md)를 참고하세요.
