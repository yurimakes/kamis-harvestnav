import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ArrowDownRight, ArrowRight, BarChart3, Check, ChevronRight, CircleHelp, ClipboardList, Download, MapPin, Play, RefreshCw, Route as RouteIcon, Settings2, ShieldCheck, Sparkles, Sprout, X } from 'lucide-react';
import { LiveFlow, ShipmentMap } from './Movement';
import { WorkSheet, ResultVerdict } from './WorkSheet';
import { AiAssistant } from './AiAssistant';
import { EvidenceView } from './EvidenceView';
import { KamisView } from './KamisView';
import { saveFile } from './PriceEvidence';
import type { PriceDecision } from './PriceEvidence';
import type { Comparison, Market, Prices, PriceSeries, Result, Scenario } from './types';
import './style.css';
import './worksheet.css';
import './redesign.css';

const number = (v:number) => new Intl.NumberFormat('ko-KR', {maximumFractionDigits:0}).format(v);
const won = (v:number) => `${number(v)}원`;
const today = () => new Intl.DateTimeFormat('sv-SE', {timeZone:'Asia/Seoul'}).format(new Date());
const dateBefore = (days:number) => {const d=new Date(`${today()}T12:00:00+09:00`);d.setDate(d.getDate()-days);return new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Seoul'}).format(d);};

async function api<T>(path:string, init?:RequestInit):Promise<T> {
  const response = await fetch(path, init);
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '입력값과 연결 상태를 확인해 주세요.');
  return data;
}

function Field({label,value,onChange,unit,min=0,max=1e9,step=1}:{label:string;value:number;onChange:(v:number)=>void;unit?:string;min?:number;max?:number;step?:number}) {
  return <label className="field"><span>{label}</span><span className="input-wrap"><input type="number" min={min} max={max} step={step} value={Number.isNaN(value)?'':value} onChange={e=>onChange(e.currentTarget.valueAsNumber)}/>{unit&&<small>{unit}</small>}</span></label>;
}

function PriceChart({series}:{series:PriceSeries}) {
  const p=series.prices, values=p.map(x=>x.price_per_kg), low=Math.min(...values)*0.96, high=Math.max(...values)*1.04;
  const first=Date.parse(p[0].date), last=Date.parse(p[p.length-1].date);
  const xy=p.map(x=>[50+(Date.parse(x.date)-first)/Math.max(1,last-first)*700, 195-(x.price_per_kg-low)/Math.max(1,high-low)*160]);
  return <svg viewBox="0 0 800 250" className="price-chart" role="img" aria-label={`실제 KAMIS 조사 가격 ${p.length}건. ${p[0].date}부터 ${p[p.length-1].date}까지, 최근 ${won(p[p.length-1].price_per_kg)} / kg`}>
    {[0,1,2,3].map(i=><g key={i}><line x1="50" x2="750" y1={35+i*53} y2={35+i*53} stroke="var(--hn-line)"/><text x="43" y={39+i*53} textAnchor="end" className="svg-muted">{number(high-(high-low)*i/3)}</text></g>)}
    <polyline points={xy.map(x=>x.join(',')).join(' ')} fill="none" stroke="var(--hn-forest)" strokeWidth="3"/>
    {xy.map((point,i)=><circle key={i} cx={point[0]} cy={point[1]} r="3" fill="var(--hn-forest)"><title>{p[i].date} · {won(p[i].price_per_kg)}/kg</title></circle>)}
    <text x="50" y="231" className="svg-muted">{p[0].date}</text><text x="750" y="231" textAnchor="end" className="svg-muted">{p[p.length-1].date}</text>
  </svg>;
}

function App() {
  const [tab,setTab]=useState('dashboard');
  const [aiOpen,setAiOpen]=useState(false),[aiAsked,setAiAsked]=useState(false),[aiReady,setAiReady]=useState(false);
  const openAi=React.useCallback(()=>setAiOpen(true),[]),closeAi=React.useCallback(()=>setAiOpen(false),[]);
  const [s,setS]=useState<Scenario|null>(null);
  const [result,setResult]=useState<Comparison|null>(null);
  const [busy,setBusy]=useState(true);
  const [error,setError]=useState('');
  const [toast,setToast]=useState('');
  const [replay,setReplay]=useState(-1);
  const [kamisConfigured,setKamisConfigured]=useState(false);
  const [prices,setPrices]=useState<Prices|null>(null);
  const [priceBusy,setPriceBusy]=useState(false);
  const [priceError,setPriceError]=useState('');
  const [seriesIndex,setSeriesIndex]=useState(0);
  const [decision,setDecision]=useState<PriceDecision|null>(null);
  const priceRequestRef=useRef(0);
  const [query,setQuery]=useState({start:dateBefore(21),end:today(),region:'1101',kind:'03',rank:'04'});
  const requestRef=useRef(0);
  useEffect(()=>{api<Scenario>('/api/examples/scenario').then(setS).catch(e=>{setError(e.message);setBusy(false);});api<{kamis_configured:boolean;ai_configured?:boolean}>('/api/health').then(d=>{setKamisConfigured(d.kamis_configured);setAiReady(!!d.ai_configured);}).catch(()=>{});},[]);
  useEffect(()=>{
    if(!s)return;
    const controller=new AbortController(), request=++requestRef.current;
    setBusy(true);setError('');
    const timer=setTimeout(()=>{api<Comparison>('/api/strategies/compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(s),signal:controller.signal}).then(data=>{if(request===requestRef.current){setResult(data);setBusy(false);}}).catch(e=>{if(e.name!=='AbortError'&&request===requestRef.current){setError(e.message);setBusy(false);}});},180);
    return ()=>{clearTimeout(timer);controller.abort();};
  },[s]);
  useEffect(()=>{if(replay<0)return;const timer=setTimeout(()=>setReplay(replay>=3?-1:replay+1),1600);return()=>clearTimeout(timer);},[replay]);
  useEffect(()=>{if(!toast)return;const timer=setTimeout(()=>setToast(''),3500);return()=>clearTimeout(timer);},[toast]);
  const patch=(p:Partial<Scenario>)=>setS(prev=>prev?{...prev,...p}:prev);
  const marketPatch=(i:number,p:Partial<Market>)=>setS(prev=>prev?{...prev,markets:prev.markets.map((m,j)=>i===j?{...m,...p}:m)}:prev);
  const useStrategy=(r:Result)=>{if(busy||error)return;patch({allocation_pct:r.allocation_pct});setToast('선택한 배분으로 다시 계산합니다.');};
  const loadPrices=async()=>{const request=++priceRequestRef.current;const submittedQuery={...query};setPriceBusy(true);setPriceError('');setPrices(null);setSeriesIndex(0);try{const data=await api<Prices>(`/api/kamis/prices?${new URLSearchParams(submittedQuery)}`);if(request===priceRequestRef.current)setPrices(data);}catch(e){if(request===priceRequestRef.current)setPriceError(e instanceof Error?e.message:'조회에 실패했습니다.');}finally{if(request===priceRequestRef.current)setPriceBusy(false);}};
  const exportJson=()=>{if(!s||!result||busy||error)return;const output={exported_at:new Date().toISOString(),scenario:s,comparison:result,kamis:prices?.source==='kamis'?prices:null,decision_context:decision?{...decision,current_price_drop_pct:s.price_drop_pct,assumption_has_changed:s.price_drop_pct!==decision.assumption.price_drop_pct}:null,notice:'입력 조건에 따른 예상 수취액 비교. 기본 단가·요율·운임은 예시이며 실제 수익·모델 예측 검증 아님.'};saveFile('harvestnav-scenario.json',JSON.stringify(output,null,2));};
  const goodResult=result&&!busy&&!error;
  const kamisLabel=prices?.status==='live'?'실제 KAMIS 조회':prices?.status==='upstream_error'?'KAMIS 조회 실패':prices?.status==='empty'?'KAMIS 자료 없음':kamisConfigured?'KAMIS 조회 전':'KAMIS 미연결';
  const nav=[{id:'dashboard',label:'시뮬레이터 시트',icon:BarChart3},{id:'map',label:'지도·물량 흐름',icon:MapPin},{id:'simulation',label:'상세 출하 조건',icon:RouteIcon},{id:'prices',label:'KAMIS 가격 흐름',icon:BarChart3},{id:'evidence',label:'계산 근거',icon:ClipboardList}];
  return <div className={aiOpen?"app-shell ai-open":"app-shell"}>
    <div className="main-shell"><header className="horizontal-header"><a className="brand" href="#" onClick={e=>{e.preventDefault();setTab('dashboard');}}><span className="brand-icon"><Sprout size={23}/></span><span>출하 내비게이션</span></a><nav aria-label="주 메뉴">{nav.map(item=><button key={item.id} className={tab===item.id?'horizontal-tab active':'horizontal-tab'} aria-current={tab===item.id?'page':undefined} onClick={()=>setTab(item.id)}>{item.label}</button>)}<div className="ai-nav"><button onClick={openAi} aria-label="AI에게 질문" aria-expanded={aiOpen}><Sparkles size={17}/>AI에게 질문{!aiAsked&&<span className="ai-new">새 기능</span>}</button></div></nav><div className="header-status"><span className="badge amber">출하 시뮬레이션</span><button className="status-link" onClick={()=>setTab('prices')}><span className={prices?.status==='live'?'dot live':'dot'}/>{kamisLabel}</button><button className="header-info" aria-label="자료와 계산 안내" onClick={()=>setTab('evidence')}><CircleHelp size={19}/></button></div></header>
    <main>
      <section className="dashboard-title"><div><h1>{tab==='dashboard'?'관심 품목':tab==='map'?'지도·물량 흐름':tab==='simulation'?'출하 시뮬레이션':tab==='prices'?'KAMIS 가격 흐름':'계산 근거'}</h1><p>배추 출하 조건과 시장별 결과를 한곳에서 비교하세요.</p></div><button className="button ghost" onClick={()=>setTab('simulation')}><Settings2 size={16}/>출하 조건 설정</button></section>
      <div className="notice"><ShieldCheck size={18}/><p><b>KAMIS 가격 흐름을 참고해 출하 조건을 비교합니다.</b> 경매가격·요율·운임의 기본값은 예시입니다. 결과는 입력 조건에 따른 예상 수취액이며 실제 수익을 보장하지 않습니다.</p><button onClick={()=>setTab('evidence')}>계산 기준<ArrowRight size={14}/></button></div>

      {tab==='map'&&<div className="page-title"><h1>전국 지도에서 보는 출하 흐름</h1><p>실제 지형 위의 출하 물량 배분 시뮬레이션 · GPS 추적이 아닙니다.</p></div>}
      {decision&&s&&(tab==='dashboard'||tab==='simulation')&&<div className="notice price-decision"><ClipboardList size={18}/><p><b>KAMIS 자료 참고 기록</b> {decision.series.region} / {decision.series.variety} · {decision.series.analysis.latest_date} 관측 {number(decision.series.analysis.latest)}원/kg · {decision.series.prices.length}건. {decision.series.analysis.change_pct===null?'관측 변화율 비교 자료 부족':`관측 변화 ${decision.series.analysis.change_pct}% (${decision.series.analysis.reference_date} → ${decision.series.analysis.latest_date}, ${decision.series.analysis.reference_gap_days}일)`}. 현재 경매가격 하락 가정은 −{s.price_drop_pct}%입니다. <small>조회 시각 {decision.retrieved_at} · {decision.assumption.basis==='observed_change_scenario'?'과거 조사 하락률과 같은 경매 하락을 가정 · 향후 예측 아님':'조사값과 별도로 설정한 가정'} · 조건·결과 저장에 근거 포함</small></p><button onClick={()=>setDecision(null)}>기록 해제</button></div>}
      {!s&&<div className="panel initial-state" role={error?'alert':'status'}>{error?`출하 조건을 불러오지 못했습니다. ${error}`:'출하 조건을 불러오는 중입니다.'}</div>}
      {tab==='dashboard'&&s&&<WorkSheet scenario={s} result={result} busy={busy} error={error} prices={prices} patch={patch} apply={useStrategy} onNavigate={setTab} onReset={()=>api<Scenario>('/api/examples/scenario').then(setS).catch(e=>setError(e.message))} onExport={exportJson}/>}
      {tab==='map'&&s&&<ShipmentMap scenario={s} patch={patch}/>}
      {tab==='simulation'&&<>
        <div className="section-heading"><div><h1>나의 출하 시나리오</h1><span>조건을 조절하면 물량과 결과가 함께 바뀝니다.</span></div><button className="button ghost" onClick={()=>api<Scenario>('/api/examples/scenario').then(setS).catch(e=>setError(e.message))}><RefreshCw size={15}/>초기화</button></div>
        {s?<div className="sim-grid"><section className="panel input-panel"><div className="panel-heading"><span className="icon-square"><Settings2 size={18}/></span><h3>출하 조건</h3><span className="step-label">01</span></div>
          <div className="commodity"><span className="commodity-icon"><Sprout size={28}/></span><div><b>배추</b><small>원/kg · 기본값은 예시 · 실제 경매가격 아님</small></div><span className="badge muted">시범 품목</span></div>
          <label className="field"><span>출발지 <small>운임 자동 계산 없음</small></span><span className="input-wrap"><MapPin size={15}/><input value={s.origin} maxLength={60} onChange={e=>patch({origin:e.target.value})} /></span></label>
          <label className="field"><span>출하 예정일 <small>기록용</small></span><input type="date" value={s.planned_date||''} onChange={e=>patch({planned_date:e.target.value||null})}/></label>
          <div className="quantity-head"><span>총 출하 물량</span><strong>{number(s.quantity_kg)}<small> kg</small></strong></div><input className="range" type="range" aria-label="총 출하 물량" min="0" max="20000" step="100" value={s.quantity_kg} onChange={e=>patch({quantity_kg:Number(e.target.value)})}/><div className="range-labels"><span>0 kg</span><span>20,000 kg</span></div>
          <Field label="물량 직접 입력" value={s.quantity_kg} onChange={v=>patch({quantity_kg:v})} unit="kg" max={100000}/>
          <div className="allocation-head"><b>시장별 물량 배분</b><span>합계 100%</span></div><div className="allocation-values"><span><i/>{s.markets[0].name}<b>{s.allocation_pct[0]}%</b></span><span><i/>{s.markets[1].name}<b>{s.allocation_pct[1]}%</b></span></div><input className="range split" type="range" aria-label="첫 시장 배분 비율" min="0" max="100" step="5" value={s.allocation_pct[0]} onChange={e=>patch({allocation_pct:[Number(e.target.value),100-Number(e.target.value)]})}/>
          <div className="input-bottom"><Field label="상품화율" value={s.marketable_pct} onChange={v=>patch({marketable_pct:v})} unit="%" max={100} step={0.1}/><Field label="기타 비용" value={s.other_cost} onChange={v=>patch({other_cost:v})} unit="원"/></div>
        </section>
        <div className="visual-column"><section className="panel flow-panel"><div className="panel-heading"><span className="icon-square"><RouteIcon size={19}/></span><h3>물량 흐름</h3><span className="badge muted">물량 배분 시뮬레이션</span></div><div className="flow-subtitle"><b>{s.origin||'출발지 미입력'}</b><span>→ 후보 시장 2곳</span></div><LiveFlow scenario={s}/><div className="replay-bar"><span>{['데이터 확인','조건 설정','물량 배분','전략 비교'].map((text,i)=><span key={text} className={replay===i?'replay-step highlighted':replay>i?'replay-step completed':'replay-step'}><i>{replay>i?<Check size={12}/>:i+1}</i>{text}{i<3&&<ChevronRight size={11}/>}</span>)}</span><button onClick={()=>setReplay(replay<0?0:-1)} aria-label={replay<0?'시연 순서 재생':'시연 순서 중지'}>{replay<0?<Play size={14}/>:<X size={14}/>}</button></div><small className="replay-caption">시연 순서 안내 · 데이터 수집이나 모델 학습을 재현하지 않습니다.</small></section>
          <section className="panel markets-panel"><div className="panel-heading"><h3>시장별 가격·비용</h3><span className="badge amber">가정값 · 수정 가능</span></div><div className="market-inputs">{s.markets.map((m,i)=><div key={m.id} className="market-input"><h4><span className={`market-dot m${i}`}/>{m.name}</h4><Field label={`${m.name} 예상 경매가격`} value={m.price_per_kg} onChange={v=>marketPatch(i,{price_per_kg:v})} unit="원/kg"/><Field label={`${m.name} 차량 1대 비용`} value={m.vehicle_cost} onChange={v=>marketPatch(i,{vehicle_cost:v})} unit="원"/><details><summary>요율·차량·물량 제약 조정</summary><div className="details-fields"><Field label={`${m.name} 위탁수수료율`} value={m.commission_pct} onChange={v=>marketPatch(i,{commission_pct:v})} unit="%" max={100} step={0.1}/><Field label={`${m.name} 하역비율`} value={m.handling_pct} onChange={v=>marketPatch(i,{handling_pct:v})} unit="%" max={100} step={0.1}/><Field label={`${m.name} 시장사용료율`} value={m.market_fee_pct} onChange={v=>marketPatch(i,{market_fee_pct:v})} unit="%" max={100} step={0.1}/><Field label={`${m.name} 물량당 처리비`} value={m.handling_per_kg} onChange={v=>marketPatch(i,{handling_per_kg:v})} unit="원/kg"/><Field label={`${m.name} 변동 운송비`} value={m.transport_per_kg} onChange={v=>marketPatch(i,{transport_per_kg:v})} unit="원/kg"/><Field label={`${m.name} 차량 용량`} value={m.vehicle_capacity_kg} onChange={v=>marketPatch(i,{vehicle_capacity_kg:v})} unit="kg" min={1} max={100000}/><Field label={`${m.name} 최소 물량`} value={m.min_kg} onChange={v=>marketPatch(i,{min_kg:v})} unit="kg" max={100000}/><Field label={`${m.name} 수용량 상한`} value={m.max_kg} onChange={v=>marketPatch(i,{max_kg:v})} unit="kg" max={100000}/></div></details></div>)}</div></section>
        </div></div>:<div className="panel empty-state">{error||'시나리오를 불러오고 있습니다.'}</div>}

        <div className="section-heading result-heading"><div><h2>전략별로, 얼마나 달라질까요?</h2><span>같은 가격·비용 조건에서 배분 방식만 비교합니다.</span></div><button className="button ghost" disabled={!goodResult} onClick={exportJson}><Download size={15}/>조건·결과 저장</button></div>
        <div role="status" aria-live="polite" className="calculation-status">{busy?'조건을 적용해 계산하고 있습니다.':error?`계산 불가: ${error}`:result?`${result.search.valid_count}개 유효 전략 비교 완료 · ${result.search.step_pct}% 격자`:'결과 없음'}</div>
        {result&&!error&&<div className={busy?"result-content pending":"result-content"} aria-busy={busy}>{busy&&<p className="pending-label" role="status">이전 계산 결과 · 변경한 조건으로 재계산 중입니다.</p>}<ResultVerdict scenario={s!} result={result} valid={!!goodResult} apply={useStrategy} detail/>
          <div className="comparison-grid"><section className="panel comparison-panel"><div className="panel-heading"><h3>단일 출하와 분산 출하 비교</h3><BarChart3 size={18}/></div>{[result.current,...result.strategies.filter(r=>r.allocation_pct.some(p=>p===100))].map((r,i)=><div className={r.net===result.best.net?"strategy-row strategy-best":"strategy-row"} key={i}><div><span>{i===0?'현재 배분':r.label}{r.net===result.best.net&&<em className="max-badge">최대</em>}</span><b>{won(r.net)}</b></div><div className="bar-track"><span style={{width:`${Math.max(0,r.net)/Math.max(1,result.best.net)*100}%`}} className={i===0?'current-bar':r.net===result.best.net?'best-bar':''}/></div><small>운송비 {won(r.transport)}{i>0&&<button onClick={()=>useStrategy(r)}>적용<ArrowRight size={12}/></button>}</small></div>)}<p className="subtle">조건을 만족하지 않는 단일시장 전략은 표시하지 않습니다. 음수 수취액은 막대 대신 금액으로 확인하세요.</p></section>
          <section className="panel stress-panel"><div className="panel-heading"><h3>상황이 달라진다면</h3><span className="badge muted">가정된 스트레스</span></div><p>모든 시장의 가격 하락과 운송비 상승을 동시에 적용합니다.</p><div className="stress-fields"><Field label="경매가격 하락" value={s!.price_drop_pct} onChange={v=>patch({price_drop_pct:v})} unit="%" max={100} step={0.01}/><Field label="운송비 상승" value={s!.transport_increase_pct} onChange={v=>patch({transport_increase_pct:v})} unit="%" max={100}/></div><div className="stress-value"><span>현재 배분의 스트레스 수취액</span><strong>{won(result.current_stressed.net)}</strong><small><ArrowDownRight size={14}/>{won(result.current.net-result.current_stressed.net)} 감소</small></div><button className="text-button" onClick={()=>useStrategy(result.conservative)}>스트레스 수취액 최대 배분 적용<ArrowRight size={14}/></button><p className="subtle">발생 확률·예측구간·손실 위험의 통계적 추정이 아닙니다.</p></section></div>
        </div>}
      </>}

      {tab==='prices'&&<KamisView query={query} setQuery={setQuery} today={today()} configured={kamisConfigured} prices={prices} busy={priceBusy} error={priceError} load={loadPrices} seriesIndex={seriesIndex} setSeriesIndex={setSeriesIndex} renderChart={series=><PriceChart series={series}/>} onCompare={context=>{setDecision(context);patch({price_drop_pct:context.assumption.price_drop_pct});setTab('dashboard');setToast(`KAMIS 참고 자료를 기록하고 가격 −${context.assumption.price_drop_pct}% 가정을 비교합니다.`);}}/>}
      {tab==='evidence'&&<EvidenceView scenario={s} result={goodResult?result:null}/>}
      <footer><span><Sprout size={15}/>출하 내비게이션</span><span>가격을 예측하기 전에, 비교할 근거부터.</span><span>KAMIS 실제 가격정보 활용 · 출하 전략 시뮬레이션</span></footer>
    </main></div><AiAssistant open={aiOpen} onOpen={openAi} onClose={closeAi} onFirstQuestion={()=>setAiAsked(true)} onNavigate={setTab} scenario={s} result={goodResult?result:null} prices={prices} tab={tab} ready={aiReady} busy={busy||!!error}/>{toast&&<div className="toast" role="status"><Check size={17}/>{toast}</div>}
  </div>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
