// Firebase 콘솔 > 프로젝트 설정 > 내 앱(웹)에 나오는 값. 웹 앱용 공개 값이라 저장소에 올려도 된다.
// 기록 보호는 Firestore 보안 규칙(users/{uid}는 본인만)으로 한다. null로 바꾸면 로그인 버튼이 숨는다.
export const firebaseConfig = {
  apiKey: "AIzaSyDMDhVBkdtgeocAOxAHNYv2_gLOFQo02qs",
  authDomain: "trend-step-f2534.firebaseapp.com",
  projectId: "trend-step-f2534",
  storageBucket: "trend-step-f2534.firebasestorage.app",
  messagingSenderId: "401326101933",
  appId: "1:401326101933:web:4d98a4b7c3604e957e3d24"
};
