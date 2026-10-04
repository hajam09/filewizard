import customtkinter as ctk


class HomeView(ctk.CTkFrame):
    def __init__(self, master, features, on_open_feature):
        super().__init__(master, fg_color='transparent')

        self.features = features
        self.on_open_feature = on_open_feature

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color='transparent')
        header.grid(row=0, column=0, sticky='ew', padx=28, pady=(28, 12))

        ctk.CTkLabel(
            header,
            text='File Wizard',
            font=ctk.CTkFont(size=28, weight='bold'),
        ).pack(anchor='w')

        ctk.CTkLabel(
            header,
            text='Choose a tool. Extra slots are ready for later features.',
            font=ctk.CTkFont(size=14),
            text_color=('gray20', 'gray70'),
        ).pack(anchor='w', pady=(4, 0))

        grid = ctk.CTkFrame(self, fg_color='transparent')
        grid.grid(row=1, column=0, sticky='nsew', padx=28, pady=(8, 28))

        columns = 2
        for column in range(columns):
            grid.grid_columnconfigure(column, weight=1, uniform='feature')

        rows = (len(features) + columns - 1) // columns
        for row in range(rows):
            grid.grid_rowconfigure(row, weight=1, uniform='feature')

        for index, feature in enumerate(features):
            row = index // columns
            column = index % columns
            self._build_card(grid, feature).grid(
                row=row,
                column=column,
                sticky='nsew',
                padx=8,
                pady=8,
            )

    def _build_card(self, parent, feature):
        card = ctk.CTkFrame(parent, corner_radius=16)

        title = feature['title']
        if not feature['ready']:
            title = f'{title}  ·  Soon'

        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=18, weight='bold'),
            anchor='w',
        ).pack(fill='x', padx=18, pady=(18, 6))

        ctk.CTkLabel(
            card,
            text=feature['description'],
            font=ctk.CTkFont(size=13),
            text_color=('gray20', 'gray70'),
            wraplength=360,
            justify='left',
            anchor='w',
        ).pack(fill='x', padx=18)

        ctk.CTkButton(
            card,
            text='Open' if feature['ready'] else 'View slot',
            height=36,
            command=lambda feature_id=feature['id']: self.on_open_feature(
                feature_id
            ),
        ).pack(fill='x', padx=18, pady=(16, 18))

        return card
