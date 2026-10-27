import { useEffect, useRef, useState } from 'react';
import { Pause, Play, Minus, Plus, RotateCcw } from 'lucide-react';
import type { Scenario } from './types';
import geography from './data/korea-region.json';

const fmt=(n:number)=>new Intl.NumberFormat('ko-KR',{maximumFractionDigits:0}).format(n);
const colors=['#0764eb','#03a8a0'];

function useMotion(){
  const [paused,setPaused]=useState(false),[reduced,setReduced]=useState(false),[elapsed,setElapsed]=useState(0);
  const prev=useRef<number|null>(null);
  useEffect(()=>{const media=matchMedia('(prefers-reduced-motion: reduce)');const apply=()=>setReduced(media.matches);apply();media.addEventListener('change',apply);return()=>media.removeEventListener('change',apply);},[]);
  useEffect(()=>{let frame=0;prev.current=null;const tick=(now:number)=>{if(prev.current!==null)setElapsed(t=>t+Math.min(now-prev.current!,80));prev.current=now;frame=requestAnimationFrame(tick);};if(!paused&&!reduced)frame=requestAnimationFrame(tick);return()=>cancelAnimationFrame(frame);},[paused,reduced]);
  return {elapsed,paused:paused||reduced,toggle:()=>setPaused(p=>!p),reduced};
}

function Vehicle({x,y,color}:{x:number;y:number;color:string}){return <g className="moving-vehicle" transform={`translate(${x.toFixed(2)} ${y.toFixed(2)})`} aria-hidden="true"><rect x="-14" y="-10" width="30" height="22" rx="6" fill="white" stroke={color}/><path d="M-9 -5H3V5H-9ZM3 -1H8L12 3V5H3Z" fill={color}/><circle cx="-5" cy="7" r="2.6" fill="#183349"/><circle cx="8" cy="7" r="2.6" fill="#183349"/></g>}

export function LiveFlow({scenario:s}:{scenario:Scenario}){
 const m=useMotion();
 return <div className="live-flow"><div className="motion-toolbar"><span className="motion-status"><i className={m.paused?'':'playing'}/>{m.reduced?'모션 축소 설정 적용':m.paused?'일시정지':'출하 흐름 재생 중'} · 시뮬레이션</span><button onClick={m.toggle} disabled={m.reduced} aria-label={m.paused?'물량 애니메이션 재생':'물량 애니메이션 일시정지'}>{m.paused?<Play size={14}/>:<Pause size={14}/>}</button></div>
 <svg viewBox="0 0 640 270" role="img" aria-label={`가상 출하 흐름: ${s.markets.map((v,i)=>`${v.name} ${fmt(s.quantity_kg*s.allocation_pct[i]/100)}kg`).join(', ')}`}>
 <defs><pattern id="flow-grid" width="18" height="18" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#d9e4ed"/></pattern></defs><rect width="640" height="270" fill="url(#flow-grid)"/>
 {s.markets.map((v,i)=>{const y=i?198:70,p=s.allocation_pct[i],active=p>0&&s.quantity_kg>0;return <g key={v.id}><path d={`M154 134 C280 134 280 ${y} 438 ${y}`} fill="none" stroke={active?colors[i]:'#dce4eb'} strokeWidth={active?3+p/8:2} opacity=".45"/>{active&&Array.from({length:Math.max(1,Math.ceil(p/25))},(_,k)=>{const t=(m.elapsed/6500+k/Math.ceil(p/25))%1,u=1-t;return <Vehicle key={k} x={u*u*u*154+3*u*u*t*280+3*u*t*t*280+t*t*t*438} y={u*u*u*134+3*u*u*t*134+3*u*t*t*y+t*t*t*y} color={colors[i]}/>;})}<rect x="438" y={y-30} width="175" height="65" rx="12" fill="white" stroke="#dce4eb"/><text x="451" y={y-6} className="flow-name">{v.name}</text><text x="451" y={y+17} className="flow-weight">{fmt(s.quantity_kg*p/100)} kg</text><text x="598" y={y+17} textAnchor="end" className="map-caption">{p}%</text></g>;})}
 <rect x="20" y="100" width="135" height="70" rx="12" fill="white" stroke="#dce4eb"/><text x="86" y="127" textAnchor="middle" className="flow-name">가상 산지</text><text x="86" y="151" textAnchor="middle" className="flow-weight">{fmt(s.quantity_kg)} kg</text><text x="320" y="257" textAnchor="middle" className="map-caption">차량 이동은 반복 시뮬레이션 · 선 굵기와 표시 수는 배분 비율에 연동</text>
 </svg></div>;
}

type Polygon={type:string;coordinates:number[][][]|number[][][][]};
const polygons=geography.features as unknown as {properties:{name:string};geometry:Polygon}[];

export function ShipmentMap({scenario:s}:{scenario:Scenario}){
 const m=useMotion(),[zoom,setZoom]=useState(1),[national,setNational]=useState(false),[selected,setSelected]=useState('origin');
 const [origin,setOrigin]=useState({lon:128.39,lat:37.37});
 const points=[{id:'origin',name:'출발점 · 평창권 예시',...origin},
 {id:s.markets[0].id,name:`${s.markets[0].name}권 예시`,lon:127.11,lat:37.49},
 {id:s.markets[1].id,name:`${s.markets[1].name}권 예시`,lon:127.14,lat:37.60}];
 const bounds=national?[124.5,32.8,130.7,39.3]:[126.3,36.85,129.1,38.12];
 const cos=Math.cos(37*Math.PI/180),scale=Math.min(690/((bounds[2]-bounds[0])*cos),330/(bounds[3]-bounds[1]));
 const project=(lon:number,lat:number):[number,number]=>[380+(lon-(bounds[0]+bounds[2])/2)*cos*scale,200-(lat-(bounds[1]+bounds[3])/2)*scale];
 const polygonPath=(g:Polygon)=>{const coords=g.type==='Polygon'?[g.coordinates]:g.coordinates;return (coords as number[][][][]).map(poly=>poly.map(ring=>ring.map(([lon,lat],i)=>`${i?'L':'M'}${project(lon,lat).map(x=>x.toFixed(2)).join(',')}`).join(' ')+'Z').join(' ')).join(' ');};
 const chosen=points.find(p=>p.id===selected)||points[0];
 return <section className="shipment-map"><div className="map-top"><div><h3>지도에서 보는 출하 흐름</h3><p>실제 지형 데이터 위의 가상 배분 · GPS 추적 아님</p></div><button className="button ghost" onClick={()=>{setNational(p=>!p);setZoom(1);}}>{national?'출하 권역 보기':'전국 보기'}</button></div>
 <div className="map-stage"><svg viewBox="0 0 760 410" role="img" aria-label="Natural Earth 지형과 WGS84 예시 좌표 기반 출하 시뮬레이션 지도"><defs><clipPath id="map-clip"><rect width="760" height="410" rx="12"/></clipPath><pattern id="map-lines" width="38" height="38" patternUnits="userSpaceOnUse"><path d="M38 0H0V38" stroke="#d3e6f1" fill="none" strokeWidth=".5"/></pattern></defs><g clipPath="url(#map-clip)"><rect width="760" height="410" fill="#eef7fb"/><rect width="760" height="410" fill="url(#map-lines)"/><g transform={`translate(${380*(1-zoom)} ${205*(1-zoom)}) scale(${zoom})`}>
 {polygons.map((feature,i)=><path key={i} d={polygonPath(feature.geometry)} fill={feature.properties.name==='South Korea'?'#f9fbf5':'#e8eee4'} stroke="#c2cdbd" strokeWidth={.9/zoom}/>)}
 {points.slice(1).map((p,i)=>{const [x0,y0]=project(origin.lon,origin.lat),[x,y]=project(p.lon,p.lat),pct=s.allocation_pct[i],active=pct>0&&s.quantity_kg>0;return <g key={p.id}><path d={`M${x0},${y0}L${x},${y}`} fill="none" stroke={colors[i]} strokeWidth={(active?2+pct/20:1)/zoom} opacity={active?.7:.2}/>{active&&Array.from({length:Math.max(1,Math.ceil(pct/25))},(_,k)=>{const t=(m.elapsed/8000+k/Math.ceil(pct/25))%1;return <g key={k} transform={`translate(${x0+(x-x0)*t} ${y0+(y-y0)*t}) scale(${1/zoom})`}><Vehicle x={0} y={0} color={colors[i]}/></g>;})}</g>;})}
 {points.map((p,i)=>{const [x,y]=project(p.lon,p.lat);return <g key={p.id} transform={`translate(${x} ${y}) scale(${1/zoom})`}><circle r="13" fill={i?colors[i-1]:'#314455'} opacity=".12"/><circle r="6" fill={i?colors[i-1]:'#314455'} stroke="white" strokeWidth="2"/><g transform={`translate(${i===1?-148:14} ${i===2?-44:6})`}><rect x="-5" y="-20" width={i?133:145} height="38" rx="6" fill="white" stroke="#dbe3e9"/><text className="map-location" y="-5">{i?s.markets[i-1].name:'예시 출발점'}</text><text className="map-caption" y="11">{i?`${fmt(s.quantity_kg*s.allocation_pct[i-1]/100)} kg · ${s.allocation_pct[i-1]}%`:`${origin.lon.toFixed(2)}°E, ${origin.lat.toFixed(2)}°N`}</text></g></g>;})}
 </g></g><text x="18" y="393" className="map-caption">Natural Earth 1:50m · WGS84 · 지점 간 직선 연결 (도로 경로 아님)</text></svg>
 <div className="map-controls"><button aria-label="지도 확대" onClick={()=>setZoom(z=>Math.min(2,z+.25))}><Plus size={17}/></button><button aria-label="지도 축소" onClick={()=>setZoom(z=>Math.max(1,z-.25))}><Minus size={17}/></button><button aria-label="지도 초기화" onClick={()=>{setZoom(1);setNational(false);}}><RotateCcw size={15}/></button><button aria-label={m.paused?'지도 이동 재생':'지도 이동 일시정지'} onClick={m.toggle} disabled={m.reduced}>{m.paused?<Play size={15}/>:<Pause size={15}/>}</button></div></div>
 <div className="map-legend"><span><i style={{background:colors[0]}}/>{s.markets[0].name}</span><span><i style={{background:colors[1]}}/>{s.markets[1].name}</span><span>{m.paused?'정지':'이동 시뮬레이션 재생 중'}</span></div>
 <div className="map-point-row"><label>좌표 확인<select value={selected} onChange={e=>setSelected(e.target.value)}>{points.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label><span>{chosen.lon.toFixed(4)}°E / {chosen.lat.toFixed(4)}°N</span><details><summary>출발점 좌표 조정</summary><label>경도<input type="number" min="124.5" max="130" step=".01" value={origin.lon} onChange={e=>{const v=e.currentTarget.valueAsNumber;if(Number.isFinite(v)&&v>=124.5&&v<=130)setOrigin(o=>({...o,lon:v}));}}/></label><label>위도<input type="number" min="33" max="39" step=".01" value={origin.lat} onChange={e=>{const v=e.currentTarget.valueAsNumber;if(Number.isFinite(v)&&v>=33&&v<=39)setOrigin(o=>({...o,lat:v}));}}/></label></details></div>
 <p className="subtle">좌표는 지역을 참고해 배치한 예시이며 실제 농가·시설 위치가 아닙니다. 출발지 문구를 바꿔도 자동 지오코딩하지 않으며 지도 좌표는 별도로 조절합니다. 운임·거리 자동 산정과 실제 배송 추적은 포함하지 않습니다.</p>
 </section>;
}
