import customtkinter as ctk


class ComingSoonView(ctk.CTkFrame):
    def __init__(self, master, title, on_back):
        super().__init__(master, fg_color='transparent')

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color='transparent')
        header.grid(row=0, column=0, sticky='ew', padx=28, pady=(24, 8))

        ctk.CTkButton(
            header,
            text='← Home',
            width=110,
            command=on_back,
        ).pack(side='left')

        body = ctk.CTkFrame(self, corner_radius=16)
        body.grid(row=1, column=0, sticky='nsew', padx=28, pady=(8, 28))

        ctk.CTkLabel(
            body,
            text=title,
            font=ctk.CTkFont(size=26, weight='bold'),
        ).pack(pady=(80, 8))

        ctk.CTkLabel(
            body,
            text='This tool is not built yet. The slot is reserved.',
            font=ctk.CTkFont(size=15),
            text_color=('gray20', 'gray70'),
        ).pack()
