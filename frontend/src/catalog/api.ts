export type Evidence={value:string;term:string;quote:string};
export type Item={source_id:string;sku:string;name:string;price:string;currency:string;supplier_text:string};
export type Result={source_id:string;status:string;issues:string[];extraction:{color?:Evidence|null;material?:Evidence|null};attempts:{issues:string[]}[]};
export type Job={payment?:null|{state:string;approval_url:string|null;order_id:string|null;capture_id:string|null;refund_id:string|null};id:string;status:string;snapshot:{contract:string;provider:string;payment_mode:string;quoted_cents:number;product_currency:string;rows:Item[];excluded:{line:number;source_id:string;issues:string[]}[]};results:Result[];settlement:null|{accepted_count:number;undelivered_count:number;refund_eligible_cents:number;retained_cents:number;payment_executed:boolean}};
export type Session={id:string;token:string};
const base=(import.meta.env.VITE_API_BASE_URL||'').replace(/\/$/,'');
export const money=(cents:number)=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(cents/100);
export async function request(path:string,session?:Session,body?:unknown,signal?:AbortSignal,operator?:string):Promise<Job&{access_token?:string}>{
 const response=await fetch(base+'/api/catalog/jobs'+path,{method:body===undefined?'GET':'POST',signal,headers:{'Content-Type':'application/json',...(session?{Authorization:'Bearer '+session.token}:{}),...(operator?{'X-Operator-Token':operator}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
 const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Check the source file and try again.');return data;
}
export async function download(session:Session,format:'csv'|'json'){
 const response=await fetch(base+'/api/catalog/jobs/'+session.id+(format==='csv'?'/products.csv':'/report.json'),{headers:{Authorization:'Bearer '+session.token}});
 if(!response.ok)throw new Error('Download is not ready. Refresh and try again.');
 const url=URL.createObjectURL(await response.blob());const a=document.createElement('a');a.href=url;a.download=format==='csv'?'products.csv':'catalog-report.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
