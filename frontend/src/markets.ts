import type { Market } from './types';
// Regional illustration coordinates, not surveyed facilities or road routing points.
export const marketLocations = [
 {id:'garak',name:'서울 가락',lon:127.11,lat:37.49,dx:-166,dy:30,price:1500,truck:180000,freight:10},
 {id:'guri',name:'구리',lon:127.14,lat:37.60,dx:-166,dy:-15,price:1600,truck:260000,freight:12},
 {id:'chuncheon',name:'춘천',lon:127.73,lat:37.88,dx:18,dy:-52,price:1480,truck:200000,freight:11},
 {id:'daejeon',name:'대전 오정',lon:127.41,lat:36.35,dx:-166,dy:-13,price:1540,truck:280000,freight:14},
 {id:'jeonju',name:'전주',lon:127.15,lat:35.85,dx:-166,dy:4,price:1520,truck:300000,freight:15},
 {id:'gwangju',name:'광주 각화',lon:126.93,lat:35.18,dx:-166,dy:24,price:1580,truck:340000,freight:17},
 {id:'daegu',name:'대구 북부',lon:128.55,lat:35.90,dx:18,dy:-24,price:1560,truck:310000,freight:16},
 {id:'busan',name:'부산 엄궁',lon:128.98,lat:35.13,dx:18,dy:22,price:1620,truck:380000,freight:19},
];
export function exampleMarket(id:string):Market{
 const v=marketLocations.find(x=>x.id===id);if(!v)throw new Error('알 수 없는 시장');
 return {id:v.id,name:v.name,price_per_kg:v.price,vehicle_cost:v.truck,transport_per_kg:v.freight,vehicle_capacity_kg:5000,commission_pct:6,handling_pct:1,market_fee_pct:.5,handling_per_kg:0,min_kg:0,max_kg:100000};
}
