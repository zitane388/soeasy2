# Soeasy2 Web Interface

웹 기반 UI를 제공하는 Soeasy2의 React + Flask 버전입니다.

## 구조

```
web/
├── backend/           # Flask API Server (port 5000)
│   ├── app.py        # Main Flask application
│   └── api/          # API blueprints
│       ├── collect.py
│       ├── naver_best.py
│       └── products.py
└── frontend/         # React Frontend (port 5173)
    └── src/
        ├── pages/    # Page components
        ├── hooks/    # Custom React hooks
        └── services/ # API client
```

## 설치 및 실행

### 1. Backend (Flask) 실행

```bash
cd web/backend

# 가상환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# Flask 서버 실행
python app.py
```

Flask 서버가 `http://localhost:5000`에서 실행됩니다.

### 2. Frontend (React) 실행

**새 터미널에서:**

```bash
cd web/frontend

# 의존성 설치 (최초 1회)
npm install

# 개발 서버 실행
npm run dev
```

React 앱이 `http://localhost:5173`에서 실행됩니다.

## 기능

### 📦 상품 수집 (CollectPage)
- Uniqlo, GU, Muji 상품 URL 입력
- Chrome Extension을 통한 자동 스크래핑
- 실시간 상태 업데이트 (WebSocket)

### 🛍️ 네이버 베스트 상품 수집 (NaverBestPage)
- **스토어 불러오기**: CSV에서 네이버 스마트스토어 URL 로드
- **리스트 수집**: 각 스토어의 베스트 상품 리스트 수집
- **상세 수집**: 상품 상세페이지 정보 수집
- **원산지 수집**: 원산지 정보 추가 수집

### ✅ 수집 완료 (CollectedPage)
- 수집된 상품 목록 표시
- 상품 상세 정보 확인
- 원본 URL 링크
- 상품 삭제 기능

## 기술 스택

### Backend
- **Flask**: 웹 프레임워크
- **Flask-SocketIO**: WebSocket 지원
- **Flask-CORS**: CORS 처리
- **eventlet**: 비동기 처리

### Frontend
- **React 18**: UI 라이브러리
- **Vite**: 빌드 도구
- **React Router**: 라우팅
- **Socket.io-client**: WebSocket 클라이언트
- **Axios**: HTTP 클라이언트
- **Tailwind CSS**: 스타일링
- **Lucide React**: 아이콘

## API 엔드포인트

### Collect API
- `POST /api/collect/scrape` - 상품 스크래핑 시작
- `GET /api/collect/pending` - 대기 중인 상품 목록

### Naver Best API
- `POST /api/naver-best/load-store` - 스토어 URL 로드
- `POST /api/naver-best/collect-list` - 리스트 수집
- `POST /api/naver-best/collect-details` - 상세 수집
- `POST /api/naver-best/collect-origin` - 원산지 수집

### Products API
- `GET /api/products/pending` - 대기 중인 상품 목록
- `GET /api/products/collected` - 수집 완료 상품 목록
- `DELETE /api/products/pending/<id>` - 대기 상품 삭제
- `DELETE /api/products/collected/<id>` - 완료 상품 삭제

## WebSocket Events

### 서버 → 클라이언트
- `status`: 상태 메시지
- `error`: 에러 메시지
- `product_collected`: 새 상품 수집 완료
- `naver_best_item`: 네이버 베스트 상품 수집

## 환경 변수

Backend는 프로젝트 루트의 `.env` 파일을 사용합니다:

```env
OPENAI_API_KEY=your-openai-api-key
NAVER_ID=your-naver-id
NAVER_PW=your-naver-password
WINDLY_USER_ID=your-windly-id
WINDLY_USER_PW=your-windly-password
```

## 개발 모드

### Backend Hot Reload
Flask는 디버그 모드에서 자동으로 코드 변경을 감지합니다.

### Frontend Hot Reload
Vite는 파일 변경 시 자동으로 브라우저를 새로고침합니다.

## 프로덕션 빌드

### Frontend 빌드
```bash
cd web/frontend
npm run build
```

빌드된 파일은 `dist/` 폴더에 생성됩니다.

### Backend 배포
프로덕션 환경에서는 `gunicorn` 사용을 권장합니다:

```bash
pip install gunicorn
gunicorn -k eventlet -w 1 -b 0.0.0.0:5000 app:app
```

## 트러블슈팅

### CORS 에러
- Backend의 `CORS` 설정에서 Frontend URL이 허용되어 있는지 확인
- 기본값: `http://localhost:5173`

### WebSocket 연결 실패
- Backend가 실행 중인지 확인
- 방화벽이 5000 포트를 차단하지 않는지 확인

### Chrome Extension 동작 안 함
- 프로젝트 루트의 `SoeasyExtension`이 Chrome에 설치되어 있는지 확인
- 메인 README의 Chrome Extension 설치 가이드 참고

## 병렬 실행

웹 UI는 기존 tkinter GUI와 **병렬로 동작**합니다:

- **tkinter GUI**: `python main.py` (기존 방식)
- **Web UI**: Backend + Frontend 동시 실행 (새로운 방식)

두 가지 방식 모두 동일한 백엔드 로직을 사용하므로, 편한 방식을 선택하여 사용하실 수 있습니다.
