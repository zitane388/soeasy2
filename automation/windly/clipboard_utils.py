import os
import subprocess
import tempfile
from PIL import Image


def copy_files_to_clipboard(file_list):
    """
    macOS에서 파일 목록을 클립보드로 복사 (Finder 형식)
    현재 프로젝트에서 사용되지 않는 것으로 보이므로 stub으로 유지
    """
    print(f"[CLIPBOARD][FILES] copy_files_to_clipboard not implemented on macOS")
    pass


def copy_image_file(path):
    """
    macOS에서 이미지를 클립보드로 복사
    osascript를 사용하여 이미지를 PNG 형식으로 클립보드에 저장
    """
    print(f"[CLIPBOARD][IMG] start copy_image_file")
    print(f"[CLIPBOARD][IMG] path = {path}")

    if not os.path.exists(path):
        print(f"[CLIPBOARD][IMG][ERROR] file not found")
        return

    try:
        img = Image.open(path)
        print(f"[CLIPBOARD][IMG] opened image size={img.size}, mode={img.mode}")

        # PNG 형식으로 임시 파일 생성
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            tmp_path = tmp_file.name

            # RGBA 모드로 변환하여 투명도 지원
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGBA')
                print(f"[CLIPBOARD][IMG] converted to RGBA")

            img.save(tmp_path, 'PNG')
            print(f"[CLIPBOARD][IMG] saved temp PNG to {tmp_path}")

        # osascript를 사용하여 클립보드에 복사
        # PNG 형식 (PNGf) 또는 TIFF 형식 (TIFFf)으로 복사 가능
        script = f'''
        set the clipboard to (read (POSIX file "{tmp_path}") as «class PNGf»)
        '''

        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True
        )

        # 임시 파일 삭제
        try:
            os.unlink(tmp_path)
        except:
            pass

        if result.returncode == 0:
            print(f"[CLIPBOARD][IMG] Image copied to clipboard SUCCESS")
        else:
            print(f"[CLIPBOARD][IMG][ERROR] osascript failed: {result.stderr}")

    except Exception as e:
        print(f"[CLIPBOARD][IMG][ERROR] clipboard failed:", e)


def copy_text(text):
    """
    macOS에서 텍스트를 클립보드로 복사
    pbcopy 명령을 사용
    """
    try:
        process = subprocess.Popen(
            ['pbcopy'],
            stdin=subprocess.PIPE,
            env={'LANG': 'en_US.UTF-8'}
        )
        process.communicate(text.encode('utf-8'))
        print(f"[CLIPBOARD][TEXT] Text copied to clipboard SUCCESS")
    except Exception as e:
        print(f"[CLIPBOARD][TEXT][ERROR] clipboard failed:", e)
