const KEY='trade-step-v1';
const base=()=>({version:1,completed:[],attempts:[],lastLesson:null,exam:null,reviewedWrongs:{},savedReviews:{},daily:null,storageIssue:null});
const validDate=n=>Number.isFinite(n)&&Number.isFinite(new Date(n).getTime());
const answer=n=>Number.isInteger(n)&&n>=0&&n<=3;
function validQuestion(q){return q&&typeof q.id==='string'&&q.id.length>0&&typeof q.prompt==='string'&&Array.isArray(q.options)&&q.options.length===4&&q.options.every(x=>typeof x==='string')&&Array.isArray(q.explanations)&&q.explanations.length===4&&q.explanations.every(x=>typeof x==='string')&&answer(q.correctIndex)&&(!q.correctIndices||(Array.isArray(q.correctIndices)&&q.correctIndices.length>0&&q.correctIndices.every(answer)))}
function restoreSession(x){
 if(!x||typeof x.id!=='string'||!x.id||!['study','test'].includes(x.mode)||!validDate(x.deadline)||typeof x.finished!=='boolean'||!x.answers||typeof x.answers!=='object'||Array.isArray(x.answers)||!Array.isArray(x.flagged)||!Array.isArray(x.revealed))throw Error();
 const exam=validateExam(x.exam),ids=new Set(exam.questions.map(q=>q.id)),oldIds=new Map(exam.questions.map(q=>[q.originalId,q.id]));
 const remap=k=>ids.has(k)?k:oldIds.get(k);
 const answers=Object.create(null);
 for(const [k,v] of Object.entries(x.answers)){const id=remap(k);if(!id||!answer(v))throw Error();answers[id]=v;}
 const flags=xs=>xs.map(k=>{const id=remap(k);if(typeof k!=='string'||!id)throw Error();return id});
 return{...x,exam,answers,flagged:flags(x.flagged),revealed:flags(x.revealed)};
}
const snapshotFields=['id','originalId','lessonId','prompt','options','correctIndex','correctIndices','explanations','sourceType','version','subject','dayKey','round','examTitle','number','subjectNumber','shortLabel','imagePaths','sourcePages','source','sourcePdf','answerPdf','explanationStatus','answerCorrection','explanationSources','explanationSummary'];
function snapshotQuestion(q){return Object.fromEntries(snapshotFields.filter(k=>q[k]!==undefined).map(k=>[k,structuredClone(q[k])]))}
function packState(s){
 const questionPool=Object.create(null),known=new Map();
 const ref=q=>{const snap=snapshotQuestion(q),encoded=JSON.stringify(snap);if(known.has(encoded))return known.get(encoded);const id='q'+known.size;known.set(encoded,id);questionPool[id]=snap;return id};
 const attempts=s.attempts.map(({question,...a})=>({...a,questionRef:ref(question)}));
 const savedReviews=Object.fromEntries(Object.entries(s.savedReviews||{}).map(([id,{question,...v}])=>[id,{...v,questionRef:ref(question)}]));
 const exam=s.exam?{...s.exam,exam:{...s.exam.exam,questions:s.exam.exam.questions.map(snapshotQuestion)}}:null;
 return{...s,attempts,savedReviews,exam,questionPool};
}
export function loadState(storage){
 let raw;try{raw=storage.getItem(KEY)}catch{return{...base(),storageIssue:'blocked'}}
 if(!raw)return base();
 try{
  const x=JSON.parse(raw);
  if(x?.questionPool&&typeof x.questionPool==='object'){
   const get=ref=>Object.hasOwn(x.questionPool,ref)?x.questionPool[ref]:undefined;
   if(Array.isArray(x.attempts))x.attempts=x.attempts.map(a=>a&&a.questionRef?{...a,question:get(a.questionRef)}:a);
   if(x.savedReviews&&typeof x.savedReviews==='object')x.savedReviews=Object.fromEntries(Object.entries(x.savedReviews).map(([k,v])=>[k,v?.questionRef?{...v,question:get(v.questionRef)}:v]));
  }
  if(!x||x.version!==1||!Array.isArray(x.attempts)||!Array.isArray(x.completed))throw Error();
  const completed=x.completed.filter(i=>typeof i==='string');
  const attempts=x.attempts.filter(a=>a&&typeof a.id==='string'&&validQuestion(a.question)&&answer(a.answer)&&typeof a.correct==='boolean'&&a.correct===isCorrect(a.question,a.answer)&&validDate(a.time));
  let corrupt=completed.length!==x.completed.length||attempts.length!==x.attempts.length,exam=null;
  if(x.exam){try{exam=restoreSession(x.exam)}catch{corrupt=true}}
  const reviewedWrongs=Object.create(null),savedReviews=Object.create(null);
  for(const [k,v] of Object.entries(x.reviewedWrongs||{})){if(v&&typeof v==='object'&&(v.lastWrongId===null||typeof v.lastWrongId==='string')&&Number.isInteger(v.savedRevision))reviewedWrongs[k]=v;}
  for(const [k,v] of Object.entries(x.savedReviews||{})){if(v&&validQuestion(v.question)&&v.question.id===k&&Number.isInteger(v.revision)&&v.revision>0)savedReviews[k]=v;}
  let daily=null;if(x.daily&&/^\d{4}-\d{2}-\d{2}$/.test(x.daily.dayKey)&&x.daily.answers&&typeof x.daily.answers==='object'){daily={dayKey:x.daily.dayKey,answers:Object.fromEntries(Object.entries(x.daily.answers).filter(([k,v])=>answer(v)))};}
  return{...base(),completed,attempts,reviewedWrongs,savedReviews,daily,lastLesson:typeof x.lastLesson==='string'?x.lastLesson:null,exam,storageIssue:corrupt?'corrupt':null};
 }catch{return{...base(),storageIssue:'corrupt'}}
}
export function saveState(storage,state){if(state.storageIssue==='corrupt')return false;try{storage.setItem(KEY,JSON.stringify(packState(state)));return true}catch{return false}}
export function toggleComplete(s,id){return{...s,completed:s.completed.includes(id)?s.completed.filter(x=>x!==id):[...s.completed,id]}}
export function submitAnswer(s,q,selected,id){if(s.attempts.some(a=>a.id===id))return s;if(!answer(selected))throw Error('답을 선택해 주세요.');return{...s,attempts:[...s.attempts,{id,question:snapshotQuestion(q),answer:selected,correct:isCorrect(q,selected),time:Date.now()}]}}
export function getWrongs(s,unresolved=false){
 const m=new Map();
 for(const a of s.attempts){
  const key=a.question.id;
  if(!a.correct&&!m.has(key))m.set(key,{question:a.question,attempts:[],resolved:false,lastWrongId:a.id});
  if(m.has(key)){const w=m.get(key);w.attempts.push(a);w.resolved=a.correct;if(!a.correct)w.lastWrongId=a.id;}
 }
 for(const [id,w] of m){const done=s.reviewedWrongs?.[id];if(done&&done.lastWrongId===w.lastWrongId&&done.savedRevision===(s.savedReviews?.[id]?.revision||0))w.resolved=true;}
 return [...m.values()].filter(w=>!unresolved||!w.resolved).reverse();
}
export function getReviewItems(s,neededOnly=false){
 const m=new Map(getWrongs(s).map(w=>[w.question.id,{...w,manual:false}]));
 for(const [id,v] of Object.entries(s.savedReviews||{})){
  const ats=s.attempts.filter(a=>a.question.id===id),latest=ats.at(-1);
  const w=m.get(id)||{question:v.question,attempts:ats,resolved:false,lastWrongId:null};
  w.manual=true;
  const done=s.reviewedWrongs?.[id];
  w.resolved=!!(done&&done.lastWrongId===w.lastWrongId&&done.savedRevision===v.revision)||!!(latest?.correct&&latest.id!==v.afterAttemptId);
  m.set(id,w);
 }
 return [...m.values()].filter(w=>!neededOnly||!w.resolved).reverse();
}
export function setWrongReviewed(s,id,reviewed=true){
 const markers={...(s.reviewedWrongs||{})},w=getReviewItems(s).find(w=>w.question.id===id);
 if(!w)return s;
 if(!reviewed)return markQuestionForReview({...s,reviewedWrongs:markers},w.question);
 markers[id]={lastWrongId:w.lastWrongId,savedRevision:s.savedReviews?.[id]?.revision||0};
 return{...s,reviewedWrongs:markers};
}
export function markQuestionForReview(s,q){
 const savedReviews={...(s.savedReviews||{})},reviewedWrongs={...(s.reviewedWrongs||{})};
 const ats=s.attempts.filter(a=>a.question.id===q.id);
 savedReviews[q.id]={question:snapshotQuestion(q),revision:(savedReviews[q.id]?.revision||0)+1,afterAttemptId:ats.at(-1)?.id||null,savedAt:Date.now()};
 delete reviewedWrongs[q.id];
 return{...s,savedReviews,reviewedWrongs};
}
export function studyDayKey(now=Date.now()){return new Date(now+8*3600000).toISOString().slice(0,10)}
export function todayCount(s,now=Date.now()){const key=studyDayKey(now);return s.attempts.filter(a=>studyDayKey(a.time)===key).length}
export function nextStudyReset(now=Date.now()){return (Math.floor((now+8*3600000)/86400000)+1)*86400000-8*3600000}
export function isCorrect(q,selected){return Number.isInteger(selected)&&(q.correctIndices||[q.correctIndex]).includes(selected)}
export function stats(s){const a=s.attempts;const first=[...new Map([...a].reverse().map(x=>[x.question.id,x])).values()];return{count:a.length,accuracy:a.length?Math.round(a.filter(x=>x.correct).length/a.length*100):null,firstAccuracy:first.length?Math.round(first.filter(x=>x.correct).length/first.length*100):null}}
export function validateExam(x){
 if(!x||typeof x.title!=='string'||!x.title.trim()||x.title.length>120||typeof x.source!=='string'||x.source.length>2048||!Array.isArray(x.questions)||!x.questions.length||x.questions.length>200)throw Error('회차 이름, http(s) 출처, 1~200개 문항이 필요해요.');
 let url;try{url=new URL(x.source)}catch{throw Error('자료 출처 주소를 확인해 주세요.')}
 if(!['http:','https:'].includes(url.protocol)||url.username||url.password)throw Error('자료 출처는 일반 http(s) 주소여야 해요.');
 const title=x.title.trim(),source=url.href,scope=`past:${encodeURIComponent(source)}:${encodeURIComponent(title)}:`,ids=new Set(),numbers=new Set();
 const questions=x.questions.map((q,i)=>{
  if(!q||typeof q.prompt!=='string'||!q.prompt.trim()||!Array.isArray(q.options)||q.options.length!==4||q.options.some(v=>typeof v!=='string'||!v.trim())||!Array.isArray(q.explanations)||q.explanations.length!==4||q.explanations.some(v=>typeof v!=='string'||!v.trim())||!answer(q.correctIndex)||(q.subject!==undefined&&typeof q.subject!=='string')||(q.correctIndices!==undefined&&(!Array.isArray(q.correctIndices)||!q.correctIndices.length||q.correctIndices.some(v=>!answer(v)))))throw Error(`${i+1}번의 보기·정답·해설을 확인해 주세요.`);
  const originalId=String(q.originalId??q.id??i+1),number=q.number??i+1;
  if(!originalId||originalId.length>400||ids.has(originalId))throw Error('문항 ID가 중복되거나 너무 길어요.');
  if(!Number.isInteger(number)||number<1||number>10000||numbers.has(number))throw Error('원래 문항 번호가 중복되거나 올바르지 않아요.');
  ids.add(originalId);numbers.add(number);
  const imagePaths=Array.isArray(q.imagePaths)?q.imagePaths.filter(p=>typeof p==='string'&&/^assets\/past\/(?:images\/)?[a-zA-Z0-9_.-]+\.(?:webp|png|jpg)$/.test(p)):[];
  const explanationSources=Array.isArray(q.explanationSources)?q.explanationSources.filter(s=>s&&typeof s.name==='string'&&typeof s.url==='string'&&/^https?:\/\//.test(s.url)).map(s=>({name:s.name,url:s.url})):[];
  const c=q.answerCorrection;const answerCorrection=c&&typeof c==='object'&&Array.isArray(c.acceptedAnswers)&&c.acceptedAnswers.every(a=>typeof a==='string')&&typeof c.sourceCorrectionDate==='string'?{sourceCorrectionDate:c.sourceCorrectionDate,acceptedAnswers:c.acceptedAnswers}:null;
  return{...q,imagePaths,answerCorrection,explanationSources,id:scope+encodeURIComponent(originalId),originalId,number,sourceType:'past',source,examTitle:title,subject:q.subject||'미분류',lessonId:typeof q.lessonId==='string'?q.lessonId:null,version:q.version||1};
 });
 return{...x,round:Number.isInteger(x.round)&&x.round>0&&x.round<10000?x.round:undefined,title,source,questions,durationMinutes:Number.isFinite(x.durationMinutes)&&x.durationMinutes>=1&&x.durationMinutes<=600?x.durationMinutes:120};
}
export function gradeExam(e,answers){let correct=0,unanswered=0;const perSubject=Object.create(null);for(const q of e.questions){const selected=Object.hasOwn(answers,q.id)?answers[q.id]:undefined;if(selected===undefined)unanswered++;if(isCorrect(q,selected))correct++;perSubject[q.subject]??={total:0,correct:0};perSubject[q.subject].total++;if(isCorrect(q,selected))perSubject[q.subject].correct++;}return{correct,unanswered,total:e.questions.length,percent:Math.round(correct/e.questions.length*100),perSubject}}
export function remainingSeconds(session,now=Date.now()){return Math.max(0,Math.ceil((session.deadline-now)/1000))}
// 두 기기의 기록을 합친다 (로그인 동기화용). 풀이 기록은 id 기준으로 모두 모으고, 나머지는 더 새로운 쪽을 고른다.
export function mergeStates(a,b){
 const attempts=[...new Map([...b.attempts,...a.attempts].map(x=>[x.id,x])).values()].sort((x,y)=>x.time-y.time);
 const completed=[...new Set([...b.completed,...a.completed])];
 const pick=(x,y,key)=>{const out=Object.create(null);for(const [k,v] of Object.entries(y||{}))out[k]=v;for(const [k,v] of Object.entries(x||{}))if(!out[k]||(v[key]||0)>=(out[k][key]||0))out[k]=v;return out};
 let daily=a.daily||b.daily;
 if(a.daily&&b.daily)daily=a.daily.dayKey===b.daily.dayKey?{dayKey:a.daily.dayKey,answers:{...b.daily.answers,...a.daily.answers}}:(a.daily.dayKey>b.daily.dayKey?a.daily:b.daily);
 return{...base(),completed,attempts,reviewedWrongs:pick(a.reviewedWrongs,b.reviewedWrongs,'savedRevision'),savedReviews:pick(a.savedReviews,b.savedReviews,'revision'),daily,lastLesson:a.lastLesson||b.lastLesson,exam:a.exam||b.exam,storageIssue:a.storageIssue};
}
export const STATE_KEY=KEY;
