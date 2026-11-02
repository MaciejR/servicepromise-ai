import React, { useEffect, useState } from 'react';
import { ArrowRight, Check, CheckCircle2, ChevronRight, CircleDollarSign, Clock3, ExternalLink, FileText, LoaderCircle, RotateCcw, ShieldCheck, Sparkles, TriangleAlert } from './icons';
import './style.css';

type Evaluation = { score:number; evaluator:string; word_count:number; sections:Record<string,boolean>; format_pass:boolean; quality_pass:boolean; refund_percent:number; refund_cents:number; verdict:{explanation:string} };
type Order = {id:string; status:string; mode:string; brief:string; price_cents:number; approval_url:string|null; delivery:string|null; evaluation:Evaluation|null; refund_cents:number; refund_id:string|null; capture_id:string|null; events:{at:string;kind:string;message:string}[]};
type Config = {payment_mode:string; ai_mode:string; auto_refund:boolean};
const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const money = (cents:number) => new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(cents/100);
const sample = 'Create a marketing brief for a small independent coffee roaster launching a monthly subscription. Reach remote workers who value fresh, ethically sourced coffee. The goal is to get the first 20 subscribers.';

function App(){
  const [config,setConfig]=useState<Config|null>(null);
  const [brief,setBrief]=useState(sample);
  const [order,setOrder]=useState<Order|null>(null);
  const [token,setToken]=useState('');
  const [operator,setOperator]=useState('');
  const [scenario,setScenario]=useState('success');
  const [busy,setBusy]=useState('');
  const [error,setError]=useState('');
  const [tab,setTab]=useState('delivery');
  const [showOperator,setShowOperator]=useState(false);

  async function request(path:string, method='GET', body?:unknown, access=token){
    const response=await fetch(apiBase+path,{method,headers:{'Content-Type':'application/json',...(access?{Authorization:`Bearer ${access}`} : {}),...(operator?{'X-Operator-Token':operator}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
    const data=await response.json();
    if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:'Check the request and try again.');
    return data;
  }
  useEffect(()=>{
    (async()=>{try{
      setConfig(await request('/api/config'));
      const saved=sessionStorage.getItem('servicepromise-order');
      if(saved){const session=JSON.parse(saved);setToken(session.token);setOrder(await request(`/api/orders/${session.id}`,'GET',undefined,session.token));}
    }catch(e){setError(e instanceof Error?e.message:'Could not connect to the API. Start the backend and reload.');}})();
  },[]);
  async function action(name:string, fn:()=>Promise<void>){setBusy(name);setError('');try{await fn();}catch(e){setError(e instanceof Error?e.message:'Something went wrong.');}finally{setBusy('');}}
  async function create(){await action('Creating your promise',async()=>{
    const result=await request('/api/orders','POST',{brief});
    setToken(result.access_token);setOrder(result);
    sessionStorage.setItem('servicepromise-order',JSON.stringify({id:result.id,token:result.access_token}));
  });}
  async function update(endpoint:string, body?:unknown){if(!order)return;await action(endpoint==='deliver'?'Delivering & evaluating':'Updating payment',async()=>{setOrder(await request(`/api/orders/${order.id}/${endpoint}`,'POST',body));});}
  function reset(){sessionStorage.removeItem('servicepromise-order');setOrder(null);setToken('');setError('');setTab('delivery');}
  const isDemo=config?.payment_mode==='demo';
  const paid=!!order&&['paid','evaluated','refunded','refund_pending'].includes(order.status);
  const evaluated=!!order?.evaluation;
  const steps=[{name:'Define the promise',done:!!order,icon:ShieldCheck},{name:'Pay securely',done:paid,icon:CircleDollarSign},{name:'Verify the work',done:evaluated,icon:Sparkles},{name:'Settle fairly',done:evaluated&&(!order!.refund_cents||['refunded','refund_pending'].includes(order!.status)),icon:CheckCircle2}];

  return <div className="app">
    <header><a className="brand" href="/" aria-label="ServicePromise AI home"><span className="brand-icon"><ShieldCheck size={23}/></span>servicepromise<span className="ai">AI</span></a><div className="header-right"><span className="environment"><i/>{config?(isDemo?'Interactive demo':'PayPal Sandbox'):'Connecting'}</span><button className="text-button" onClick={()=>setShowOperator(!showOperator)}>Operator settings</button></div></header>
    <main>
      <div className="hero"><div><div className="eyebrow"><span/> TRUST, BUILT INTO THE TRANSACTION</div><h1>A promise you<br/>can <em>measure.</em></h1><p>Buy an AI service. See how it performs.<br/>If the work falls short, the policy makes it right.</p><div className="hero-tags"><span><ShieldCheck size={15}/> Quality-backed</span><span><CircleDollarSign size={15}/> Powered by PayPal</span></div></div><div className="hero-note"><span className="note-number">01 — 04</span><div className="mini-flow"><span><FileText size={20}/></span><i/><span><Sparkles size={20}/></span><i/><span><Check size={20}/></span></div><h3>Good work gets paid.<br/>Broken promises get refunded.</h3><p>Clear expectations. Verifiable evidence.<br/>A fair outcome for both sides.</p></div></div>
      <div className="mode-notice"><TriangleAlert size={16}/><span>{isDemo?'Demo mode: payments, content and AI scores are simulated. No real money moves.':config?'Sandbox mode: test payments only. Azure OpenAI generates and evaluates the service.':'Connecting to the service…'}</span></div>
      {showOperator&&<div className="operator"><label htmlFor="operator">Operator token <small>Required for sandbox delivery and refunds. Kept in memory only.</small></label><input id="operator" type="password" autoComplete="off" value={operator} onChange={e=>setOperator(e.target.value)} placeholder="Enter backend OPERATOR_TOKEN"/></div>}
      <nav className="steps" aria-label="Order progress">{steps.map((step,index)=><div key={step.name} className={`step ${step.done?'complete':''}`}><span className="step-number">{step.done?<Check size={15}/>:String(index+1).padStart(2,'0')}</span><span>{step.name}</span>{index<3&&<ChevronRight size={15} className="step-arrow"/>}</div>)}</nav>
      {error&&<div role="alert" className="error"><TriangleAlert size={18}/><span>{error}</span><button onClick={()=>setError('')} aria-label="Dismiss error">×</button></div>}
      <div className="workspace"><section className="card order-card"><div className="card-top"><span className="eyebrow">THE SERVICE</span><span className="pill">CONTENT & STRATEGY</span></div><h2>Your next campaign,<br/>with a quality promise.</h2><p className="muted">A focused marketing brief for your business, with an independent quality check built in.</p><label htmlFor="brief">What are we working on?</label><textarea id="brief" value={order?.brief??brief} disabled={!!order||!!busy} onChange={e=>setBrief(e.target.value)} maxLength={3000} rows={6}/><div className="input-caption"><span>Be specific about the audience and outcome.</span><span>{(order?.brief??brief).length}/3000</span></div>
        <div className="guarantee"><div className="guarantee-heading"><ShieldCheck size={19}/><strong>The promise, before you pay</strong></div><ul><li><Check size={14}/>120–220 words, structured into 3 sections</li><li><Check size={14}/>Audience · Value · Action</li><li><Check size={14}/>Quality score of at least 70/100</li></ul><div className="refund-policy"><span>Format breach <b>25% back</b></span><span>Quality breach <b>25% back</b></span><small>Refunds add up to a maximum of 50%. Policy v1.</small></div></div>
        <div className="price"><div><span>One brief. One clear promise.</span><small>No subscription. No surprises.</small></div><strong>$12<span>.00</span></strong></div>
        {!order?<button className="primary" disabled={!!busy||!config||brief.trim().length<20} onClick={create}>Create my promise<ArrowRight size={18}/></button>:order.status==='created'?<button className="primary" disabled={!!busy} onClick={()=>update('checkout')}>{isDemo?'Simulate payment':'Continue to PayPal Sandbox'}<ArrowRight size={18}/></button>:order.status==='awaiting_approval'?<div className="checkout-actions"><a className="primary paypal" href={order.approval_url??'#'}>Approve in PayPal Sandbox<ExternalLink size={17}/></a><button className="secondary" disabled={!!busy} onClick={()=>update('capture')}>I approved — capture payment</button></div>:<div className="paid-line"><CheckCircle2 size={18}/>{isDemo?'Demo payment captured':'Sandbox payment captured'}<strong>{money(order.price_cents)}</strong></div>}
        {order&&<button className="reset text-button" disabled={!!busy} onClick={reset}><RotateCcw size={13}/> Start a new order</button>}
      </section>
      <section className="results"><div className="card result-card"><div className="card-top"><span className="eyebrow">THE EVIDENCE</span><span className={`pill ${evaluated?(order!.refund_cents?'amber':'green'):''}`}>{evaluated?(order!.refund_cents?'PROMISE BREACHED':'PROMISE KEPT'):'AWAITING DELIVERY'}</span></div>
        <div className="result-heading"><h2>Trust the evidence.</h2><p className="muted">Every promise has a paper trail.</p></div>
        {!evaluated?<><div className="empty-state"><div className="orb"><Sparkles size={30}/></div><h3>{paid?'Ready to put the promise to work.':'Your quality report starts here.'}</h3><p>{paid?'Deliver the service and evaluate it against the exact policy you accepted.':'Create a promise and complete checkout to see the delivery, quality checks and settlement.'}</p></div>{isDemo&&<fieldset className="scenario"><legend>CHOOSE A DEMO OUTCOME</legend><button disabled={!!busy} className={scenario==='success'?'selected':''} onClick={()=>setScenario('success')}><CheckCircle2 size={17}/><span>Promise kept<small>Complete, structured brief</small></span></button><button disabled={!!busy} className={scenario==='breach'?'selected breach':''} onClick={()=>setScenario('breach')}><TriangleAlert size={17}/><span>Promise breached<small>Short, low-quality delivery</small></span></button></fieldset>}<button className="primary" disabled={!paid||!!busy} onClick={()=>update('deliver',{scenario})}><Sparkles size={17}/>Deliver & evaluate<ArrowRight size={17}/></button></>:<>
        <div className="score-row"><div className={`score-ring ${order!.refund_cents?'warning':''}`}><strong>{order!.evaluation!.score}</strong><span>/ 100</span></div><div><h3>{order!.refund_cents?'The promise fell short.':'A promise delivered.'}</h3><p className="muted">{order!.evaluation!.evaluator==='demo-fixture'?'Simulated AI verdict · demo fixture':'Azure OpenAI · independent evaluation'}</p><span className="small-badge">Threshold: 70 / 100</span></div></div>
        <div className="check-grid"><div><span>Length</span><strong>{order!.evaluation!.word_count} words</strong><small className={order!.evaluation!.word_count>=120&&order!.evaluation!.word_count<=220?'ok':'warn'}>{order!.evaluation!.word_count>=120&&order!.evaluation!.word_count<=220?'Within promise':'Outside promise'}</small></div><div><span>Structure</span><strong>{Object.values(order!.evaluation!.sections).filter(Boolean).length} / 3 sections</strong><small className={Object.values(order!.evaluation!.sections).every(Boolean)?'ok':'warn'}>{Object.values(order!.evaluation!.sections).every(Boolean)?'All present':'Missing sections'}</small></div><div><span>Quality</span><strong>{order!.evaluation!.quality_pass?'Passed':'Below threshold'}</strong><small className={order!.evaluation!.quality_pass?'ok':'warn'}>{order!.evaluation!.evaluator==='demo-fixture'?'Demo fixture':'AI assessment'}</small></div></div>
        <div className="tabs" role="tablist" aria-label="Evidence"><button role="tab" aria-selected={tab==='delivery'} onClick={()=>setTab('delivery')}>Delivered brief</button><button role="tab" aria-selected={tab==='evaluation'} onClick={()=>setTab('evaluation')}>Quality reasoning</button></div><div className="delivery" role="tabpanel">{tab==='delivery'?order!.delivery:order!.evaluation!.verdict.explanation}</div>
        <div className={`settlement ${order!.refund_cents?'refund':''}`}><div><span>{order!.refund_cents?'Policy-backed refund':'Settlement'}</span><strong>{order!.refund_cents?money(order!.refund_cents):'Full payment earned'}</strong><small>{order!.refund_cents?`${order!.evaluation!.refund_percent}% of ${money(order!.price_cents)} · ${order!.status==='refunded'?'completed':order!.status==='refund_pending'?'pending at PayPal':'eligible'}`:'The service met the agreed conditions.'}</small></div><ShieldCheck size={30}/></div>
        {order!.refund_cents>0&&order!.status==='evaluated'&&<button className="primary" disabled={!!busy} onClick={()=>update('refund')}>{isDemo?'Simulate policy refund':'Issue PayPal Sandbox refund'}<ArrowRight size={17}/></button>}
        </>}
      </div>
      <div className="card activity"><div className="activity-title"><h3>Transaction trail</h3><span><Clock3 size={13}/> AUDIT LOG</span></div>{order?<ol>{order.events.map((event,index)=><li key={index}><span className={`event-dot ${event.kind==='refund'?'refund-dot':''}`}/><div><strong>{event.kind}</strong><p>{event.message}</p></div><time>{new Date(event.at).toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'})}</time></li>)}</ol>:<p className="muted empty-log">Your order, payment and quality decisions will appear here.</p>}</div></section></div>
      <footer><span><ShieldCheck size={15}/> Built for accountable AI commerce.</span><span>ServicePromise AI · PayPal AI Hackathon 2026</span></footer>
    </main>{busy&&<div className="busy" role="status"><LoaderCircle size={18} className="spin"/>{busy}…</div>}
  </div>;
}

export default App;
