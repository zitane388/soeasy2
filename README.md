# Soeasy2 - E-commerce Automation System

Uniqlo, GU, Muji 등의 상품 정보를 자동으로 스크래핑하고 네이버 스마트스토어에 업로드하는 자동화 시스템입니다.

## 주요 기능

- 🌐 **브랜드 상품 스크래핑**: Uniqlo/GU/Muji 등 해외 쇼핑몰 크롤링
- 🤖 **AI 상품명/설명 생성**: OpenAI GPT를 활용한 한국어 상품명 및 상세설명 자동 생성
- 🖼️ **이미지 처리**: 자동 썸네일 생성, 배경 제거, 상품 포커스
- 📦 **네이버 스마트스토어 연동**: 네이버 API를 통한 자동 상품 등록
- 🎨 **GUI 인터페이스**: tkinter 기반 사용자 친화적 인터페이스
- 🌐 **웹 UI**: React + Flask 기반 웹 인터페이스 (선택 사항)

## 시스템 요구사항

### Python 버전
- **Python 3.11** (필수)
  - Python 3.11.14에서 테스트 완료
  - Python 3.12+ 미지원 (mediapipe 호환성 문제)

### 운영체제
- macOS (테스트 완료)
- Windows (지원)
- Linux (지원 예상)

## 설치 방법

### 1. 저장소 클론
```bash
git clone <repository-url>
cd soeasy2
```

### 2. Python 3.11 설치
#### macOS (Homebrew)
```bash
brew install python@3.11
```

#### Windows
[Python 3.11 다운로드](https://www.python.org/downloads/)

### 3. 가상환경 생성 및 활성화
```bash
# 가상환경 생성
python3.11 -m venv .venv

# 가상환경 활성화
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows
```

### 4. 의존성 패키지 설치
```bash
pip install -r requirements.txt
```

### 5. Playwright 브라우저 설치
```bash
playwright install chromium
```

### 6. 환경 변수 설정
`.env` 파일을 생성하고 필요한 정보를 설정하세요.

**방법 1: 샘플 파일 복사**
```bash
cp .env.example .env
```

**방법 2: 직접 생성**
```bash
# .env
# OpenAI API Key
OPENAI_API_KEY=your-openai-api-key-here

# Naver SmartStore Credentials
NAVER_ID=your-naver-id@example.com
NAVER_PW=your-naver-password

# Windly Automation Credentials
WINDLY_USER_ID=your-windly-email@example.com
WINDLY_USER_PW=your-windly-password
```

**필수 설정:**
- `OPENAI_API_KEY`: OpenAI API 키 ([발급 링크](https://platform.openai.com/api-keys))
- `NAVER_ID`, `NAVER_PW`: 네이버 스마트스토어 계정
- `WINDLY_USER_ID`, `WINDLY_USER_PW`: Windly 자동화 계정

**⚠️ 중요**: `.env` 파일은 Git에 커밋되지 않도록 `.gitignore`에 포함되어 있습니다!

### 7. Chrome 확장 프로그램 설치 (필수)

프로그램이 상품 정보를 수집하려면 Chrome 확장 프로그램이 필요합니다.

**설치 방법:**
1. Chrome 브라우저에서 `chrome://extensions/` 접속
2. 우측 상단 "개발자 모드" 활성화
3. "압축해제된 확장 프로그램을 로드합니다" 클릭
4. 프로젝트의 `SoeasyExtension` 폴더 선택
5. 확장 프로그램이 활성화되었는지 확인

**지원 사이트:**
- Uniqlo Japan (uniqlo.com/jp)
- GU Japan (gu-global.com/jp)
- Muji Japan (muji.com/jp)
- Uniqlo Vietnam (uniqlo.com/vn)

## 실행 방법

### 옵션 1: GUI 모드 (tkinter)

```bash
# 가상환경 활성화 (아직 안 했다면)
source .venv/bin/activate

# 프로그램 실행
python main.py
```

GUI 창이 열리면 다음 기능을 사용할 수 있습니다:
1. **정보수집하기** - 상품 URL에서 정보 스크래핑
2. **썸네일 생성** - AI 기반 상품 이미지 최적화
3. **네이버 업로드** - 스마트스토어 자동 등록

### 옵션 2: 웹 UI 모드 (React + Flask)

웹 브라우저에서 사용할 수 있는 모던한 UI입니다.

```bash
# 웹 디렉토리로 이동
cd web

# 자동 실행 스크립트 사용 (권장)
./start.sh         # macOS/Linux
# or
start.bat          # Windows
```

또는 수동으로 실행:

```bash
# Terminal 1: Backend 실행
cd web/backend
pip install -r requirements.txt
python app.py

# Terminal 2: Frontend 실행
cd web/frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5173` 접속

**웹 UI 기능:**
- 📦 상품 수집 - URL 입력으로 간편 수집
- 🛍️ 네이버 베스트 상품 수집 - 4단계 자동화 워크플로우
- ✅ 수집 완료 - 상품 목록 관리
- 🔄 실시간 상태 업데이트 (WebSocket)

자세한 내용은 [web/README.md](web/README.md) 참고

## 프로젝트 구조

```
soeasy2/
├── main.py                 # 메인 실행 파일 (tkinter GUI)
├── gui/                    # tkinter GUI 인터페이스
├── web/                    # 웹 UI (선택 사항)
│   ├── backend/            # Flask API 서버
│   │   ├── app.py          # Flask 메인
│   │   └── api/            # API 라우트
│   ├── frontend/           # React 프론트엔드
│   │   └── src/            # React 소스
│   ├── start.sh            # 자동 실행 스크립트 (macOS/Linux)
│   ├── start.bat           # 자동 실행 스크립트 (Windows)
│   └── README.md           # 웹 UI 문서
├── scrapers/               # 브랜드별 스크래퍼
├── parsers/                # HTML 파싱 로직
├── llm/                    # OpenAI GPT 연동
├── image_tools/            # 이미지 처리 (썸네일, 배경제거)
├── naver_uploader/         # 네이버 API 업로드
├── automation/             # Windly 자동화
├── category/               # 카테고리 매칭
├── utils/                  # 유틸리티 함수
├── SoeasyExtension/        # Chrome 확장 프로그램 (필수)
│   ├── manifest.json       # 확장 프로그램 설정
│   ├── content.js          # 메인 스크립트
│   ├── background.js       # 백그라운드 서비스
│   └── handlers/           # 브랜드별 핸들러 (uniqlo_jp.js, gu_jp.js 등)
├── requirements.txt        # Python 패키지 목록
├── .env                    # 환경 변수 (Git 제외)
└── README.md               # 이 파일
```

## 주요 의존성

- **beautifulsoup4** - HTML 파싱
- **Flask** - HTML 수신 서버
- **Pillow** - 이미지 처리
- **openai** - GPT API 연동
- **playwright** - 브라우저 자동화
- **rembg** - 배경 제거
- **torch, torchvision** - 딥러닝 모델
- **mediapipe 0.10.5** - 포즈 감지 (solutions API 포함)
- **deep_translator** - 번역

## 문제 해결

### tkinter 오류 (macOS)
```bash
brew install python-tk@3.11
```

### mediapipe solutions 오류
```bash
# mediapipe 버전 확인
pip show mediapipe

# 0.10.5가 아니면 재설치
pip uninstall mediapipe
pip install mediapipe==0.10.5
```

### Playwright 브라우저 오류
```bash
playwright install chromium
```

## 개발 환경

- Python 3.11.14
- macOS Sequoia 15.2
- Homebrew 패키지 관리자

## 라이센스

(라이센스 정보 추가 필요)

## 문의

(문의처 정보 추가)
