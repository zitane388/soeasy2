import time


def move_cursor_to_bottom(page):
    page.keyboard.down("Control")
    page.keyboard.press("End")
    page.keyboard.up("Control")
    time.sleep(0.05)


def apply_font_large(page):
    size_button = page.locator("span.ql-picker-label")
    size_button.first.click()
    time.sleep(0.2)

    large_option = page.locator("span.ql-picker-item[data-value='large']")
    large_option.click()
    time.sleep(0.3)


def open_detail_editor(page):
    page.locator("button:has-text('상세페이지')").first.click()
    time.sleep(2)


def clear_editor(page):
    editor = page.locator("div.ql-editor")
    editor.click()

    page.keyboard.down("Control")
    page.keyboard.press("A")
    page.keyboard.up("Control")

    page.keyboard.press("Delete")
    time.sleep(0.3)
