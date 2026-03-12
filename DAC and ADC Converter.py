import tkinter as tk
from tkinter import ttk, filedialog

try:
    from openpyxl import Workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    Workbook = None
    OPENPYXL_AVAILABLE = False


class DACFrame(ttk.Frame):
    BITS_MIN = 1
    BITS_MAX = 64
    EXPORT_BITS_MAX = 16

    MODE_UNIPOLAR = "Đơn cực"
    MODE_BIPOLAR = "Lưỡng cực"
    MODE_TWOS = "Bù 2"

    def __init__(self, master, back_callback):
        super().__init__(master, padding=12)
        self.back_callback = back_callback

        self.style = ttk.Style()
        self.style.configure("Status.Info.TLabel", foreground="#444")
        self.style.configure("Status.Ok.TLabel", foreground="#0b6e0b")
        self.style.configure("Status.Err.TLabel", foreground="#b00020")

        self.bits_var = tk.StringVar(value="8")
        self.code_var = tk.StringVar()
        self.r_var = tk.StringVar(value="1.0")
        self.mode_var = tk.StringVar(value=self.MODE_UNIPOLAR)

        self.status_var = tk.StringVar(value="Nhập số bit, mã nhị phân và R rồi nhấn Convert.")
        self.out_dec_var = tk.StringVar(value="-")
        self.out_hex_var = tk.StringVar(value="-")
        self.out_q_var = tk.StringVar(value="-")
        self.out_x_var = tk.StringVar(value="-")
        self.out_range_var = tk.StringVar(value="-")

        self._build_ui()

        self.bits_var.trace_add("write", self.on_bits_change)
        self.code_var.trace_add("write", self.on_code_change)

        self._apply_bits_default()

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
    def parse_positive_float(text: str, name: str):
        s = text.strip()
        if s == "":
            return None, f"Vui lòng nhập {name}."
        try:
            value = float(s)
        except Exception:
            return None, f"{name} phải là số."
        if value <= 0:
            return None, f"{name} phải là số dương."
        return value, ""

    @staticmethod
    def validate_binary(text: str, bits=None):
        s = text.strip().replace(" ", "")
        if s.startswith("0b") or s.startswith("0B"):
            s = s[2:]

        errors = []

        if s == "":
            errors.append("Vui lòng nhập mã nhị phân.")
            return None, errors

        invalid = sorted(set(c for c in s if c not in "01"))
        if invalid:
            errors.append("Sai giá trị nhập: chỉ được 0/1. Ký tự sai: " + ", ".join(invalid))

        if bits is not None:
            if len(s) != bits:
                if len(s) < bits:
                    errors.append(f"Thiếu bit: độ dài {len(s)}/{bits} (thiếu {bits - len(s)} bit).")
                else:
                    errors.append(f"Dư bit: độ dài {len(s)}/{bits} (dư {len(s) - bits} bit).")

        if errors:
            return None, errors

        return int(s, 2), []

    def dac_output(self, m: int, R: float, bits: int, mode: str):
        Q = R / (1 << bits)

        if mode == self.MODE_UNIPOLAR:
            x = Q * m
            rng = f"0 ≤ x < {R:g}"

        elif mode == self.MODE_BIPOLAR:
            x = Q * m - 0.5 * R
            rng = f"-{R/2:g} ≤ x < {R/2:g}"

        elif mode == self.MODE_TWOS:
            s = m if m < (1 << (bits - 1)) else m - (1 << bits)
            x = Q * s
            smin = -(1 << (bits - 1))
            smax = (1 << (bits - 1)) - 1
            rng = f"x = Q·s, s ∈ [{smin}..{smax}]"

        else:
            raise ValueError("Mode không hợp lệ.")

        return Q, x, rng

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
        b, err = self.parse_bits(self.bits_var.get())
        if b is None:
            self.code_label.configure(text="Mã nhị phân (? bit):")
            self.set_status(err, kind="err")
            return

        self.code_label.configure(text=f"Mã nhị phân ({b} bit):")
        self.code_var.set("0" * b)
        self.set_status(f"Đã chọn {b} bit. Nhập mã nhị phân rồi nhấn Convert.", kind="info")

    def on_bits_change(self, *args):
        b, err = self.parse_bits(self.bits_var.get())
        if b is None:
            self.set_status(err, kind="err")
            return

        self.code_label.configure(text=f"Mã nhị phân ({b} bit):")
        self.code_var.set("0" * b)
        self.set_status(f"Đã chọn {b} bit. Nhập mã nhị phân rồi nhấn Convert.", kind="info")

    def on_code_change(self, *args):
        b, berr = self.parse_bits(self.bits_var.get())
        if b is None:
            self.set_status(berr, kind="err")
            return

        text = self.code_var.get()
        if not text.strip():
            self.set_status("Nhập mã nhị phân rồi nhấn Convert.", kind="info")
            return

        m, errors = self.validate_binary(text, b)
        if m is None:
            self.set_status("Có lỗi:\n- " + "\n- ".join(errors), kind="err")
        else:
            self.set_status("Hợp lệ ✓ (nhấn Convert hoặc Enter)", kind="ok")

    def on_convert(self, event=None):
        errors = []

        b, berr = self.parse_bits(self.bits_var.get())
        if b is None:
            errors.append(berr)

        m = None
        m_raw, bin_errors = self.validate_binary(self.code_var.get(), b if b is not None else None)
        if bin_errors:
            errors.extend(bin_errors)
        else:
            m = m_raw

        R, rerr = self.parse_positive_float(self.r_var.get(), "R (Full-scale range)")
        if R is None:
            errors.append(rerr)

        if errors:
            self.set_status("Có lỗi:\n- " + "\n- ".join(errors), kind="err", clear_output=True)
            return

        Q, x, rng = self.dac_output(m, R, b, self.mode_var.get())

        self.set_status("Hợp lệ ✓", kind="ok")
        self.out_dec_var.set(str(m))

        hex_digits = (b + 3) // 4
        self.out_hex_var.set("0x" + format(m, f"0{hex_digits}X"))
        self.out_q_var.set(f"{Q:.10g}")
        self.out_x_var.set(f"{x:.10g}")
        self.out_range_var.set(rng)

    def generate_excel(self, bits, R, filename):
        wb = Workbook()
        modes = [self.MODE_UNIPOLAR, self.MODE_BIPOLAR, self.MODE_TWOS]

        for i, mode in enumerate(modes):
            if i == 0:
                ws = wb.active
                ws.title = mode
            else:
                ws = wb.create_sheet(mode)

            if mode == self.MODE_TWOS:
                ws.append(["Giá trị lượng tử", "Giá trị thập phân (m)", "Giá trị có dấu (s)", "Q", "Giá trị analog"])
            else:
                ws.append(["Giá trị lượng tử", "Giá trị thập phân (m)", "Q", "Giá trị analog"])

            Q = R / (1 << bits)

            for m in range(1 << bits):
                binary = format(m, f"0{bits}b")

                if mode == self.MODE_UNIPOLAR:
                    x = Q * m
                    ws.append([binary, m, Q, x])

                elif mode == self.MODE_BIPOLAR:
                    x = Q * m - 0.5 * R
                    ws.append([binary, m, Q, x])

                elif mode == self.MODE_TWOS:
                    s = m if m < (1 << (bits - 1)) else m - (1 << bits)
                    x = Q * s
                    ws.append([binary, m, s, Q, x])

        wb.save(filename)

    def export_excel(self):
        if not OPENPYXL_AVAILABLE:
            self.set_status(
                "Chưa cài openpyxl nên chưa thể xuất Excel. Cài bằng: pip install openpyxl",
                kind="err"
            )
            return

        b, berr = self.parse_bits(self.bits_var.get())
        if b is None:
            self.set_status(berr, kind="err")
            return

        if b > self.EXPORT_BITS_MAX:
            self.set_status(
                f"Xuất Excel chỉ hỗ trợ đến {self.EXPORT_BITS_MAX} bit để tránh file quá lớn. "
                f"Phần Convert vẫn dùng được đến {self.BITS_MAX} bit.",
                kind="err"
            )
            return

        R, rerr = self.parse_positive_float(self.r_var.get(), "R (Full-scale range)")
        if R is None:
            self.set_status(rerr, kind="err")
            return

        filename = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".xlsx",
            filetypes=[("Excel file", "*.xlsx")]
        )
        if not filename:
            return

        self.generate_excel(b, R, filename)
        self.set_status("Đã tạo file Excel DAC thành công ✓", kind="ok")

    def _build_ui(self):
        top_bar = ttk.Frame(self)
        top_bar.pack(fill="x", pady=(0, 10))

        ttk.Button(top_bar, text="Thoát", command=self.back_callback, width=12).pack(side="left")
        ttk.Label(top_bar, text="DAC", font=("Segoe UI", 16, "bold")).pack(side="left", padx=(12, 0))

        ttk.Label(
            self,
            text="Hỗ trợ Convert đến 64 bit. Xuất Excel nên dùng tối đa 16 bit để tránh file quá lớn."
        ).pack(anchor="w", pady=(0, 10))

        inp = ttk.LabelFrame(self, text="Thông tin vào", padding=12)
        inp.pack(fill="x")

        ttk.Label(inp, text="Bits (1..64):").grid(row=0, column=0, sticky="w")
        self.bits_entry = ttk.Entry(inp, textvariable=self.bits_var, width=8)
        self.bits_entry.grid(row=0, column=1, sticky="w", padx=(8, 18))

        self.code_label = ttk.Label(inp, text="Mã nhị phân (8 bit):")
        self.code_label.grid(row=0, column=2, sticky="w")

        self.code_entry = ttk.Entry(inp, textvariable=self.code_var, width=40)
        self.code_entry.grid(row=0, column=3, sticky="w", padx=(8, 0))

        ttk.Label(inp, text="R (Full-scale range):").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.r_entry = ttk.Entry(inp, textvariable=self.r_var, width=10)
        self.r_entry.grid(row=1, column=1, sticky="w", padx=(8, 18), pady=(10, 0))

        ttk.Label(inp, text="Mode:").grid(row=1, column=2, sticky="w", pady=(10, 0))
        self.mode_box = ttk.Combobox(
            inp,
            textvariable=self.mode_var,
            values=[self.MODE_UNIPOLAR, self.MODE_BIPOLAR, self.MODE_TWOS],
            state="readonly",
            width=18,
        )
        self.mode_box.grid(row=1, column=3, sticky="w", padx=(8, 0), pady=(10, 0))

        button_row = ttk.Frame(inp)
        button_row.grid(row=2, column=0, columnspan=4, sticky="e", pady=(12, 0))

        self.export_btn = ttk.Button(button_row, text="Export Excel", command=self.export_excel)
        self.export_btn.pack(side="left", padx=(0, 8))

        self.convert_btn = ttk.Button(button_row, text="Convert", command=self.on_convert)
        self.convert_btn.pack(side="left")

        self.status_label = ttk.Label(self, textvariable=self.status_var, style="Status.Info.TLabel")
        self.status_label.pack(anchor="w", pady=(10, 8))

        out = ttk.LabelFrame(self, text="Kết quả", padding=12)
        out.pack(fill="both", expand=True)

        def out_row(label, var, r):
            ttk.Label(out, text=label).grid(row=r, column=0, sticky="w", pady=3)
            ttk.Label(out, textvariable=var, font=("Consolas", 11)).grid(row=r, column=1, sticky="w", pady=3)

        out_row("Giá trị thập phân (m):", self.out_dec_var, 0)
        out_row("Hex:", self.out_hex_var, 1)
        out_row("Bước lượng tử Q = R / 2^bits:", self.out_q_var, 2)
        out_row("Giá trị analog x_Q:", self.out_x_var, 3)
        out_row("Miền giá trị:", self.out_range_var, 4)


class ADCFrame(ttk.Frame):
    BITS_MIN = 1
    BITS_MAX = 64

    MODE_UNIPOLAR = "Đơn cực"
    MODE_BIPOLAR = "Lưỡng cực"
    MODE_TWOS = "Bù 2"

    def __init__(self, master, back_callback):
        super().__init__(master, padding=12)
        self.back_callback = back_callback

        self.style = ttk.Style()
        self.style.configure("Status.Info.TLabel", foreground="#444")
        self.style.configure("Status.Ok.TLabel", foreground="#0b6e0b")
        self.style.configure("Status.Err.TLabel", foreground="#b00020")

        self.bits_var = tk.StringVar(value="8")
        self.x_var = tk.StringVar(value="0.0")
        self.r_var = tk.StringVar(value="1.0")
        self.mode_var = tk.StringVar(value=self.MODE_UNIPOLAR)

        self.status_var = tk.StringVar(value="Nhập số bit, x và R rồi nhấn Convert.")
        self.range_hint_var = tk.StringVar(value="Miền x hợp lệ: 0 ≤ x ≤ 1")

        self.out_bin_var = tk.StringVar(value="-")
        self.out_dec_var = tk.StringVar(value="-")
        self.out_hex_var = tk.StringVar(value="-")
        self.out_q_var = tk.StringVar(value="-")
        self.out_xq_var = tk.StringVar(value="-")
        self.out_signed_var = tk.StringVar(value="-")
        self.out_range_var = tk.StringVar(value="-")

        self._build_ui()

        self.mode_var.trace_add("write", self.on_mode_or_r_change)
        self.r_var.trace_add("write", self.on_mode_or_r_change)

        self.update_range_hint()

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
    def parse_float(text: str, name: str):
        s = text.strip()
        if s == "":
            return None, f"Vui lòng nhập {name}."
        try:
            value = float(s)
        except Exception:
            return None, f"{name} phải là số."
        return value, ""

    @staticmethod
    def parse_positive_float(text: str, name: str):
        s = text.strip()
        if s == "":
            return None, f"Vui lòng nhập {name}."
        try:
            value = float(s)
        except Exception:
            return None, f"{name} phải là số."
        if value <= 0:
            return None, f"{name} phải là số dương."
        return value, ""

    @staticmethod
    def clamp(v, vmin, vmax):
        return max(vmin, min(v, vmax))

    def get_input_range_text(self, R, mode):
        if mode == self.MODE_UNIPOLAR:
            return f"Miền x hợp lệ: 0 ≤ x ≤ {R:g}"
        elif mode == self.MODE_BIPOLAR:
            return f"Miền x hợp lệ: -{R/2:g} ≤ x ≤ {R/2:g}"
        elif mode == self.MODE_TWOS:
            return f"Miền x hợp lệ: -{R/2:g} ≤ x ≤ {R/2:g}"
        return "Miền x hợp lệ: -"

    def update_range_hint(self):
        R, err = self.parse_positive_float(self.r_var.get(), "R")
        if R is None:
            self.range_hint_var.set("Miền x hợp lệ: chưa xác định vì R chưa hợp lệ.")
            return
        self.range_hint_var.set(self.get_input_range_text(R, self.mode_var.get()))

    def on_mode_or_r_change(self, *args):
        self.update_range_hint()

    def adc_quantize(self, x, R, bits, mode):
        Q = R / (1 << bits)
        n = 1 << bits

        if mode == self.MODE_UNIPOLAR:
            if not (0 <= x <= R):
                return None, None, None, None, None, f"x phải nằm trong khoảng 0 ≤ x ≤ {R:g}"

            m = round(x / Q)
            m = self.clamp(m, 0, n - 1)
            xq = Q * m
            signed_str = "-"
            rng = f"0 ≤ x ≤ {R:g}"

        elif mode == self.MODE_BIPOLAR:
            xmin = -R / 2
            xmax = R / 2

            if not (xmin <= x <= xmax):
                return None, None, None, None, None, f"x phải nằm trong khoảng {xmin:g} ≤ x ≤ {xmax:g}"

            m = round((x + R / 2) / Q)
            m = self.clamp(m, 0, n - 1)
            xq = Q * m - R / 2
            signed_str = "-"
            rng = f"{xmin:g} ≤ x ≤ {xmax:g}"

        elif mode == self.MODE_TWOS:
            smin = -(1 << (bits - 1))
            smax = (1 << (bits - 1)) - 1
            xmin = -R / 2
            xmax = R / 2

            if not (xmin <= x <= xmax):
                return None, None, None, None, None, f"x phải nằm trong khoảng {xmin:g} ≤ x ≤ {xmax:g}"

            s = round(x / Q)
            s = self.clamp(s, smin, smax)
            m = s if s >= 0 else s + n
            xq = Q * s
            signed_str = str(s)
            rng = f"x = Q·s, s ∈ [{smin}..{smax}]"

        else:
            return None, None, None, None, None, "Mode không hợp lệ."

        return m, Q, xq, signed_str, rng, ""

    def set_status(self, msg: str, kind: str = "info", clear_output: bool = False):
        self.status_var.set(msg)

        if kind == "ok":
            self.status_label.configure(style="Status.Ok.TLabel")
        elif kind == "err":
            self.status_label.configure(style="Status.Err.TLabel")
        else:
            self.status_label.configure(style="Status.Info.TLabel")

        if clear_output:
            self.out_bin_var.set("-")
            self.out_dec_var.set("-")
            self.out_hex_var.set("-")
            self.out_q_var.set("-")
            self.out_xq_var.set("-")
            self.out_signed_var.set("-")
            self.out_range_var.set("-")

    def on_convert(self, event=None):
        errors = []

        b, berr = self.parse_bits(self.bits_var.get())
        if b is None:
            errors.append(berr)

        x, xerr = self.parse_float(self.x_var.get(), "x")
        if x is None:
            errors.append(xerr)

        R, rerr = self.parse_positive_float(self.r_var.get(), "R")
        if R is None:
            errors.append(rerr)

        if errors:
            self.set_status("Có lỗi:\n- " + "\n- ".join(errors), kind="err", clear_output=True)
            return

        m, Q, xq, signed_str, rng, quant_err = self.adc_quantize(x, R, b, self.mode_var.get())
        if m is None:
            self.set_status(quant_err, kind="err", clear_output=True)
            return

        self.out_bin_var.set(format(m, f"0{b}b"))
        self.out_dec_var.set(str(m))

        hex_digits = (b + 3) // 4
        self.out_hex_var.set("0x" + format(m, f"0{hex_digits}X"))
        self.out_q_var.set(f"{Q:.10g}")
        self.out_xq_var.set(f"{xq:.10g}")
        self.out_signed_var.set(signed_str)
        self.out_range_var.set(rng)

        self.set_status("Hợp lệ ✓", kind="ok")

    def _build_ui(self):
        top_bar = ttk.Frame(self)
        top_bar.pack(fill="x", pady=(0, 10))

        ttk.Button(top_bar, text="Thoát", command=self.back_callback, width=12).pack(side="left")
        ttk.Label(top_bar, text="ADC", font=("Segoe UI", 16, "bold")).pack(side="left", padx=(12, 0))

        ttk.Label(
            self,
            text="Hỗ trợ Convert đến 64 bit. Miền x hợp lệ sẽ đổi theo mode và giá trị R."
        ).pack(anchor="w", pady=(0, 10))

        inp = ttk.LabelFrame(self, text="Thông tin vào", padding=12)
        inp.pack(fill="x")

        ttk.Label(inp, text="Bits (1..64):").grid(row=0, column=0, sticky="w")
        self.bits_entry = ttk.Entry(inp, textvariable=self.bits_var, width=8)
        self.bits_entry.grid(row=0, column=1, sticky="w", padx=(8, 18))

        ttk.Label(inp, text="Giá trị analog x:").grid(row=0, column=2, sticky="w")
        self.x_entry = ttk.Entry(inp, textvariable=self.x_var, width=20)
        self.x_entry.grid(row=0, column=3, sticky="w", padx=(8, 0))

        ttk.Label(inp, text="R (Full-scale range):").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.r_entry = ttk.Entry(inp, textvariable=self.r_var, width=10)
        self.r_entry.grid(row=1, column=1, sticky="w", padx=(8, 18), pady=(10, 0))

        ttk.Label(inp, text="Mode:").grid(row=1, column=2, sticky="w", pady=(10, 0))
        self.mode_box = ttk.Combobox(
            inp,
            textvariable=self.mode_var,
            values=[self.MODE_UNIPOLAR, self.MODE_BIPOLAR, self.MODE_TWOS],
            state="readonly",
            width=18,
        )
        self.mode_box.grid(row=1, column=3, sticky="w", padx=(8, 0), pady=(10, 0))

        self.range_hint_label = ttk.Label(
            inp,
            textvariable=self.range_hint_var,
            style="Status.Info.TLabel"
        )
        self.range_hint_label.grid(row=2, column=0, columnspan=4, sticky="w", pady=(10, 0))

        button_row = ttk.Frame(inp)
        button_row.grid(row=3, column=0, columnspan=4, sticky="e", pady=(12, 0))
        ttk.Button(button_row, text="Convert", command=self.on_convert).pack(side="left")

        self.status_label = ttk.Label(self, textvariable=self.status_var, style="Status.Info.TLabel")
        self.status_label.pack(anchor="w", pady=(10, 8))

        out = ttk.LabelFrame(self, text="Kết quả", padding=12)
        out.pack(fill="both", expand=True)

        def out_row(label, var, r):
            ttk.Label(out, text=label).grid(row=r, column=0, sticky="w", pady=3)
            ttk.Label(out, textvariable=var, font=("Consolas", 11)).grid(row=r, column=1, sticky="w", pady=3)

        out_row("Mã nhị phân:", self.out_bin_var, 0)
        out_row("Giá trị thập phân (m):", self.out_dec_var, 1)
        out_row("Hex:", self.out_hex_var, 2)
        out_row("Bước lượng tử Q = R / 2^bits:", self.out_q_var, 3)
        out_row("Giá trị lượng tử hóa x_Q:", self.out_xq_var, 4)
        out_row("Giá trị có dấu s:", self.out_signed_var, 5)
        out_row("Miền giá trị:", self.out_range_var, 6)


class HomeFrame(ttk.Frame):
    def __init__(self, master, open_dac_callback, open_adc_callback):
        super().__init__(master, padding=20)
        self.open_dac_callback = open_dac_callback
        self.open_adc_callback = open_adc_callback
        self._build_ui()

    def _build_ui(self):
        ttk.Label(
            self,
            text="Xin vui lòng chọn chức năng",
            font=("Segoe UI", 18, "bold")
        ).pack(pady=(40, 24))

        button_frame = ttk.Frame(self)
        button_frame.pack(pady=(0, 14))

        ttk.Button(button_frame, text="DAC", command=self.open_dac_callback, width=18).grid(row=0, column=0, padx=12)
        ttk.Button(button_frame, text="ADC", command=self.open_adc_callback, width=18).grid(row=0, column=1, padx=12)

class MainApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ADC And DAC Converter")
        self.root.geometry("860x600")
        self.root.minsize(860, 600)

        self.home_frame = HomeFrame(self.root, self.show_dac, self.show_adc)
        self.dac_frame = DACFrame(self.root, self.show_home)
        self.adc_frame = ADCFrame(self.root, self.show_home)

        self.current_frame = None
        self.show_home()

        self.root.bind("<Return>", self.on_enter_key)

    def hide_all_frames(self):
        self.home_frame.pack_forget()
        self.dac_frame.pack_forget()
        self.adc_frame.pack_forget()

    def show_home(self):
        self.hide_all_frames()
        self.home_frame.pack(fill="both", expand=True)
        self.current_frame = "home"

    def show_dac(self):
        self.hide_all_frames()
        self.dac_frame.pack(fill="both", expand=True)
        self.current_frame = "dac"
        self.dac_frame.bits_entry.focus_set()

    def show_adc(self):
        self.hide_all_frames()
        self.adc_frame.pack(fill="both", expand=True)
        self.current_frame = "adc"
        self.adc_frame.bits_entry.focus_set()

    def on_enter_key(self, event=None):
        if self.current_frame == "dac":
            self.dac_frame.on_convert()
        elif self.current_frame == "adc":
            self.adc_frame.on_convert()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    MainApp().run()