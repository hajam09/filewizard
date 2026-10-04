import queue
import threading
from tkinter import filedialog

import customtkinter as ctk

from filewizard.services.convert_to_pdf_service import (
    POWERPOINT_FILE_TYPES,
    WORD_FILE_TYPES,
    convert_files_to_pdf,
)


class ConvertPdfView(ctk.CTkFrame):
    def __init__(self, master, on_back):
        super().__init__(master, fg_color='transparent')

        self.on_back = on_back
        self.progress_queue = queue.Queue()
        self.running = False

        self.folder_path = ctk.StringVar(value='')
        self.include_subfolders = ctk.StringVar(value='no')
        self.dry_run = ctk.StringVar(value='yes')
        self.delete_original = ctk.StringVar(value='no')
        self.overwrite_existing = ctk.StringVar(value='no')
        self.file_type_vars = {
            key: ctk.BooleanVar(value=key in {'doc', 'docx', 'ppt', 'pptx'})
            for key in list(WORD_FILE_TYPES) + list(POWERPOINT_FILE_TYPES)
        }

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_body()
        self.after(100, self._drain_progress_queue)

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.grid(row=0, column=0, sticky='ew', padx=28, pady=(24, 8))

        ctk.CTkButton(
            header,
            text='← Home',
            width=110,
            command=self.on_back,
        ).pack(side='left')

        ctk.CTkLabel(
            header,
            text='Convert to PDF',
            font=ctk.CTkFont(size=22, weight='bold'),
        ).pack(side='left', padx=16)

    def _build_body(self):
        body = ctk.CTkScrollableFrame(self, fg_color='transparent')
        body.grid(row=1, column=0, sticky='nsew', padx=20, pady=(0, 20))
        body.grid_columnconfigure(0, weight=1)

        path_card = self._card(body, 'Folder')
        path_row = ctk.CTkFrame(path_card, fg_color='transparent')
        path_row.pack(fill='x', padx=16, pady=(0, 16))
        path_row.grid_columnconfigure(0, weight=1)

        ctk.CTkEntry(
            path_row,
            textvariable=self.folder_path,
            height=36,
        ).grid(row=0, column=0, sticky='ew', padx=(0, 8))

        ctk.CTkButton(
            path_row,
            text='Browse',
            width=110,
            command=self._browse_folder,
        ).grid(row=0, column=1)

        options_card = self._card(body, 'Options')
        self._radio_row(
            options_card,
            'Apply to subfolders?',
            self.include_subfolders,
            hint='Yes converts files in this folder and every nested folder.',
        )
        self._radio_row(
            options_card,
            'Dry run?',
            self.dry_run,
            hint='Yes only lists what would change. No converts the files.',
        )
        self._radio_row(
            options_card,
            'Delete original files after conversion?',
            self.delete_original,
            hint='Only deletes a source file after its PDF is created.',
        )
        self._radio_row(
            options_card,
            'Overwrite existing PDF files?',
            self.overwrite_existing,
            hint=(
                'Yes replaces an existing PDF. No keeps it and saves as '
                'name_2.pdf, name_3.pdf, and so on.'
            ),
        )

        types_card = self._card(body, 'File types')
        types_inner = ctk.CTkFrame(types_card, fg_color='transparent')
        types_inner.pack(fill='x', padx=16, pady=(0, 16))
        types_inner.grid_columnconfigure(0, weight=1)
        types_inner.grid_columnconfigure(1, weight=1)

        self._checkbox_group(
            types_inner,
            'Word',
            WORD_FILE_TYPES,
            row=0,
            column=0,
        )
        self._checkbox_group(
            types_inner,
            'PowerPoint',
            POWERPOINT_FILE_TYPES,
            row=0,
            column=1,
        )

        actions = ctk.CTkFrame(body, fg_color='transparent')
        actions.pack(fill='x', pady=(4, 12))

        self.run_button = ctk.CTkButton(
            actions,
            text='Run conversion',
            height=40,
            command=self._start_conversion,
        )
        self.run_button.pack(side='left')

        self.status_label = ctk.CTkLabel(
            actions,
            text='Ready',
            text_color=('gray20', 'gray70'),
        )
        self.status_label.pack(side='left', padx=16)

        self.progress_bar = ctk.CTkProgressBar(body)
        self.progress_bar.pack(fill='x', pady=(0, 12))
        self.progress_bar.set(0)

        log_card = self._card(body, 'Results')
        self.results_box = ctk.CTkTextbox(log_card, height=220)
        self.results_box.pack(fill='both', expand=True, padx=16, pady=(0, 16))
        self.results_box.insert('1.0', 'Results will appear here.\n')
        self.results_box.configure(state='disabled')

    def _card(self, parent, title):
        card = ctk.CTkFrame(parent, corner_radius=14)
        card.pack(fill='x', pady=8)
        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=16, weight='bold'),
            anchor='w',
        ).pack(fill='x', padx=16, pady=(14, 10))
        return card

    def _radio_row(self, parent, label, variable, hint):
        row = ctk.CTkFrame(parent, fg_color='transparent')
        row.pack(fill='x', padx=16, pady=(0, 12))

        ctk.CTkLabel(
            row,
            text=label,
            font=ctk.CTkFont(size=14, weight='bold'),
            anchor='w',
        ).pack(fill='x')

        ctk.CTkLabel(
            row,
            text=hint,
            font=ctk.CTkFont(size=12),
            text_color=('gray20', 'gray70'),
            wraplength=760,
            justify='left',
            anchor='w',
        ).pack(fill='x', pady=(0, 6))

        choices = ctk.CTkFrame(row, fg_color='transparent')
        choices.pack(anchor='w')

        ctk.CTkRadioButton(
            choices,
            text='Yes',
            variable=variable,
            value='yes',
        ).pack(side='left', padx=(0, 16))

        ctk.CTkRadioButton(
            choices,
            text='No',
            variable=variable,
            value='no',
        ).pack(side='left')

    def _checkbox_group(self, parent, title, file_types, row, column):
        group = ctk.CTkFrame(parent, fg_color='transparent')
        group.grid(row=row, column=column, sticky='nsew', padx=8)

        ctk.CTkLabel(
            group,
            text=title,
            font=ctk.CTkFont(size=14, weight='bold'),
            anchor='w',
        ).pack(fill='x', pady=(0, 6))

        for key, extension in file_types.items():
            ctk.CTkCheckBox(
                group,
                text=extension,
                variable=self.file_type_vars[key],
            ).pack(anchor='w', pady=3)

    def _browse_folder(self):
        selected = filedialog.askdirectory(title='Choose a folder')
        if selected:
            self.folder_path.set(selected)

    def _selected_file_types(self):
        return [
            key
            for key, variable in self.file_type_vars.items()
            if variable.get()
        ]

    def _start_conversion(self):
        if self.running:
            return

        folder = self.folder_path.get().strip()
        file_types = self._selected_file_types()

        if not folder:
            self._set_status('Choose a folder first.')
            return

        if not file_types:
            self._set_status('Select at least one file type.')
            return

        self.running = True
        self.run_button.configure(state='disabled')
        self.progress_bar.set(0)
        self._set_status('Working...')
        self._write_results('Starting...\n')

        options = {
            'folder_path': folder,
            'include_subfolders': self.include_subfolders.get() == 'yes',
            'dry_run': self.dry_run.get() == 'yes',
            'delete_original': self.delete_original.get() == 'yes',
            'overwrite_existing': self.overwrite_existing.get() == 'yes',
            'file_types': file_types,
        }

        worker = threading.Thread(
            target=self._run_conversion,
            args=(options,),
            daemon=True,
        )
        worker.start()

    def _run_conversion(self, options):
        try:
            results = convert_files_to_pdf(
                progress_callback=self._on_progress,
                **options,
            )
            self.progress_queue.put(('done', results))
        except Exception as exception:
            self.progress_queue.put(('error', str(exception)))

    def _on_progress(self, current, total, path):
        self.progress_queue.put(('progress', current, total, path))

    def _drain_progress_queue(self):
        while True:
            try:
                item = self.progress_queue.get_nowait()
            except queue.Empty:
                break

            kind = item[0]
            if kind == 'progress':
                _kind, current, total, path = item
                fraction = current / total if total else 1
                self.progress_bar.set(fraction)
                self._set_status(f'{current} / {total}  {path}')
            elif kind == 'done':
                self._finish_success(item[1])
            elif kind == 'error':
                self._finish_error(item[1])

        self.after(100, self._drain_progress_queue)

    def _finish_success(self, results):
        self.running = False
        self.run_button.configure(state='normal')
        self.progress_bar.set(1)

        mode = 'Dry run' if results['dryRun'] else 'Conversion'
        self._set_status(
            f"{mode} finished. "
            f"{len(results['converted'])} ready, "
            f"{len(results['failed'])} failed, "
            f"{len(results['skipped'])} skipped."
        )
        self._write_results(self._format_results(results))

    def _finish_error(self, message):
        self.running = False
        self.run_button.configure(state='normal')
        self._set_status('Stopped with an error.')
        self._write_results(f'Error: {message}\n')

    def _format_results(self, results):
        lines = [
            f"Folder: {results['folderPath']}",
            f"Mode: {'dry run' if results['dryRun'] else 'live'}",
            f"Files found: {results['total']}",
            f"Converted: {len(results['converted'])}",
            f"Skipped: {len(results['skipped'])}",
            f"Failed: {len(results['failed'])}",
            f"Deleted originals: {len(results['deleted'])}",
            '',
        ]

        if results['converted']:
            heading = 'Would convert:' if results['dryRun'] else 'Converted:'
            lines.append(heading)
            for item in results['converted']:
                lines.append(
                    f"  {item['sourcePath']}  ->  {item['outputPath']}"
                )
            lines.append('')

        if results['skipped']:
            lines.append('Skipped:')
            for item in results['skipped']:
                lines.append(
                    f"  {item['filePath']}  ({item['reason']})"
                )
            lines.append('')

        if results['failed']:
            lines.append('Failed:')
            for item in results['failed']:
                lines.append(
                    f"  {item['filePath']}  ({item['reason']})"
                )
            lines.append('')

        if results['deleted']:
            lines.append('Deleted originals:')
            for path in results['deleted']:
                lines.append(f'  {path}')
            lines.append('')

        return '\n'.join(lines)

    def _write_results(self, text):
        self.results_box.configure(state='normal')
        self.results_box.delete('1.0', 'end')
        self.results_box.insert('1.0', text)
        self.results_box.configure(state='disabled')

    def _set_status(self, text):
        self.status_label.configure(text=text)
