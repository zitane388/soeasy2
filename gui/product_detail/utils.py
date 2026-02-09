import tkinter as tk

class Toast:
    """
    detail_window, thumb_panel 등에서 호출하는 토스트 메세지 팝업.
    부모 위에 1~3초 동안 작게 떠서 자동으로 사라지는 구조.
    """

    @staticmethod
    def show(parent, message, duration=2000):
        """
        parent: 토스트가 뜰 Tk 또는 Toplevel 또는 Frame
        message: 표시할 문자열
        duration: 표시 시간(ms)
        """

        # 최상위(overlay) 작은 창
        toast = tk.Toplevel(parent)
        toast.overrideredirect(True)  # 테두리 제거
        toast.attributes("-topmost", True)

        # 라벨 구성
        label = tk.Label(
            toast,
            text=message,
            bg="#333333",
            fg="white",
            padx=12,
            pady=6
        )
        label.pack()

        # parent 중심으로 위치 조정
        toast.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()

        tw = toast.winfo_width()
        th = toast.winfo_height()

        x = px + (pw - tw) // 2
        y = py + (ph - th) // 2

        toast.geometry(f"{tw}x{th}+{x}+{y}")

        # duration 이후 자동 제거
        toast.after(duration, toast.destroy)
