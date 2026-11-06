// 구글 로그인으로 학습 기록을 기기 사이에 맞춘다 (Firebase Auth + Firestore).
// 저장 위치: users/{uid} 문서 하나. 기록(JSON)은 gzip으로 줄여 바이트로 넣는다.
import {firebaseConfig} from './firebase-config.js';

const V = '10.12.2', CDN = `https://www.gstatic.com/firebasejs/${V}`;
let fb = null, user = null, uploadTimer = null, busy = false, hooks = null, lastPulled = 0;

export const syncEnabled = () => !!firebaseConfig;
export const syncUser = () => user;

async function gzip(text) {
  if (typeof CompressionStream === 'undefined') return null;
  const s = new Blob([text]).stream().pipeThrough(new CompressionStream('gzip'));
  return new Uint8Array(await new Response(s).arrayBuffer());
}
async function gunzip(bytes) {
  const s = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
  return await new Response(s).text();
}

async function pull() {
  if (!user || busy) return;
  busy = true;
  try {
    const snap = await fb.getDoc(fb.doc(fb.db, 'users', user.uid));
    if (snap.exists()) {
      const d = snap.data();
      const raw = d.enc === 'gzip' ? await gunzip(d.data.toUint8Array()) : d.data;
      hooks.applyRemote(raw);
    }
    lastPulled = Date.now();
    busy = false;
    await push(); // 합친 결과(또는 처음 올리는 기록)를 바로 올린다
  } catch (e) {
    console.warn('동기화 불러오기 실패', e);
    hooks.onStatus('error');
  } finally { busy = false; }
}

async function push() {
  if (!user) return;
  const raw = hooks.getRaw();
  if (!raw) return;
  try {
    const z = await gzip(raw);
    const data = z ? {enc: 'gzip', data: fb.Bytes.fromUint8Array(z)} : {enc: 'json', data: raw};
    await fb.setDoc(fb.doc(fb.db, 'users', user.uid), {...data, updatedAt: fb.serverTimestamp()});
    hooks.onStatus('synced');
  } catch (e) {
    console.warn('동기화 저장 실패', e);
    hooks.onStatus('error');
  }
}

// 기록이 바뀔 때마다 부른다. 2초 모아서 한 번 올린다.
export function scheduleUpload() {
  if (!user) return;
  clearTimeout(uploadTimer);
  uploadTimer = setTimeout(push, 2000);
}

export async function signIn() {
  if (!fb) return;
  const provider = new fb.GoogleAuthProvider();
  try { await fb.signInWithPopup(fb.auth, provider); }
  catch (e) {
    if (e.code === 'auth/popup-blocked' || e.code === 'auth/operation-not-supported-in-this-environment') await fb.signInWithRedirect(fb.auth, provider);
    else if (e.code !== 'auth/popup-closed-by-user' && e.code !== 'auth/cancelled-popup-request') throw e;
  }
}
export async function signOutUser() {
  if (!fb) return;
  clearTimeout(uploadTimer);
  await push();
  await fb.signOut(fb.auth);
}

export async function initSync(h) {
  hooks = h;
  if (!firebaseConfig) return;
  const [app, auth, fs] = await Promise.all([
    import(`${CDN}/firebase-app.js`), import(`${CDN}/firebase-auth.js`), import(`${CDN}/firebase-firestore.js`)]);
  const a = app.initializeApp(firebaseConfig);
  const au = auth.getAuth(a);
  await auth.setPersistence(au, auth.browserLocalPersistence); // 로그인 상태를 이 기기에 계속 유지
  fb = {auth: au, db: fs.getFirestore(a), ...auth, ...fs};
  auth.getRedirectResult(au).catch(() => {});
  auth.onAuthStateChanged(au, u => {
    user = u;
    hooks.onUser(u);
    if (u) pull();
  });
  // 다른 기기에서 푼 기록을 다시 열 때 받아 온다
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && user && Date.now() - lastPulled > 15000) pull();
    if (document.visibilityState === 'hidden' && user && uploadTimer) { clearTimeout(uploadTimer); push(); }
  });
}
