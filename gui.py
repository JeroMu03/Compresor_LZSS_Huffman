import queue
import threading
import tkinter as tk

from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from compressor import compress_file
from decompressor import decompress_file


class CompresorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Compresor LZSS + Huffman")
        self.root.geometry("540x340")
        self.root.resizable(False, False)

        self.results = queue.Queue()
        self.busy = False

        container = ttk.Frame(root, padding=28)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="Compresor de archivos",
            font=("Segoe UI", 20, "bold"),
        ).pack(pady=(0, 6))

        ttk.Label(
            container,
            text="LZSS + Huffman estático · Sin pérdida",
        ).pack(pady=(0, 24))

        self.compress_button = ttk.Button(
            container,
            text="Comprimir archivo",
            command=self.select_compress,
        )
        self.compress_button.pack(fill="x", pady=6, ipady=8)

        self.decompress_button = ttk.Button(
            container,
            text="Descomprimir archivo",
            command=self.select_decompress,
        )
        self.decompress_button.pack(fill="x", pady=6, ipady=8)

        self.progress = ttk.Progressbar(
            container,
            mode="indeterminate",
        )
        self.progress.pack(fill="x", pady=(20, 10))

        self.status = tk.StringVar(value="Seleccioná una operación.")

        ttk.Label(
            container,
            textvariable=self.status,
            wraplength=470,
        ).pack()

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self.check_results)

    def select_compress(self):
        source = filedialog.askopenfilename(
            title="Seleccionar archivo para comprimir",
            filetypes=[("Todos los archivos", "*.*")],
        )

        if not source:
            return

        source_path = Path(source)

        destination = filedialog.asksaveasfilename(
            title="Guardar archivo comprimido",
            initialdir=str(source_path.parent),
            initialfile=source_path.name + ".lzh",
            defaultextension=".lzh",
            filetypes=[("Archivo del compresor", "*.lzh")],
        )

        if destination:
            self.start("compress", source, destination)

    def select_decompress(self):
        source = filedialog.askopenfilename(
            title="Seleccionar archivo comprimido",
            filetypes=[
                ("Archivo del compresor", "*.lzh"),
                ("Todos los archivos", "*.*"),
            ],
        )

        if not source:
            return

        source_path = Path(source)

        # foto.png.lzh → foto_recuperado.png
        original_name = Path(source_path.stem)
        suggested_name = (
            original_name.stem
            + "_recuperado"
            + original_name.suffix
        )

        destination = filedialog.asksaveasfilename(
            title="Guardar archivo descomprimido",
            initialdir=str(source_path.parent),
            initialfile=suggested_name,
            filetypes=[("Todos los archivos", "*.*")],
        )

        if destination:
            self.start("decompress", source, destination)

    def start(self, operation, source, destination):
        if Path(source).resolve() == Path(destination).resolve():
            messagebox.showerror(
                "Ruta inválida",
                "El archivo de salida debe ser distinto al de entrada.",
            )
            return

        self.busy = True
        self.compress_button.config(state="disabled")
        self.decompress_button.config(state="disabled")

        self.status.set(
            "Comprimiendo..."
            if operation == "compress"
            else "Descomprimiendo..."
        )

        self.progress.start(12)

        threading.Thread(
            target=self.process,
            args=(operation, source, destination),
            daemon=True,
        ).start()

    def process(self, operation, source, destination):
        # Este hilo realiza el trabajo sin bloquear la ventana.
        # Los cambios de interfaz se realizan en check_results().
        try:
            if operation == "compress":
                original_size = Path(source).stat().st_size

                compress_file(source, destination)

                final_size = Path(destination).stat().st_size

                detail = (
                    f"Original: {original_size:,} bytes\n"
                    f"Comprimido: {final_size:,} bytes"
                )

                if original_size:
                    reduction = (
                        1 - final_size / original_size
                    ) * 100

                    detail += f"\nReducción: {reduction:.2f}%"

            else:
                recovered_hash = decompress_file(
                    source,
                    destination,
                )

                final_size = Path(destination).stat().st_size

                detail = (
                    f"Recuperado: {final_size:,} bytes\n\n"
                    f"SHA-256 calculado:\n{recovered_hash}"
                )

            self.results.put(
                (
                    True,
                    f"{detail}\n\nGuardado en:\n{destination}",
                )
            )

        except Exception as error:
            self.results.put((False, str(error)))

    def check_results(self):
        try:
            success, message = self.results.get_nowait()

        except queue.Empty:
            pass

        else:
            self.busy = False
            self.progress.stop()

            self.compress_button.config(state="normal")
            self.decompress_button.config(state="normal")

            if success:
                self.status.set("Operación completada.")
                messagebox.showinfo("Resultado", message)
            else:
                self.status.set("No se pudo completar la operación.")
                messagebox.showerror("Error", message)

        self.root.after(100, self.check_results)

    def close(self):
        if self.busy:
            messagebox.showinfo(
                "Operación en curso",
                "Esperá a que termine antes de cerrar la ventana.",
            )
            return

        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = CompresorApp(root)
    root.mainloop()