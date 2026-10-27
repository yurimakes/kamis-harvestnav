import type { Prices, PriceSeries } from './types';

export type PriceDecision = {
  captured_at: string;
  source_name: string;
  retrieved_at: string;
  query: Prices['query'];
  series: PriceSeries;
  assumption: { price_drop_pct: number; basis: 'manual_review' | 'observed_change_scenario'; explanation: string };
};

export function saveFile(name: string, content: string, type = 'application/json') {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement('a');
  a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function makeDecision(prices: Prices, series: PriceSeries, observed = false): PriceDecision {
  const observedDrop = series.analysis.change_pct !== null && series.analysis.change_pct < 0;
  const useObserved = observed && observedDrop;
  return {
    captured_at: new Date().toISOString(), source_name: prices.source_name,
    retrieved_at: prices.retrieved_at!, query: { ...prices.query }, series,
    assumption: {
      price_drop_pct: useObserved ? -series.analysis.change_pct! : 10,
      basis: useObserved ? 'observed_change_scenario' : 'manual_review',
      explanation: useObserved ? '과거 조사 가격의 관측 하락률이 가정 경매가격에도 동일하게 발생한다고 놓은 스트레스. 향후 경매 하락률의 예측·검증된 전이 관계가 아님.' : '조사 가격 변화율과 별도로 설정한 사용자 검토용 가정. 경매 단가 치환·가격 예측·인과 효과 추정이 아님.',
    },
  };
}

const csvCell = (value: unknown) => {
  const text = String(value ?? '');
  // Spreadsheet applications may execute cells beginning with formula markers.
  const safe = /^[\s]*[=+\-@]/.test(text) ? `'${text}` : text;
  return `"${safe.replaceAll('"', '""')}"`;
};

export function PriceEvidence({ prices, series, onCompare }: { prices: Prices; series: PriceSeries; onCompare: (decision: PriceDecision) => void }) {
  const valid = prices.source === 'kamis' && prices.status === 'live' && !!prices.retrieved_at && series.prices.length > 0;
  const record = () => ({
    evidence_version: 1, exported_at: new Date().toISOString(),
    source_name: prices.source_name, documentation: prices.documentation,
    retrieved_at: prices.retrieved_at, as_of: prices.as_of, cached: !!prices.cached,
    query: prices.query, unit: prices.unit, quality: prices.quality,
    selected_series: series,
    scope: '조회 API에서 정규화·검증한 선택 시계열. 별도의 원천값 수동 대조·현장 효과 검증이 필요합니다.',
  });
  const csv = () => {
    const rows = [['조사일', '가격(원/kg)', '품목', '품종', '등급 코드', '지역', '조사시장', '출처', '조회 시각', '원 조사가격', '원 단위', '단위크기', '중량(kg)'],
      ...series.prices.map(p => [p.date, p.price_per_kg, series.item, series.variety, prices.query.rank_code, series.region, series.market, prices.source_name, prices.retrieved_at, p.original_price, p.original_unit, p.original_unit_size, p.weight_kg])];
    saveFile('harvestnav-kamis-prices.csv', '\ufeff' + rows.map(row => row.map(csvCell).join(',')).join('\r\n'), 'text/csv;charset=utf-8');
  };
  return <section className="price-evidence" aria-label="KAMIS 활용 근거">
    <div className="panel-heading"><h3>조회와 분석 근거 남기기</h3><span className="badge muted">선택 시계열 {series.prices.length}건</span></div>
    <dl className="evidence-facts">
      <div><dt>관측 범위</dt><dd>{series.prices[0].date} ~ {series.analysis.latest_date}</dd></div>
      <div><dt>조회 조건 코드</dt><dd>품목 {prices.query.item_code} · 품종 {prices.query.kind_code} · 등급 {prices.query.rank_code} · 지역 {prices.query.region_code}</dd></div>
      <div><dt>변화율 비교 간격</dt><dd>{series.analysis.reference_gap_days == null ? '7일 이전 관측 자료 부족' : `${series.analysis.reference_gap_days}일 · ${series.analysis.reference_date} 기준`}</dd></div>
    </dl>
    <p className="subtle">결측·중복 건수는 이번 조회 전체 기준입니다. 조사하지 않은 날은 보간하지 않으며, 비교 간격이 정확히 7일인지는 위 날짜로 확인하세요.</p>
    <div className="evidence-actions">
      <button className="button ghost" disabled={!valid} onClick={() => saveFile('harvestnav-kamis-evidence.json', JSON.stringify(record(), null, 2))}>조회·분석 근거 JSON 저장</button>
      <button className="button ghost" disabled={!valid} onClick={csv}>선택 가격표 CSV 저장</button>
      <button className="button primary" disabled={!valid} onClick={() => onCompare(makeDecision(prices, series))}>이 자료를 참고해 가격 −10% 조건 비교 →</button>
      {series.analysis.change_pct !== null && series.analysis.change_pct < 0 && <button className="button ghost" disabled={!valid} onClick={() => onCompare(makeDecision(prices, series, true))}>관측 하락률 {series.analysis.change_pct}%를 같은 하락 가정으로 비교 →</button>}
    </div>
    <p className="subtle">−10%는 검토용 가정입니다. 저장 자료에는 출처·조회 시각·코드·조사일·선택 시계열·분석값이 포함되며 인증정보는 포함하지 않습니다.</p>
    {series.analysis.change_pct !== null && series.analysis.change_pct < 0 && <p className="subtle">관측 하락률 비교는 과거 조사 가격의 변화와 같은 하락을 경매가격에도 가정합니다. 두 가격의 변화가 같다는 관계를 검증하거나 미래를 예측한 결과는 아닙니다.</p>}
  </section>;
}
