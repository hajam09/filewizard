import queue
import threading
import tkinter as tk
from tkinter import filedialog, ttk

import customtkinter as ctk

from filewizard.services.FilesCounterService import FilesCounterService


class FilesCounterView(ctk.CTkFrame):

    def __init__(self, master, on_back):
        super().__init__(
            master,
            fg_color='transparent',
        )

        self.on_back = on_back
        self.progress_queue = queue.Queue()
        self.running = False

        self.folder_path = ctk.StringVar(value='')

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._configure_table_style()
        self._build_header()
        self._build_body()

        self.after(
            100,
            self._drain_progress_queue,
        )

    def _configure_table_style(self):
        style = ttk.Style()

        try:
            style.theme_use('clam')
        except tk.TclError:
            pass

        style.configure(
            'FileCounter.Treeview',
            rowheight=32,
            font=('TkDefaultFont', 11),
        )

        style.configure(
            'FileCounter.Treeview.Heading',
            font=(
                'TkDefaultFont',
                11,
                'bold',
            ),
        )

        style.map(
            'FileCounter.Treeview',
            background=[
                ('selected', '#1f6aa5'),
            ],
            foreground=[
                ('selected', 'white'),
            ],
        )

    def _build_header(self):
        header = ctk.CTkFrame(
            self,
            fg_color='transparent',
        )

        header.grid(
            row=0,
            column=0,
            sticky='ew',
            padx=28,
            pady=(24, 8),
        )

        ctk.CTkButton(
            header,
            text='← Home',
            width=110,
            command=self.on_back,
        ).pack(side='left')

        ctk.CTkLabel(
            header,
            text='File Counter',
            font=ctk.CTkFont(
                size=22,
                weight='bold',
            ),
        ).pack(
            side='left',
            padx=16,
        )

    def _build_body(self):
        body = ctk.CTkScrollableFrame(
            self,
            fg_color='transparent',
        )

        body.grid(
            row=1,
            column=0,
            sticky='nsew',
            padx=20,
            pady=(0, 20),
        )

        body.grid_columnconfigure(
            0,
            weight=1,
        )

        self._build_folder_section(body)
        self._build_action_section(body)
        self._build_summary_section(body)
        self._build_file_types_section(body)

    def _build_folder_section(self, parent):
        folder_card = self._card(
            parent,
            'Folder',
        )

        path_row = ctk.CTkFrame(
            folder_card,
            fg_color='transparent',
        )

        path_row.pack(
            fill='x',
            padx=16,
            pady=(0, 16),
        )

        path_row.grid_columnconfigure(
            0,
            weight=1,
        )

        ctk.CTkEntry(
            path_row,
            textvariable=self.folder_path,
            height=36,
        ).grid(
            row=0,
            column=0,
            sticky='ew',
            padx=(0, 8),
        )

        ctk.CTkButton(
            path_row,
            text='Browse',
            width=110,
            command=self._browse_folder,
        ).grid(
            row=0,
            column=1,
        )

        ctk.CTkLabel(
            folder_card,
            text=(
                'The selected folder and all of its '
                'subfolders will be scanned.'
            ),
            font=ctk.CTkFont(size=12),
            text_color=('gray20', 'gray70'),
            anchor='w',
        ).pack(
            fill='x',
            padx=16,
            pady=(0, 14),
        )

    def _build_action_section(self, parent):
        actions = ctk.CTkFrame(
            parent,
            fg_color='transparent',
        )

        actions.pack(
            fill='x',
            pady=(4, 12),
        )

        self.run_button = ctk.CTkButton(
            actions,
            text='Scan',
            height=40,
            command=self._start_scan,
        )

        self.run_button.pack(
            side='left',
        )

        self.status_label = ctk.CTkLabel(
            actions,
            text='Ready',
            text_color=('gray20', 'gray70'),
        )

        self.status_label.pack(
            side='left',
            padx=16,
        )

        self.progress_bar = ctk.CTkProgressBar(
            parent,
        )

        self.progress_bar.pack(
            fill='x',
            pady=(0, 12),
        )

        self.progress_bar.set(0)

    def _build_summary_section(self, parent):
        summary_card = self._card(
            parent,
            'Summary',
        )

        self.summary_frame = ctk.CTkFrame(
            summary_card,
            fg_color='transparent',
        )

        self.summary_frame.pack(
            fill='x',
            padx=16,
            pady=(0, 16),
        )

        self.summary_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        self.summary_frame.grid_columnconfigure(
            1,
            weight=1,
        )

        self.summary_frame.grid_columnconfigure(
            2,
            weight=1,
        )

        self.summary_frame.grid_columnconfigure(
            3,
            weight=1,
        )

        self.summary_values = {}

        metrics = [
            ('totalFiles', 'Total Files'),
            ('totalSize', 'Total Size'),
            ('uniqueFileTypes', 'Unique Types'),
            ('emptyFiles', 'Empty Files'),
            ('averageFileSize', 'Average File Size'),
            ('largestFileSize', 'Largest File'),
        ]

        for index, (key, label) in enumerate(metrics):
            row = index // 3
            column = index % 3

            metric = ctk.CTkFrame(
                self.summary_frame,
                corner_radius=10,
            )

            metric.grid(
                row=row,
                column=column,
                sticky='ew',
                padx=5,
                pady=5,
            )

            ctk.CTkLabel(
                metric,
                text=label,
                font=ctk.CTkFont(
                    size=12,
                ),
                text_color=('gray20', 'gray70'),
            ).pack(
                anchor='w',
                padx=12,
                pady=(10, 2),
            )

            value_label = ctk.CTkLabel(
                metric,
                text='—',
                font=ctk.CTkFont(
                    size=18,
                    weight='bold',
                ),
                anchor='w',
            )

            value_label.pack(
                anchor='w',
                padx=12,
                pady=(0, 10),
            )

            self.summary_values[key] = value_label

    def _build_file_types_section(self, parent):
        results_card = self._card(
            parent,
            'File Types',
        )

        table_frame = ctk.CTkFrame(
            results_card,
            fg_color='transparent',
        )

        table_frame.pack(
            fill='both',
            expand=True,
            padx=16,
            pady=(0, 16),
        )

        table_frame.grid_rowconfigure(
            0,
            weight=1,
        )

        table_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        self.file_types_table = ttk.Treeview(
            table_frame,
            columns=(
                'type',
                'count',
                'size',
                'percentage',
            ),
            show='headings',
            height=12,
            style='FileCounter.Treeview',
        )

        self.file_types_table.heading(
            'type',
            text='File Type',
            command=lambda: self._sort_table(
                'type',
                False,
            ),
        )

        self.file_types_table.heading(
            'count',
            text='Files',
            command=lambda: self._sort_table(
                'count',
                True,
            ),
        )

        self.file_types_table.heading(
            'size',
            text='Total Size',
            command=lambda: self._sort_table(
                'size',
                True,
            ),
        )

        self.file_types_table.heading(
            'percentage',
            text='Storage',
            command=lambda: self._sort_table(
                'percentage',
                True,
            ),
        )

        self.file_types_table.column(
            'type',
            width=180,
            minwidth=120,
            anchor='w',
        )

        self.file_types_table.column(
            'count',
            width=100,
            minwidth=80,
            anchor='e',
        )

        self.file_types_table.column(
            'size',
            width=140,
            minwidth=120,
            anchor='e',
        )

        self.file_types_table.column(
            'percentage',
            width=100,
            minwidth=90,
            anchor='e',
        )

        scrollbar = ctk.CTkScrollbar(
            table_frame,
            command=self.file_types_table.yview,
        )

        self.file_types_table.configure(
            yscrollcommand=scrollbar.set,
        )

        self.file_types_table.grid(
            row=0,
            column=0,
            sticky='nsew',
        )

        scrollbar.grid(
            row=0,
            column=1,
            sticky='ns',
            padx=(6, 0),
        )

        self.file_types_table.bind(
            '<Double-1>',
            self._on_file_type_double_click,
        )

        self._table_sort_reverse = {}

    def _card(self, parent, title):
        card = ctk.CTkFrame(
            parent,
            corner_radius=14,
        )

        card.pack(
            fill='x',
            pady=8,
        )

        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(
                size=16,
                weight='bold',
            ),
            anchor='w',
        ).pack(
            fill='x',
            padx=16,
            pady=(14, 10),
        )

        return card

    def _browse_folder(self):
        selected = filedialog.askdirectory(
            title='Choose a folder',
        )

        if selected:
            self.folder_path.set(selected)

    def _start_scan(self):
        if self.running:
            return

        folder = self.folder_path.get().strip()

        if not folder:
            self._set_status(
                'Choose a folder first.'
            )
            return

        self.running = True

        self.run_button.configure(
            state='disabled',
        )

        self.progress_bar.configure(
            mode='indeterminate',
        )

        self.progress_bar.start()

        self._set_status(
            'Scanning...'
        )

        self._clear_results()

        worker = threading.Thread(
            target=self._run_scan,
            args=(folder,),
            daemon=True,
        )

        worker.start()

    def _run_scan(self, folder):
        try:
            service = FilesCounterService(
                folderPath=folder,
                progressCallback=self._on_progress,
            )

            results = service.execute()

            self.progress_queue.put(
                (
                    'done',
                    results,
                )
            )

        except Exception as exception:
            self.progress_queue.put(
                (
                    'error',
                    str(exception),
                )
            )

    def _on_progress(self, current, total, path):
        self.progress_queue.put(
            (
                'progress',
                current,
                total,
                path,
            )
        )

    def _drain_progress_queue(self):
        while True:
            try:
                item = self.progress_queue.get_nowait()

            except queue.Empty:
                break

            kind = item[0]

            if kind == 'progress':
                _, current, total, path = item

                self._set_status(
                    f'Scanning: {path}'
                )

            elif kind == 'done':
                self._finish_success(
                    item[1],
                )

            elif kind == 'error':
                self._finish_error(
                    item[1],
                )

        self.after(
            100,
            self._drain_progress_queue,
        )

    def _finish_success(self, results):
        self.running = False

        self.progress_bar.stop()

        self.progress_bar.configure(
            mode='determinate',
        )

        self.progress_bar.set(1)

        self.run_button.configure(
            state='normal',
        )

        self._set_status(
            'Scan complete.'
        )

        self._update_summary(
            results,
        )

        self._populate_file_types_table(
            results,
        )

    def _finish_error(self, message):
        self.running = False

        self.progress_bar.stop()

        self.progress_bar.configure(
            mode='determinate',
        )

        self.progress_bar.set(0)

        self.run_button.configure(
            state='normal',
        )

        self._set_status(
            'Stopped with an error.'
        )

        self._clear_results()

        self.summary_values['totalFiles'].configure(
            text='Error',
        )

        self.summary_values['totalSize'].configure(
            text=message,
        )

    def _update_summary(self, results):
        self.summary_values['totalFiles'].configure(
            text=f'{results.get("totalFiles", 0):,}',
        )

        self.summary_values['totalSize'].configure(
            text=results.get(
                'formattedTotalSize',
                '0 B',
            ),
        )

        self.summary_values['uniqueFileTypes'].configure(
            text=f'{results.get("uniqueFileTypes", 0):,}',
        )

        self.summary_values['emptyFiles'].configure(
            text=f'{results.get("emptyFiles", 0):,}',
        )

        self.summary_values['averageFileSize'].configure(
            text=results.get(
                'formattedAverageFileSize',
                '0 B',
            ),
        )

        self.summary_values['largestFileSize'].configure(
            text=results.get(
                'formattedLargestFileSize',
                '0 B',
            ),
        )

    def _populate_file_types_table(self, results):
        self._clear_table()

        file_types = results.get(
            'fileTypes',
            [],
        )

        for item in file_types:
            self.file_types_table.insert(
                '',
                'end',
                values=(
                    item['type'],
                    f'{item["count"]:,}',
                    item['formattedSize'],
                    f'{item["percentage"]:.2f}%',
                ),
            )

    def _clear_table(self):
        for item in self.file_types_table.get_children():
            self.file_types_table.delete(item)

    def _clear_results(self):
        self._clear_table()

        for label in self.summary_values.values():
            label.configure(
                text='—',
            )

    def _sort_table(self, column, numeric):
        rows = []

        for item in self.file_types_table.get_children(''):
            value = self.file_types_table.set(
                item,
                column,
            )

            if numeric:
                value = self._parse_numeric_value(
                    value,
                )

            rows.append(
                (
                    value,
                    item,
                )
            )

        reverse = self._table_sort_reverse.get(
            column,
            False,
        )

        rows.sort(
            key=lambda item: item[0],
            reverse=reverse,
        )

        for index, (_, item) in enumerate(rows):
            self.file_types_table.move(
                item,
                '',
                index,
            )

        self._table_sort_reverse[column] = not reverse

    def _parse_numeric_value(self, value):
        value = value.replace(
            ',',
            '',
        )

        if value.endswith('%'):
            return float(
                value.rstrip('%')
            )

        units = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 ** 2,
            'GB': 1024 ** 3,
            'TB': 1024 ** 4,
            'PB': 1024 ** 5,
        }

        parts = value.split()

        if len(parts) != 2:
            try:
                return float(value)
            except ValueError:
                return 0

        try:
            number = float(parts[0])
            multiplier = units.get(
                parts[1],
                1,
            )

            return number * multiplier

        except ValueError:
            return 0

    def _on_file_type_double_click(self, event):
        selection = self.file_types_table.selection()

        if not selection:
            return

        item = self.file_types_table.item(
            selection[0],
        )

        values = item.get(
            'values',
            [],
        )

        if not values:
            return

        file_type = values[0]

        self._set_status(
            f'Selected file type: {file_type}'
        )

    def _set_status(self, text):
        self.status_label.configure(
            text=text,
        )
