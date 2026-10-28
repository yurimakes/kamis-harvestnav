import { useEffect, useRef, useState } from 'react';
import { ArrowUp, FileText, Link2, Sparkles, X } from 'lucide-react';
import type { Comparison, Prices, Scenario } from './types';

const tabs:Record<string,string>={simulator:'dashboard',map:'map',detail:'simulation',kamis:'prices',basis:'evidence'};
const names:Record<string,string>={dashboard:'시뮬레이터 시트',map:'지도·물량 흐름',simulation:'상세 출하 조건',prices:'KAMIS 가격 흐름',evidence:'계산 근거'};
type Source={tab:string;label:string};
type Message={role:'user'|'assistant';content:string;sources?:Source[];context?:string};
type Props={open:boolean;onClose:()=>void;onOpen:()=>void;onFirstQuestion:()=>void;onNavigate:(tab:string)=>void;scenario:Scenario|null;result:Comparison|null;prices:Prices|null;tab:string;ready:boolean;busy:boolean};
export function buildSheetContext(s:Scenario,r:Comparison|null,p:Prices|null,tab:string){
  return {active_tab:Object.keys(tabs).find(k=>tabs[k]===tab)||'simulator',is_sample_scenario:s.source==='synthetic',kamis_status:p?.status||'not_loaded',item:s.commodity,total_kg:s.quantity_kg,yield_rate:s.marketable_pct/100,
    markets:s.markets.map((m,i)=>({name:m.name,share:s.allocation_pct[i]/100,price_per_kg:m.price_per_kg,truck_cost:m.vehicle_cost,capacity_kg:m.vehicle_capacity_kg,commission_pct:m.commission_pct,handling_pct:m.handling_pct,market_fee_pct:m.market_fee_pct,freight_per_kg:m.transport_per_kg,net:r?.current.routes[i]?.net??null})),
    stress:{price_drop:s.price_drop_pct/100,freight_rise:s.transport_increase_pct/100},
    results:r?{current_net:r.current.net,best:{label:r.best.label,net:r.best.net,freight:r.best.transport},diff_vs_current:r.best.delta_vs_current,current_stress_net:r.current_stressed.net,best_stress:{label:r.conservative.label,net:r.conservative.stressed_net},candidates_count:r.search.valid_count}:null,
    kamis:p?.status==='live'?{as_of:p.as_of,query:p.query,series:p.series.map(x=>({region:x.region,variety:x.variety,analysis:x.analysis}))}:null};
}
function readMessages():Message[]{
  try{const v=JSON.parse(sessionStorage.getItem('hn_ai_messages')||'[]');if(!Array.isArray(v))return [];return v.filter(x=>x&&['user','assistant'].includes(x.role)&&typeof x.content==='string'&&x.content.length<=4000).slice(-12).map(x=>({role:x.role,content:x.content,context:typeof x.context==='string'?x.context.slice(0,180):undefined,sources:Array.isArray(x.sources)?x.sources.filter((v:Source)=>v&&v.tab in tabs&&typeof v.label==='string').map((v:Source)=>({tab:v.tab,label:v.label.slice(0,80)})).slice(0,5):[]}));}catch{return [];}
}
export function AiAssistant({open,onClose,onOpen,onFirstQuestion,onNavigate,scenario:s,result,prices,tab,ready,busy}:Props){
  const [dismissed,setDismissed]=useState(()=>{try{return localStorage.getItem('hn_ai_bubble_dismissed')==='1';}catch{return false;}});
  const [messages,setMessages]=useState<Message[]>(readMessages),[draft,setDraft]=useState(''),[loading,setLoading]=useState(false),[error,setError]=useState('');
  const [retry,setRetry]=useState<{question:string;context:object;label:string;history:Message[]}|null>(null);
  const input=useRef<HTMLTextAreaElement>(null),scroll=useRef<HTMLDivElement>(null),opener=useRef<HTMLElement|null>(null),request=useRef<AbortController|null>(null),inflight=useRef(false);
  const label=`${names[tab]||'시뮬레이터 시트'} · 배추 ${s?new Intl.NumberFormat('ko-KR').format(s.quantity_kg):'—'}kg · ${s?.markets[0].name??'첫 시장'} ${s?.allocation_pct[0]??'—'}%`;
  function dismiss(){setDismissed(true);try{localStorage.setItem('hn_ai_bubble_dismissed','1');}catch{/* storage can be unavailable */}}
  useEffect(()=>{try{sessionStorage.setItem('hn_ai_messages',JSON.stringify(messages.slice(-12)));}catch{/* conversation still works in memory */}},[messages]);
  useEffect(()=>{if(!open)return;opener.current=document.activeElement as HTMLElement;dismiss();const frame=requestAnimationFrame(()=>input.current?.focus());const esc=(e:KeyboardEvent)=>{if(e.key==='Escape'){e.preventDefault();onClose();}};document.addEventListener('keydown',esc);return()=>{cancelAnimationFrame(frame);document.removeEventListener('keydown',esc);if(opener.current?.isConnected)opener.current.focus();};},[open,onClose]);
  useEffect(()=>{if(scroll.current)scroll.current.scrollTop=scroll.current.scrollHeight;},[messages,loading,error,open]);
  useEffect(()=>()=>request.current?.abort(),[]);
  async function send(again=false){
    if(inflight.current||!ready||!s||busy||!result)return;
    const question=(again?retry?.question:draft)?.trim();if(!question||question.length>500)return;
    const ctx=again&&retry?retry.context:buildSheetContext(s,result,prices,tab), captured=again&&retry?retry.label:label, history=again&&retry?retry.history:messages.slice(-12);
    const payload=JSON.stringify({question,history:history.map(({role,content})=>({role,content})),sheet_context:ctx});
    if(new TextEncoder().encode(payload).length>32768){setError('대화가 길어졌습니다. 대화 지우기 후 다시 질문해 주세요.');return;}
    if(!again){setMessages(old=>[...old,{role:'user',content:question,context:captured}]);setDraft('');}
    onFirstQuestion();setError('');setLoading(true);inflight.current=true;setRetry({question,context:ctx,label:captured,history});
    const controller=new AbortController();request.current=controller;const timeout=setTimeout(()=>controller.abort(),32000);
    try{const response=await fetch('/api/ai/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:payload,signal:controller.signal});
      if(!response.ok)throw new Error(response.status===429?'질문이 많아 잠시 쉬고 다시 보내 주세요.':response.status===503?'AI 연결 전입니다. 서버의 AI 설정을 확인해 주세요.':'답변을 가져오지 못했어요. 다시 보내 주세요.');
      const data=await response.json();if(typeof data.answer!=='string'||!Array.isArray(data.sources))throw new Error('답변 형식을 확인하지 못했어요.');
      setMessages(old=>[...old,{role:'assistant',content:data.answer,context:captured,sources:data.sources.filter((v:Source)=>v&&v.tab in tabs&&typeof v.label==='string')}]);setRetry(null);
    }catch(e){setError(e instanceof Error&&e.name!=='AbortError'?e.message:'응답 시간이 초과됐어요. 다시 보내 주세요.');}
    finally{clearTimeout(timeout);inflight.current=false;setLoading(false);}
  }
  return <>{!open&&<div className="ai-launcher">{!dismissed&&<div className="ai-bubble" role="status"><button className="ai-bubble-close" aria-label="AI 안내 말풍선 닫기" onClick={dismiss}><X size={14}/></button><button className="ai-bubble-open" onClick={onOpen}><strong>궁금한 건 AI에게 바로 물어보세요</strong><p>지금 보고 있는 계산 결과를 읽고 쉽게 설명해 드려요.</p></button></div>}<button className="ai-fab" aria-label="AI에게 묻기 패널 열기" onClick={onOpen}><span><Sparkles size={22}/></span>AI에게 묻기</button></div>}
    {open&&<aside className="ai-panel" aria-label="HarvestNav AI"><header className="ai-panel-header"><span className="ai-panel-icon"><Sparkles size={20}/></span><div><b>HarvestNav AI</b><small>지금 보는 시트를 바탕으로 답해요</small></div><button aria-label="AI 패널 닫기" onClick={onClose}><X size={19}/></button></header><div className="ai-context"><FileText size={15}/><span>읽는 중: {label}</span></div>
      <div className="ai-conversation" aria-live="polite" aria-busy={loading} ref={scroll}>{!messages.length&&<div className="ai-empty"><Sparkles size={26}/><p>계산 결과가 궁금한가요?<br/>가격·운송비·배분의 근거를 질문해 보세요.</p></div>}{messages.map((m,i)=><div key={i} className={`ai-message ${m.role}`}><p>{m.content}</p>{m.role==='assistant'&&<><small>질문 시점: {m.context}</small><div className="ai-sources">{m.sources?.map((v,j)=><button key={j} onClick={()=>onNavigate(tabs[v.tab])}><Link2 size={12}/>{v.label}</button>)}</div></>}</div>)}{loading&&<div className="ai-loading" role="status" aria-label="AI 답변을 기다리는 중"><i/><i/><i/></div>}{error&&<div className="ai-error" role="alert"><p>{error}</p>{retry&&<button onClick={()=>void send(true)} disabled={loading}>다시 보내기</button>}</div>}</div>
      <div className="ai-composer">{!ready&&<div className="ai-connection" role="status">AI 연결 전입니다. 현재 계산과 KAMIS 조회는 사용할 수 있습니다. 질문 답변은 서버 AI 설정 후 제공됩니다.</div>}<div className="ai-suggestions"><span>이런 걸 물어볼 수 있어요</span>{['스트레스 조건에서 수취액이 가장 큰 배분은?','운송비가 30% 오르면 결과가 어떻게 바뀌어요?','KAMIS 가격은 언제 반영돼요?'].map(q=><button key={q} onClick={()=>{setDraft(q);input.current?.focus();}}>{q}</button>)}</div><div className="ai-input"><textarea aria-label="AI 질문" ref={input} rows={2} maxLength={500} placeholder="시트에 대해 무엇이든 물어보세요" value={draft} onChange={e=>setDraft(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();void send();}}}/><button aria-label="AI 질문 보내기" disabled={!ready||loading||busy||!result||!draft.trim()} onClick={()=>void send()}><ArrowUp size={19}/></button></div><small>AI 답변은 입력한 가정값으로 계산한 설명이며 실제 수익을 보장하지 않아요. 질문과 화면 요약을 AI 서비스에 전송합니다.</small>{messages.length>0&&<button className="text-button" disabled={loading} onClick={()=>{setMessages([]);setError('');setRetry(null);}}>대화 지우기</button>}</div>
    </aside>}
  </>;
}
