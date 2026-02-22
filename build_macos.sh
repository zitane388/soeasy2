# macOS Build Script

# Clean previous builds
rm -f main.spec
rm -rf dist
rm -rf build

# Kill running process (if any)
pkill -f main || true

# Build with PyInstaller
pyinstaller --noconfirm --onedir --console --clean \
--collect-all mediapipe \
--collect-all ultralytics \
--collect-all cv2 \
--add-data "llm:llm" \
--add-data "images:images" \
--add-data "data:data" \
--add-data "category/sources:category/sources" \
--add-data "automation/windly_config.json:automation" \
--add-data "naver_uploader/config.json:naver_uploader" \
--add-data "templates:templates" \
--add-data "parsers/product_pages/rules:parsers/product_pages/rules" \
--add-data "models:models" \
main.py

echo "Build complete! Check dist/main/"
