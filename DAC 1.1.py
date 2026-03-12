import tkinter as tk
from tkinter import ttk, filedialog
from openpyxl import Workbook


class DACApp:
    BITS_MIN = 1
    BITS_MAX = 16   # nên giới hạn để tránh Excel quá lớn

    def __init__(self):

        self.root = tk.Tk()
        self.root.title("DAC Application")
        self.root.geometry("600x360")

        self.style = ttk.Style(self.root)
        self.style.configure("Status.Info.TLabel", foreground="#444")
        self.style.configure("Status.Ok.TLabel", foreground="#0b6e0b")
        self.style.configure("Status.Err.TLabel", foreground="#b00020")

        self.bits_var = tk.StringVar(value="8")
        self.code_var = tk.StringVar()
        self.r_var = tk.StringVar(value="1.0")
        self.mode_var = tk.StringVar(value="unipolar")

        self.status_var = tk.StringVar()

        self.out_dec_var = tk.StringVar(value="-")
        self.out_hex_var = tk.StringVar(value="-")
        self.out_q_var = tk.StringVar(value="-")
        self.out_x_var = tk.StringVar(value="-")
        self.out_range_var = tk.StringVar(value="-")

        self._build_ui()

        self.bits_var.trace_add("write", self.on_bits_change)
        self.code_var.trace_add("write", self.on_code_change)

        self.root.bind("<Return>", self.on_convert)

        self._apply_bits_default()

    # =========================
    # Parsing
    # =========================

    def parse_bits(self, text):

        try:
            b = int(text)
        except:
            return None, "Bits phải là số nguyên"

        if b < self.BITS_MIN or b > self.BITS_MAX:
            return None, f"Bits phải trong khoảng {self.BITS_MIN}-{self.BITS_MAX}"

        return b, ""

    def parse_binary(self, text, bits):

        s = text.strip()

        if len(s) != bits:
            return None, "Sai số bit"

        if any(c not in "01" for c in s):
            return None, "Binary chỉ gồm 0 và 1"

        return int(s, 2), ""

    # =========================
    # DAC math
    # =========================

    def dac_output(self, m, R, bits, mode):

        Q = R / (1 << bits)

        if mode == "unipolar":
            x = Q * m
            rng = f"0 ≤ x < {R}"

        elif mode == "offset":
            x = Q * m - R / 2
            rng = f"-{R/2} ≤ x < {R/2}"

        elif mode == "twos":

            s = m if m < (1 << (bits - 1)) else m - (1 << bits)
            x = Q * s
            rng = "Two's complement"

        return Q, x, rng

    # =========================
    # Excel generator
    # =========================

    def generate_excel(self, bits, R, filename):

        wb = Workbook()

        modes = ["unipolar", "offset", "twos"]

        for i, mode in enumerate(modes):

            if i == 0:
                ws = wb.active
                ws.title = mode
            else:
                ws = wb.create_sheet(mode)

            if mode == "twos":
                ws.append(["Binary", "Decimal (m)", "Signed s", "Q", "Analog Output"])
            else:
                ws.append(["Binary", "Decimal (m)", "Q", "Analog Output"])

            Q = R / (1 << bits)

            for m in range(1 << bits):

                binary = format(m, f"0{bits}b")

                if mode == "unipolar":

                    x = Q * m
                    ws.append([binary, m, Q, x])

                elif mode == "offset":

                    x = Q * m - R / 2
                    ws.append([binary, m, Q, x])

                elif mode == "twos":

                    s = m if m < (1 << (bits - 1)) else m - (1 << bits)
                    x = Q * s
                    ws.append([binary, m, s, Q, x])

        wb.save(filename)

    # =========================
    # Export button
    # =========================

    def export_excel(self):

        b, err = self.parse_bits(self.bits_var.get())

        if b is None:
            self.set_status(err, "err")
            return

        try:
            R = float(self.r_var.get())
        except:
            self.set_status("R không hợp lệ", "err")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel file", "*.xlsx")]
        )

        if not filename:
            return

        self.generate_excel(b, R, filename)

        self.set_status("Đã tạo file Excel DAC ✓", "ok")

    # =========================
    # Events
    # =========================

    def on_bits_change(self, *args):

        b, err = self.parse_bits(self.bits_var.get())

        if b is None:
            self.set_status(err, "err")
            return

        self.code_var.set("0" * b)

    def on_code_change(self, *args):

        b, err = self.parse_bits(self.bits_var.get())

        if b is None:
            return

        m, err = self.parse_binary(self.code_var.get(), b)

        if m is None:
            self.set_status(err, "err")
        else:
            self.set_status("Binary hợp lệ", "ok")

    def on_convert(self, event=None):

        b, err = self.parse_bits(self.bits_var.get())

        if b is None:
            self.set_status(err, "err")
            return

        m, err = self.parse_binary(self.code_var.get(), b)

        if m is None:
            self.set_status(err, "err")
            return

        R = float(self.r_var.get())

        Q, x, rng = self.dac_output(m, R, b, self.mode_var.get())

        self.out_dec_var.set(str(m))
        self.out_hex_var.set(hex(m))
        self.out_q_var.set(str(Q))
        self.out_x_var.set(str(x))
        self.out_range_var.set(rng)

        self.set_status("Convert thành công", "ok")

    # =========================
    # Status
    # =========================

    def set_status(self, msg, kind="info"):

        self.status_var.set(msg)

        if kind == "ok":
            self.status_label.configure(style="Status.Ok.TLabel")
        elif kind == "err":
            self.status_label.configure(style="Status.Err.TLabel")
        else:
            self.status_label.configure(style="Status.Info.TLabel")

    # =========================
    # UI
    # =========================

    def _apply_bits_default(self):

        b, _ = self.parse_bits(self.bits_var.get())

        if b:
            self.code_var.set("0" * b)

    def _build_ui(self):

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="DAC Tool", font=("Segoe UI", 16)).pack(anchor="w")

        inp = ttk.LabelFrame(main, text="Input", padding=10)
        inp.pack(fill="x")

        ttk.Label(inp, text="Bits").grid(row=0, column=0)

        self.bits_entry = ttk.Entry(inp, textvariable=self.bits_var, width=10)
        self.bits_entry.grid(row=0, column=1)

        ttk.Label(inp, text="Binary").grid(row=0, column=2)

        self.code_entry = ttk.Entry(inp, textvariable=self.code_var, width=30)
        self.code_entry.grid(row=0, column=3)

        ttk.Label(inp, text="R").grid(row=1, column=0)

        self.r_entry = ttk.Entry(inp, textvariable=self.r_var)
        self.r_entry.grid(row=1, column=1)

        ttk.Label(inp, text="Mode").grid(row=1, column=2)

        self.mode_box = ttk.Combobox(
            inp,
            textvariable=self.mode_var,
            values=["unipolar", "offset", "twos"],
            state="readonly"
        )

        self.mode_box.grid(row=1, column=3)

        ttk.Button(inp, text="Convert", command=self.on_convert).grid(row=2, column=3)

        ttk.Button(inp, text="Export Excel", command=self.export_excel).grid(row=2, column=2)

        self.status_label = ttk.Label(main, textvariable=self.status_var)
        self.status_label.pack(anchor="w", pady=5)

        out = ttk.LabelFrame(main, text="Output", padding=10)
        out.pack(fill="both", expand=True)

        ttk.Label(out, text="Decimal").grid(row=0, column=0)
        ttk.Label(out, textvariable=self.out_dec_var).grid(row=0, column=1)

        ttk.Label(out, text="Hex").grid(row=1, column=0)
        ttk.Label(out, textvariable=self.out_hex_var).grid(row=1, column=1)

        ttk.Label(out, text="Q").grid(row=2, column=0)
        ttk.Label(out, textvariable=self.out_q_var).grid(row=2, column=1)

        ttk.Label(out, text="Analog").grid(row=3, column=0)
        ttk.Label(out, textvariable=self.out_x_var).grid(row=3, column=1)

        ttk.Label(out, text="Range").grid(row=4, column=0)
        ttk.Label(out, textvariable=self.out_range_var).grid(row=4, column=1)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    DACApp().run()