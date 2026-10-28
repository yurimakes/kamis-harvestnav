/** Example network visualization only. Does not calculate eight-market profits. */
export const networkPresets=[
 {name:'전국 분산',shares:[20,15,5,15,10,10,10,15]},
 {name:'영남 중심',shares:[10,5,5,10,5,5,25,35]},
 {name:'호남 중심',shares:[10,5,5,10,30,25,5,10]},
];
export function allocateNetwork(total:number,shares:number[]){
 if(!Number.isInteger(total)||total<0||total>100000||shares.length!==8||shares.some(v=>!Number.isFinite(v)||v<0)||shares.reduce((a,b)=>a+b,0)!==100)throw new Error('시연 물량과 비율 확인 필요');
 const raw=shares.map(p=>total*p/100),kg=raw.map(Math.floor);
 const order=raw.map((v,i)=>({i,f:v-kg[i]})).sort((a,b)=>b.f-a.f||a.i-b.i);
 const missing=total-kg.reduce((a,b)=>a+b,0);
 for(let i=0;i<missing;i++)kg[order[i].i]++;

 return kg;
}
