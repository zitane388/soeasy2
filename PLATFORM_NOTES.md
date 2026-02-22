# Platform Compatibility Notes

## macOS 호환성 수정 완료 ✅

### 수정된 파일:

1. **automation/windly/clipboard_utils.py**
   - Windows/macOS 플랫폼 자동 감지
   - macOS: `osascript`, `pbcopy` 사용
   - Windows: `win32clipboard` 사용 (기존 유지)

2. **browser_launcher.py**
   - macOS Chrome 경로 추가: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
   - Linux 경로도 추가

3. **gui/product_detail/description_panel.py**
   - Chrome 경로 플랫폼별 자동 감지
   - macOS/Linux 경로 추가

4. **requirements.txt**
   - `pywin32==306; sys_platform == 'win32'` - Windows 전용으로 설정
   - macOS에서는 자동으로 설치 제외

5. **build_macos.sh** (신규)
   - macOS용 빌드 스크립트
   - 실행: `./build_macos.sh`

### 의존성 차이:

- **Windows**: `pywin32` 필요
- **macOS**: 기본 시스템 도구 사용 (추가 패키지 불필요)

### 설치 방법:

```bash
# macOS/Linux
pip install -r requirements.txt

# Windows
pip install -r requirements.txt  # pywin32 자동 설치됨
```

### 실행 방법:

```bash
# 개발 환경
python main.py

# 빌드 (macOS)
./build_macos.sh

# 빌드 (Windows)
# PowerShell에서:
.\build_menual.txt 내용 실행
```

### 테스트 완료:
- ✅ 클립보드 기능 (파일, 이미지, 텍스트)
- ✅ Chrome 브라우저 실행
- ✅ 플랫폼 자동 감지

클립보드 기능은 자동으로 macOS 방식으로 동작합니다.

