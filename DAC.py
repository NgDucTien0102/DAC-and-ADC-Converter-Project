import tkinter as tk
from tkinter import ttk


class DACApp:
    BITS_MIN = 1
    BITS_MAX = 64

    def __init__(self):
        # ---- Root window ----
        self.root = tk.Tk()
        self.root.title("DAC (Python)")
        self.root.geometry("600x360")
        self.root.minsize(600, 360)

        # ---- Styles (status colors) ----
        self.style = ttk.Style(self.root)
        self.style.configure("Status.Info.TLabel", foreground="#444")
        self.style.configure("Status.Ok.TLabel", foreground="#0b6e0b")
        self.style.configure("Status.Err.TLabel", foreground="#b00020")

        # ---- Variables ----
        self.bits_var = tk.StringVar(value="8")
        self.code_var = tk.StringVar()
        self.r_var = tk.StringVar(value="1.0")
        self.mode_var = tk.StringVar(value="unipolar")

        self.status_var = tk.StringVar(value="Nhập số bit và mã nhị phân rồi nhấn Convert (hoặc Enter).")

        self.out_dec_var = tk.StringVar(value="-")
        self.out_hex_var = tk.StringVar(value="-")
        self.out_q_var = tk.StringVar(value="-")
        self.out_x_var = tk.StringVar(value="-")
        self.out_range_var = tk.StringVar(value="-")

        # ---- Build UI ----
        self._build_ui()

        # ---- Traces / binds ----
        self.bits_var.trace_add("write", self.on_bits_change)
        self.code_var.trace_add("write", self.on_code_change)
        self.root.bind("<Return>", self.on_convert)

        # ---- Init default code by bits ----
        self._apply_bits_default()

        self.bits_entry.focus_set()
        self.bits_entry.selection_range(0, tk.END)

    # =========================
    # Parsing / Math
    # =========================
    @classmethod
    def parse_bits(cls, text: str):
        s = text.strip()
        if s == "":
            return None, "Vui lòng nhập số bit."
        try:
            b = int(s)
        except Exception:
            return None, "Số bit phải là số nguyên (ví dụ: 8, 10, 11...)."
        if not (cls.BITS_MIN <= b <= cls.BITS_MAX):
            return None, f"Số bit phải nằm trong [{cls.BITS_MIN}..{cls.BITS_MAX}]."
        return b, ""

    @staticmethod
    def parse_binary(text: str, bits: int):
        s = text.strip().replace(" ", "")
        if s.startswith("0b") or s.startswith("0B"):
            s = s[2:]

        errors = []

        # length errors
        if len(s) != bits:
            if len(s) < bits:
                errors.append(f"Thiếu bit: độ dài {len(s)}/{bits} (thiếu {bits - len(s)} bit).")
            else:
                errors.append(f"Dư bit: độ dài {len(s)}/{bits} (dư {len(s) - bits} bit).")

        # invalid chars
        invalid = sorted(set(c for c in s if c not in "01"))
        if invalid:
            errors.append("Sai giá trị nhập: chỉ được 0/1. Ký tự sai: " + ", ".join(invalid))

        if errors:
            return None, "Có lỗi:\n- " + "\n- ".join(errors)

        return int(s, 2), ""

    @staticmethod
    def dac_output(m: int, R: float, bits: int, mode: str):
        Q = R / (1 << bits)
        mode = mode.lower()

        if mode == "unipolar":
            x = Q * m
            rng = f"0 ≤ x < {R:g}"
        elif mode == "offset":
            x = Q * m - 0.5 * R
            rng = f"-{R/2:g} ≤ x < {R/2:g}"
        elif mode == "twos":
            s = m if m < (1 << (bits - 1)) else m - (1 << bits)
            x = Q * s
            smin = -(1 << (bits - 1))
            smax = (1 << (bits - 1)) - 1
            rng = f"x = Q·s, s ∈ [{smin}..{smax}]"
        else:
            raise ValueError("Unknown mode")

        return Q, x, rng

    # =========================
    # UI helpers
    # =========================
    def set_status(self, msg: str, kind: str = "info", clear_output: bool = False):
        self.status_var.set(msg)
        if kind == "ok":
            self.status_label.configure(style="Status.Ok.TLabel")
        elif kind == "err":
            self.status_label.configure(style="Status.Err.TLabel")
        else:
            self.status_label.configure(style="Status.Info.TLabel")

        if clear_output:
            self.out_dec_var.set("-")
            self.out_hex_var.set("-")
            self.out_q_var.set("-")
            self.out_x_var.set("-")
            self.out_range_var.set("-")

    def _apply_bits_default(self):
        """Update label + set default code '000..0' based on current bits_var (if valid)."""
        b, err = self.parse_bits(self.bits_var.get())
        if b is None:
            self.code_label.configure(text="Binary code (? -bit):")
            self.set_status(err, kind="err")
            return

        self.code_label.configure(text=f"Binary code ({b}-bit):")
        self.code_var.set("0" * b)
        self.code_entry.focus_set()
        self.code_entry.selection_range(0, tk.END)
        self.set_status(f"Đã chọn {b} bit. Nhập mã nhị phân rồi nhấn Convert (hoặc Enter).", kind="info")

    # =========================
    # Event handlers
    # =========================
    def on_bits_change(self, *args):
        # chỉ update default code khi bits hợp lệ
        b, err = self.parse_bits(self.bits_var.get())
        if b is None:
            self.set_status(err, kind="err")  # không clear output để đỡ “giật”
            return

        self.code_label.configure(text=f"Binary code ({b}-bit):")
        self.code_var.set("0" * b)
        self.code_entry.focus_set()
        self.code_entry.selection_range(0, tk.END)
        self.set_status(f"Đã chọn {b} bit. Nhập mã nhị phân rồi nhấn Convert (hoặc Enter).", kind="info")

    def on_code_change(self, *args):
        b, berr = self.parse_bits(self.bits_var.get())
        if b is None:
            self.set_status(berr, kind="err")
            return

        text = self.code_var.get()
        if not text.strip():
            self.set_status("Nhập mã nhị phân rồi nhấn Convert (hoặc Enter).", kind="info")
            return

        m, err = self.parse_binary(text, b)
        if m is None:
            self.set_status(err, kind="err")
        else:
            self.set_status("Hợp lệ ✓ (nhấn Convert hoặc Enter)", kind="ok")

    def on_convert(self, event=None):
        # bits
        b, berr = self.parse_bits(self.bits_var.get())
        if b is None:
            self.set_status(berr, kind="err", clear_output=True)
            self.bits_entry.focus_set()
            self.bits_entry.selection_range(0, tk.END)
            return

        # code
        m, err = self.parse_binary(self.code_var.get(), b)
        if m is None:
            self.set_status(err, kind="err", clear_output=True)
            self.code_entry.focus_set()
            self.code_entry.selection_range(0, tk.END)
            return

        # R
        try:
            R = float(self.r_var.get())
            if R <= 0:
                raise ValueError
        except Exception:
            self.set_status("R (Full-scale range) phải là số dương. Ví dụ: 1.0 hoặc 5.0",
                            kind="err", clear_output=True)
            self.r_entry.focus_set()
            self.r_entry.selection_range(0, tk.END)
            return

        # compute
        Q, x, rng = self.dac_output(m, R, b, self.mode_var.get())

        # output
        self.set_status("Hợp lệ ✓", kind="ok")
        self.out_dec_var.set(str(m))

        hex_digits = (b + 3) // 4  # đủ số nibble
        self.out_hex_var.set("0x" + format(m, f"0{hex_digits}X"))

        self.out_q_var.set(f"{Q:.10g}")
        self.out_x_var.set(f"{x:.10g}")
        self.out_range_var.set(rng)

    # =========================
    # UI build
    # =========================
    def _build_ui(self):
        main = ttk.Frame(self.root, padding=14)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="DAC", font=("Segoe UI", 16, "bold")).pack(anchor="w")

        ttk.Label(
            main,
            text="Nhập số bit (1..64) và mã nhị phân đúng số bit. Sai định dạng sẽ báo lỗi.",
        ).pack(anchor="w", pady=(2, 12))

        # Input frame
        inp = ttk.LabelFrame(main, text="Input", padding=12)
        inp.pack(fill="x")

        # Row 0: Bits + Binary
        ttk.Label(inp, text="Bits (1..64):").grid(row=0, column=0, sticky="w")
        self.bits_entry = ttk.Entry(inp, textvariable=self.bits_var, width=8)
        self.bits_entry.grid(row=0, column=1, sticky="w", padx=(8, 18))

        self.code_label = ttk.Label(inp, text="Binary code (8-bit):")
        self.code_label.grid(row=0, column=2, sticky="w")

        self.code_entry = ttk.Entry(inp, textvariable=self.code_var, width=40)
        self.code_entry.grid(row=0, column=3, sticky="w", padx=(8, 0))

        # Row 1: R + Mode
        ttk.Label(inp, text="R (Full-scale range):").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.r_entry = ttk.Entry(inp, textvariable=self.r_var, width=10)
        self.r_entry.grid(row=1, column=1, sticky="w", padx=(8, 18), pady=(10, 0))

        ttk.Label(inp, text="Mode:").grid(row=1, column=2, sticky="w", pady=(10, 0))
        self.mode_box = ttk.Combobox(
            inp,
            textvariable=self.mode_var,
            values=["unipolar", "offset", "twos"],
            state="readonly",
            width=18,
        )
        self.mode_box.grid(row=1, column=3, sticky="w", padx=(8, 0), pady=(10, 0))

        # Row 2: Convert
        self.convert_btn = ttk.Button(inp, text="Convert", command=self.on_convert)
        self.convert_btn.grid(row=2, column=3, sticky="e", pady=(10, 0))

        inp.columnconfigure(3, weight=1)

        # Status
        self.status_label = ttk.Label(main, textvariable=self.status_var, style="Status.Info.TLabel")
        self.status_label.pack(anchor="w", pady=(10, 8))

        # Output frame
        out = ttk.LabelFrame(main, text="Output panel", padding=12)
        out.pack(fill="both", expand=True)

        def out_row(label, var, r):
            ttk.Label(out, text=label).grid(row=r, column=0, sticky="w", pady=3)
            ttk.Label(out, textvariable=var, font=("Consolas", 11)).grid(row=r, column=1, sticky="w", pady=3)

        out_row("Decimal (m):", self.out_dec_var, 0)
        out_row("Hex:", self.out_hex_var, 1)
        out_row("Step Q = R / 2^bits:", self.out_q_var, 2)
        out_row("Analog output x_Q:", self.out_x_var, 3)
        out_row("Range:", self.out_range_var, 4)

        out.columnconfigure(1, weight=1)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    DACApp().run()