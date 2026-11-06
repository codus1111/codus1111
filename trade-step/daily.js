// Reviewed local templates; no external AI, live law, tax-rate or exam-frequency claims.
const fmt=n=>n.toLocaleString('en-US');
export function shuffleQuestions(qs,rng=Math.random){
  const a=[...qs];
  for(let i=a.length-1;i>0;i--){const j=Math.floor(rng()*(i+1));[a[i],a[j]]=[a[j],a[i]];}
  return a;
}
export function selectQuestions(banks,{round='all',subject='전체',random=false,count}={},rng=Math.random){
  let qs=banks.filter(b=>round==='all'||Number(b.round)===Number(round)).flatMap(b=>b.questions).filter(q=>subject==='전체'||q.subject===subject);
  // Identity duplicates across banks are removed before selecting.
  const seen=new Set(); qs=qs.filter(q=>{const key=q.id??q;if(seen.has(key))return false;seen.add(key);return true;});
  if(random)qs=shuffleQuestions(qs,rng);
  return count==null?qs:qs.slice(0,Math.max(0,Math.floor(count)));
}
function seeded(s){let h=2166136261;for(const c of s)h=Math.imul(h^c.charCodeAt(0),16777619);return()=>{h+=0x6D2B79F5;let t=h;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return((t^t>>>14)>>>0)/4294967296;};}
const subjects=['기초 입문','무역규범','무역결제','무역계약','무역영어'];
function raw(subject,lessonId,prompt,answers){return{subject,lessonId,prompt,answers};}
function numeric(subject,lessonId,prompt,value,unit,work,offset){
  const values=[value,value+offset,value-offset,value+2*offset];
  return raw(subject,lessonId,prompt,values.map((n,i)=>[`${fmt(n)}${unit}`,i===0?`${work} 따라서 ${fmt(value)}${unit}입니다.`:`${fmt(n)}${unit}는 주어진 조건의 계산 결과가 아닙니다. ${work} 따라서 정답은 ${fmt(value)}${unit}입니다.`]));
}
const cases={
  payment:[
    ['payment-2','UCP 600 적용을 명시한 신용장 거래에서 은행 심사의 중심 대상은?',[
      ['신용장 조건 등에 일치하는 서류 제시','은행은 원칙적으로 물품 자체가 아니라 서류를 취급하며 신용장 조건·적용 규칙에 맞는 제시를 심사합니다.'],['물품의 실제 품질을 은행이 직접 검사','물품 품질에 관한 매매 분쟁과 은행의 서류 심사는 구분해야 합니다.'],['물품 도착만으로 무조건 지급','물품 도착만으로 일치하는 서류 제시가 이루어졌다고 볼 수 없습니다.'],['송금 통화만 맞으면 다른 조건은 무시','통화 외에도 신용장 조건과 적용 규칙에 맞는 서류 제시인지 확인해야 합니다.']]],
    ['payment-2','통지은행이 신용장을 수출자에게 통지했습니다. 통지 사실만으로 판단할 수 있는 것은?',[
      ['통지만으로 별도의 지급확약이 추가되지는 않는다','통지은행은 신용장을 통지하며 통지만 했다는 사실은 독자적 지급확약의 추가를 뜻하지 않습니다.'],['통지은행이 언제나 확인은행이 된다','확인의 추가와 단순한 통지는 다르므로 통지은행이 언제나 확인은행이 되는 것은 아닙니다.'],['통지은행이 물품 품질을 보증한다','신용장 통지는 물품의 실제 품질 보증을 뜻하지 않습니다.'],['매매계약이 통지로 자동 변경된다','신용장은 매매계약과 별개로 취급되며 통지가 매매 조건을 자동 변경하지 않습니다.']]],
    ['payment-1','D/A 추심에서 서류 인도의 연결 대상은 무엇인가요?',[
      ['어음의 인수','D/A는 Documents against Acceptance로 어음 인수와 서류 인도를 연결합니다. 인수와 만기 지급은 구분합니다.'],['반드시 즉시 현금 지급','대금 지급과 연결되는 D/P와 달리 D/A는 인수와 연결하므로 즉시 현금 지급으로 단정하지 않습니다.'],['은행의 무조건 지급보증','추심 업무에 은행이 참여했다는 사실만으로 신용장 같은 지급확약이 생기는 것은 아닙니다.'],['화물의 품질 검사 완료','D/A의 인수는 어음의 만기 지급 의무와 관련되며 화물 품질 검사를 뜻하지 않습니다.']]],
    ['payment-2','일반적인 수입 신용장 거래에서 해외 판매자인 수출자의 지위는?',[
      ['수익자(Beneficiary)','일반적인 수입 신용장에서 수출자는 신용장에 따라 이익을 받는 수익자입니다.'],['개설의뢰인(Applicant)','일반적인 수입 신용장에서 개설을 의뢰하는 쪽은 수입자이며 수출자는 수익자입니다.'],['개설은행(Issuing bank)','개설은행은 의뢰에 따라 신용장을 발행하는 은행으로 판매자인 수출자와 다릅니다.'],['통지은행(Advising bank)','통지은행은 신용장을 수익자에게 통지하는 은행으로 수출자 자신을 의미하지 않습니다.']]]
  ],
  rules:[
    ['rules-1','해외 기계를 수입하는 회사가 세관 신고 절차를 확인하고 있습니다. 가장 직접 연결되는 입문 개념은?',[
      ['통관','통관은 물품의 국경 이동과 관련된 세관의 법정 절차입니다.'],['운송계약 체결','운송계약은 화물 운송의 약정이며 세관 신고 자체와 구분합니다.'],['은행의 지급확약','은행의 지급확약은 결제의 문제이며 세관 신고 절차를 뜻하지 않습니다.'],['매매대금 협상','가격 협상은 계약 당사자의 거래 조건 결정이며 세관 절차와 다릅니다.']]],
    ['rules-2','수입 화물이 항구에 도착했습니다. 통관 완료 여부를 판단하는 가장 적절한 태도는?',[
      ['필요한 세관 신고와 법정 절차의 이행을 별도로 확인한다','물리적인 도착과 세관 법정 절차 완료는 다르므로 별도로 확인해야 합니다.'],['도착만으로 통관 완료로 본다','도착은 물리적 사건이며 세관 절차가 끝났다는 뜻이 아닙니다.'],['창고에 보관하면 신고가 대체된다','창고 보관과 세관 신고는 다른 행위이므로 보관만으로 대체되지 않습니다.'],['운임 지급만 확인한다','운임은 운송의 대가이며 세관 신고 이행을 증명하지 않습니다.']]],
    ['rules-3','판매자가 물품을 A국에서 선적했다는 사실만 알려주었습니다. 원산지 판단에 적절한 설명은?',[
      ['선적국만으로 원산지를 확정하지 않는다','원산지는 적용되는 원산지 기준과 생산 관련 사실 등으로 판단하며 선적국과 같다고 단정할 수 없습니다.'],['선적국은 항상 원산지다','선적은 출발 장소의 정보로, 생산과 원산지 기준 충족을 곧바로 증명하지 않습니다.'],['구매자의 소재지가 항상 원산지다','구매자 소재지는 거래 당사자의 정보이며 물품의 원산지 기준을 대신하지 않습니다.'],['송금 통화가 원산지를 정한다','결제 통화는 지급 조건이며 물품의 생산 및 원산지 기준과 다른 정보입니다.']]],
    ['rules-2','회사 직원이 수입 신고용 물품의 재질과 용도를 조사합니다. 가장 직접 관련된 것은?',[
      ['품목분류','품목분류는 어떤 물품인지 분류하는 작업으로 재질과 용도가 판단에 연결될 수 있습니다.'],['신용장 통지','신용장 통지는 은행의 결제 관련 업무이며 물품분류 작업이 아닙니다.'],['송금 통화 결정','결제 통화를 정하는 것과 재질·용도에 따른 품목분류는 다릅니다.'],['운임 선지급 표시','운임 지급 표시는 운송비 처리 정보이며 품목분류를 대신하지 않습니다.']]]
  ],
  contract:[
    ['contract-2','CIF 지정 목적항 Incoterms 2020 거래에서 매도인이 목적항까지 운임을 부담합니다. 위험 이전에 관한 설명은?',[
      ['선적항에서 본선 적재 시 위험이 이전한다','CIF의 위험은 선적항에서 본선에 적재할 때 이전하며 목적항까지의 운임 부담과 구분합니다.'],['목적항 도착 시까지 매도인이 언제나 위험을 부담한다','CIF는 목적항까지의 비용 부담과 위험 이전 지점이 같지 않습니다. 위험은 선적항 본선 적재 시 이전합니다.'],['물품대금 송금 시 위험이 이전한다','CIF 위험 이전은 결제 시점이 아니라 선적항 본선 적재라는 인도 지점에 연결됩니다.'],['소유권 이전일을 CIF가 모두 정한다','Incoterms는 소유권 이전을 모두 정해 주지 않습니다. CIF 위험 이전과 소유권 약정은 구분합니다.']]],
    ['contract-1','CISG 적용 거래에서 구매자가 가격을 낮춘 조건으로 동의한다고 답했습니다. 가장 적절한 검토는?',[
      ['중요한 조건의 변경 여부와 적용 규칙을 살핀다','가격 변경을 원래 청약에 대한 무조건 승낙으로 단정하지 말고 변경 내용과 적용 규칙을 확인합니다.'],['가격 변경이 있어도 항상 무조건 승낙이다','가격은 중요한 조건이므로 변경을 무시하여 무조건 승낙으로 볼 수 없습니다.'],['침묵 자체와 언제나 동일하다','가격을 바꾼 답변은 적극적인 의사표시로 침묵 자체와 다릅니다.'],['운송서류가 청약 내용을 자동 수정한다','운송서류가 당사자의 가격 변경 답변에 관한 법적 판단을 자동 대체하지 않습니다.']]],
    ['contract-3','항공화물운송장 AWB를 받은 담당자가 서류의 성질을 확인합니다. 적절한 설명은?',[
      ['AWB는 일반적으로 유통성 있는 권리증권으로 보지 않는다','AWB는 항공운송 서류이며 일반적으로 유통성 있는 권리증권으로 보지 않습니다.'],['AWB는 언제나 해상 지시식 B/L과 같다','AWB와 해상 선하증권은 운송 방식과 성질이 다르므로 같게 취급할 수 없습니다.'],['모든 운송서류는 반드시 배서로 권리를 이전한다','운송서류마다 성질이 다르므로 모든 서류가 같은 권리증권인 것은 아닙니다.'],['AWB가 보험 담보 범위를 모두 증명한다','운송서류는 보험계약의 담보 조건 확인을 대신하지 않습니다.']]],
    ['contract-3','운송 중 화물 손해가 발생했고 적하보험이 있습니다. 다음으로 확인할 사항은?',[
      ['담보 조건·면책·보험 기간과 구간','보험의 존재만으로 모든 손해가 보상되지는 않으며 약정된 담보와 면책 등을 확인합니다.'],['보험이 있으므로 원인에 관계없이 전액 보상','적하보험에는 담보 조건과 면책이 있으므로 모든 원인에 대한 보상을 단정할 수 없습니다.'],['운송장 이름만으로 보상 범위 확정','운송장과 보험계약은 역할이 다르므로 보험의 담보 범위는 보험 조건에서 확인합니다.'],['송장 금액만 알면 면책 확인 불필요','송장 금액을 알아도 해당 위험의 담보 여부와 면책은 별도로 확인해야 합니다.']]]
  ]
};
export function generateDailyQuestions(dayKey,count=10){
  if(!/^\d{4}-\d{2}-\d{2}$/.test(dayKey)||new Date(dayKey+'T00:00:00Z').toISOString().slice(0,10)!==dayKey)throw new RangeError('유효한 YYYY-MM-DD가 필요합니다.');
  if(!Number.isInteger(count)||count<0||count>100)throw new RangeError('count는 0~100 정수입니다.');
  const rng=seeded(dayKey),ordinal=Math.floor(Date.parse(dayKey+'T00:00:00Z')/86400000);
  const n=(min,max)=>min+Math.floor(rng()*(max-min+1));
  const product=['머그잔','노트','수건','텀블러','가방','연필 세트'][ordinal%6];
  const out=[];
  for(let i=0;i<count;i++){
    const subject=subjects[Math.floor((i%10)/2)],slot=i%10,cycle=Math.floor(i/10);
    let q;
    if(slot<2){
      const price=n(5,75),qty=n(12,190),boxes=n(3,20);
      q=slot===0?numeric(subject,'intro-2',`가상 주문: ${product} ${qty}개를 개당 ${price}달러에 구매합니다. 다른 비용과 할인은 없고 반올림은 필요 없습니다. 물품 총액을 계산하면?`,price*qty,'달러',`${qty}개 × ${price}달러/개 = ${fmt(price*qty)}달러입니다.`,price):numeric(subject,'intro-3',`가상 포장명세서: ${product}가 상자당 ${qty}개씩 ${boxes}상자입니다. 빈 상자와 추가 물품은 없습니다. 총 수량을 계산하면?`,qty*boxes,'개',`${qty}개/상자 × ${boxes}상자 = ${fmt(qty*boxes)}개입니다.`,qty);
    }else if(slot===2||slot===3||slot===6||slot===7){
      const group=slot<4?'rules':'contract',templates=cases[group],idx=(ordinal+slot%2+cycle*2)%templates.length;
      const [lessonId,prompt,answers]=templates[idx];
      // Scenario context rotates separately from concept; no claim to be an official exam item.
      q=raw(subject,lessonId,`가상 ${product} 거래 사례: ${prompt}`,answers);
    }else if(slot===5 && ordinal%2===1){
      const [lessonId,prompt,answers]=cases.payment[(Math.floor(ordinal/2)+cycle)%cases.payment.length];
      q=raw(subject,lessonId,`가상 ${product} 거래 사례: ${prompt}`,answers);
    }else if(slot===4||slot===5){
      const usd=n(10,180)*100,rate=n(110,150)*10,change=n(1,8)*10;
      if(slot===4)q=numeric(subject,'payment-3',`${fmt(usd)}달러를 받는 수출자입니다. 1달러=${fmt(rate)}원으로 전액 환전합니다. 수수료·다른 비용은 없고 반올림은 필요 없습니다. 계산한 원화 수령액은?`,usd*rate,'원',`${fmt(usd)}달러 × ${fmt(rate)}원/달러 = ${fmt(usd*rate)}원입니다.`,usd*10);
      else {const rise=(ordinal+cycle)%2===0,delta=usd*change; q=numeric(subject,'payment-3',`수출자가 받을 대금은 ${fmt(usd)}달러로 같습니다. 원/달러 환율이 ${fmt(rate)}원에서 ${fmt(rate+(rise?change:-change))}원으로 ${rise?'상승':'하락'}했습니다. 수수료·원가·헤지는 없고 반올림은 필요 없습니다. 원화 수령액의 ${rise?'증가액':'감소액'}을 계산하면?`,delta,'원',`환율 차이는 ${change}원/달러이고, ${fmt(usd)}달러 × ${change}원/달러 = ${fmt(delta)}원 ${rise?'증가':'감소'}입니다.`,usd*10);}
    }else if(slot===8){
      const price=n(5,90),qty=n(15,150);
      q=numeric(subject,'english-1',`"Unit price: USD ${price} per unit; Quantity: ${qty} units." 할인·추가 비용은 없으며 반올림은 필요 없습니다. 이 조건의 물품 총액을 계산하면?`,price*qty,'달러',`per unit은 개당이므로 ${price}달러/개 × ${qty}개 = ${fmt(price*qty)}달러입니다.`,price);
    }else{
      const start=n(1,12),days=n(5,14),month=n(1,12),end=start+days;
      q=numeric(subject,'english-3',`가상 약정: "Payment within ${days} days after the invoice date." 송장일은 ${month}월 ${start}일입니다. 송장일 다음 날을 제1일로 세고 주말·공휴일도 포함하며 기한 연장은 없다고 명시했습니다. 같은 달의 지급 마감일은?`,end,'일',`after the invoice date의 기준은 송장일입니다. 다음 날부터 ${days}일을 세면 ${start} + ${days} = ${end}, 즉 ${month}월 ${end}일입니다.`,1);
    }
    const answers=shuffleQuestions(q.answers.map(([text,explanation],j)=>({text,explanation,correct:j===0})),rng);
    out.push({id:`daily-${dayKey}-${i+1}`,sourceType:'generated',subject:q.subject,lessonId:q.lessonId,prompt:q.prompt,options:answers.map(a=>a.text),correctIndex:answers.findIndex(a=>a.correct),explanations:answers.map(a=>a.explanation),version:1,dayKey});
  }
  return out;
}
