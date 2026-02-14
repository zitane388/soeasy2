import os
import struct
import io
import tempfile
import win32clipboard
import win32con
from PIL import Image
from automation.windly_config_loader import get_windly_temp_dir
import hashlib


def create_explorer_hdrop(file_list):
    file_utf16_list = []
    for path in file_list:
        file_utf16_list.append(path.encode("utf-16le") + b"\x00\x00")
    file_block = b"".join(file_utf16_list) + b"\x00\x00"

    pFiles = struct.pack("<I", 20)
    flags = struct.pack("<I", 0)
    point = struct.pack("<ii", 0, 0)

    return pFiles + flags + point + file_block


def copy_files_to_clipboard(file_list):
    data = create_explorer_hdrop(file_list)
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32con.CF_HDROP, data)
    win32clipboard.CloseClipboard()


def copy_image_file(path):
    print(f"[CLIPBOARD][IMG] start copy_image_file")
    print(f"[CLIPBOARD][IMG] path = {path}")

    if not os.path.exists(path):
        print(f"[CLIPBOARD][IMG][ERROR] file not found")
        return

    img = Image.open(path)
    try:
        with open(path, "rb") as f:
            md5 = hashlib.md5(f.read()).hexdigest()
        print(f"[CLIPBOARD][IMG] opened image size={img.size}, mode={img.mode}, md5={md5}")
    except Exception as e:
        print(f"[CLIPBOARD][IMG] opened image size={img.size}, mode={img.mode}, md5=ERR ({e})")

    if img.mode != "RGB":
        img = img.convert("RGB")
        print(f"[CLIPBOARD][IMG] converted to RGB")

    output = io.BytesIO()
    img.save(output, "BMP")
    bmp_bytes = output.getvalue()
    output.close()

    print(f"[CLIPBOARD][IMG] BMP total bytes = {len(bmp_bytes)}")

    data = bmp_bytes[14:]
    print(f"[CLIPBOARD][IMG] DIB bytes = {len(data)}")

    if len(data) < 100:
        print(f"[CLIPBOARD][IMG][WARN] DIB size too small, suspicious")

    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_DIB, data)
        win32clipboard.CloseClipboard()
        print(f"[CLIPBOARD][IMG] CF_DIB set SUCCESS")
        # Debug: verify clipboard content (optional)
        if os.environ.get("WINDLY_DEBUG_CLIPBOARD") == "1":
            try:
                win32clipboard.OpenClipboard()
                dib = win32clipboard.GetClipboardData(win32con.CF_DIB)
                win32clipboard.CloseClipboard()

                # Rebuild BMP header from DIB
                header_size = struct.unpack("<I", dib[:4])[0]
                bmp_size = 14 + len(dib)
                offset = 14 + header_size
                bmp_header = struct.pack("<2sIHHI", b"BM", bmp_size, 0, 0, offset)
                bmp_bytes = bmp_header + dib

                img = Image.open(io.BytesIO(bmp_bytes))
                img.load()

                temp_dir = get_windly_temp_dir() if os.path.isdir(get_windly_temp_dir()) else tempfile.gettempdir()
                os.makedirs(temp_dir, exist_ok=True)
                out_path = os.path.join(temp_dir, "clipboard_last.png")
                img.save(out_path)
                print(f"[CLIPBOARD][IMG][DEBUG] saved clipboard image -> {out_path}")
            except Exception as e:
                try:
                    win32clipboard.CloseClipboard()
                except Exception:
                    pass
                print(f"[CLIPBOARD][IMG][DEBUG] clipboard verify failed: {e}")
    except Exception as e:
        print(f"[CLIPBOARD][IMG][ERROR] clipboard failed:", e)


def copy_text(text):
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
    win32clipboard.CloseClipboard()
