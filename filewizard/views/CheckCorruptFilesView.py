import logging
import queue
import threading
import traceback
from tkinter import filedialog

import customtkinter as ctk

from filewizard.services.CheckCorruptFilesService import (
    CheckCorruptFilesService,
)

logger = logging.getLogger(__name__)


class CheckCorruptFilesView(ctk.CTkFrame):

    def __init__(self, master, on_back):
        super().__init__(master, fg_color='transparent')

        self.on_back = on_back
        self.progress_queue = queue.Queue()
        self.running = False

        self.folder_path = ctk.StringVar(value='')
        self.include_subfolders = ctk.StringVar(value='no')
        self.dry_run = ctk.StringVar(value='yes')
        self.file_type_options = {
            extension: ctk.BooleanVar(value=True)
            for extensions in CheckCorruptFilesService.FILE_TYPE_GROUPS.values()
            for extension in extensions
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
            text='Check Corrupt Files',
            font=ctk.CTkFont(size=22, weight='bold'),
        ).pack(side='left', padx=16)

    def _build_body(self):
        body = ctk.CTkScrollableFrame(self, fg_color='transparent')
        body.grid(
            row=1,
            column=0,
            sticky='nsew',
            padx=20,
            pady=(0, 20),
        )
        body.grid_columnconfigure(0, weight=1)

        folder_card = self._card(body, 'Folder')
        path_row = ctk.CTkFrame(
            folder_card,
            fg_color='transparent',
        )
        path_row.pack(fill='x', padx=16, pady=(0, 8))
        path_row.grid_columnconfigure(0, weight=1)

        ctk.CTkEntry(
            path_row,
            textvariable=self.folder_path,
            height=36,
            placeholder_text='Choose a folder...',
        ).grid(row=0, column=0, sticky='ew', padx=(0, 8))

        ctk.CTkButton(
            path_row,
            text='Browse',
            width=110,
            command=self._browse_folder,
        ).grid(row=0, column=1)

        ctk.CTkLabel(
            folder_card,
            text=(
                'Select extensions to check. Office files are checked '
                'structurally; legacy binary formats are checked for a '
                'valid container and required document stream. Text files '
                'are checked for common '
                'encoding errors. Detected corrupt files are moved under '
                'the selected folder’s corrupt directory.'
            ),
            font=ctk.CTkFont(size=12),
            text_color=('gray20', 'gray70'),
            wraplength=760,
            justify='left',
            anchor='w',
        ).pack(fill='x', padx=16, pady=(0, 14))

        options_card = self._card(body, 'Options')
        self._build_file_type_options(options_card)
        self._radio_row(
            options_card,
            'Apply to subfolders?',
            self.include_subfolders,
            (
                'Yes checks all nested folders and keeps their relative '
                'paths under corrupt. No checks only this folder.'
            ),
        )
        self._radio_row(
            options_card,
            'Dry run?',
            self.dry_run,
            (
                'Yes previews corrupt files without moving them. No moves '
                'them to the corrupt folder.'
            ),
        )

        actions = ctk.CTkFrame(body, fg_color='transparent')
        actions.pack(fill='x', pady=(4, 12))

        self.run_button = ctk.CTkButton(
            actions,
            text='Check Files',
            height=40,
            command=self._start_check,
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

        results_card = self._card(body, 'Results')
        self.results_box = ctk.CTkTextbox(results_card, height=240)
        self.results_box.pack(
            fill='both',
            expand=True,
            padx=16,
            pady=(0, 16),
        )
        self._write_results('Corrupt file results will appear here.\n')

    def _build_file_type_options(self, parent):
        row = ctk.CTkFrame(parent, fg_color='transparent')
        row.pack(fill='x', padx=16, pady=(0, 14))

        ctk.CTkLabel(
            row,
            text='File types to check',
            font=ctk.CTkFont(size=14, weight='bold'),
            anchor='w',
        ).pack(fill='x', pady=(0, 6))

        for group, extensions in CheckCorruptFilesService.FILE_TYPE_GROUPS.items():
            group_frame = ctk.CTkFrame(row, fg_color='transparent')
            group_frame.pack(fill='x', pady=(4, 0))

            ctk.CTkLabel(
                group_frame,
                text=group,
                font=ctk.CTkFont(size=12, weight='bold'),
                anchor='w',
            ).pack(anchor='w')

            choices = ctk.CTkFrame(group_frame, fg_color='transparent')
            choices.pack(anchor='w')
            for index, extension in enumerate(extensions):
                ctk.CTkCheckBox(
                    choices,
                    text=extension,
                    variable=self.file_type_options[extension],
                ).grid(
                    row=index // 5,
                    column=index % 5,
                    sticky='w',
                    padx=(0, 18),
                    pady=3,
                )

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

        for text, value in (('Yes', 'yes'), ('No', 'no')):
            ctk.CTkRadioButton(
                choices,
                text=text,
                variable=variable,
                value=value,
            ).pack(side='left', padx=(0, 16))

    def _browse_folder(self):
        selected = filedialog.askdirectory(
            title='Choose a folder',
        )

        if selected:
            self.folder_path.set(selected)

    def _start_check(self):
        if self.running:
            return

        folder = self.folder_path.get().strip()

        if not folder:
            self._set_status('Choose a folder first.')
            return

        file_extensions = [
            extension
            for extension, variable in self.file_type_options.items()
            if variable.get()
        ]

        if not file_extensions:
            self._set_status('Select at least one file type to check.')
            return

        self.running = True
        self.run_button.configure(state='disabled')
        self.progress_bar.set(0)
        self._set_status('Checking files...')
        self._write_results('Starting file check...\n')

        options = {
            'folderPath': folder,
            'includeSubfolders': (
                self.include_subfolders.get() == 'yes'
            ),
            'dryRun': self.dry_run.get() == 'yes',
            'fileExtensions': file_extensions,
        }

        worker = threading.Thread(
            target=self._run_check,
            args=(options,),
            daemon=True,
        )
        worker.start()

    def _run_check(self, options):
        try:
            service = CheckCorruptFilesService(
                progressCallback=self._on_progress,
                **options,
            )
            results = service.execute()
            self.progress_queue.put(('done', results))
        except Exception as exception:
            exceptionTraceback = traceback.format_exc()
            logger.exception('Corrupt-file scan failed')
            self.progress_queue.put(
                (
                    'error',
                    type(exception).__name__,
                    str(exception),
                    exceptionTraceback,
                )
            )

    def _on_progress(self, current, total, file_path):
        self.progress_queue.put(
            ('progress', current, total, file_path)
        )

    def _drain_progress_queue(self):
        while True:
            try:
                item = self.progress_queue.get_nowait()
            except queue.Empty:
                break

            kind = item[0]

            if kind == 'progress':
                _, current, total, file_path = item
                self.progress_bar.set(
                    current / total if total else 1
                )
                self._set_status(
                    f'{current} / {total}  {file_path}'
                )
            elif kind == 'done':
                self._finish_success(item[1])
            elif kind == 'error':
                self._finish_error(*item[1:])

        self.after(100, self._drain_progress_queue)

    def _finish_success(self, results):
        self.running = False
        self.run_button.configure(state='normal')
        self.progress_bar.set(1)

        corrupt = results['corrupt']
        failed = results['failed']
        corruptCounts = self._count_by_extension(corrupt)
        countSummary = ', '.join(
            f'{count} {extension} file(s)'
            for extension, count in sorted(corruptCounts.items())
        ) or '0 corrupt files'
        if results['dryRun']:
            status = (
                f'Preview complete. {countSummary} found.'
            )
        else:
            status = (
                f'Finished. {countSummary} moved.'
            )

        if failed:
            status += f' {len(failed)} files failed.'
        self._set_status(status)
        self._write_results(self._format_results(results))

    def _finish_error(self, errorType, message, exceptionTraceback):
        self.running = False
        self.run_button.configure(state='normal')
        self.progress_bar.set(0)
        self._set_status('Stopped with an error.')
        self._write_results(
            f'Scan error: {errorType}: {message}\n\n'
            f'Traceback:\n{exceptionTraceback}'
        )

    def _format_results(self, results):
        if results['dryRun']:
            lines = ['Corrupt files (preview; not moved):', '']
        else:
            lines = ['Corrupt files moved:', '']

        if results['corrupt']:
            for item in results['corrupt']:
                lines.append(
                    f"  {item['filePath']} "
                    f"({item['extension']}) -> {item['destination']}"
                )
        else:
            lines.append('No corrupt files found.')

        if results['skipped']:
            lines.extend(('', 'Skipped:'))
            for item in results['skipped']:
                lines.append(
                    f"  {item['filePath']}: {item['reason']}"
                )

        if results['failed']:
            lines.extend(('', 'Failed:'))
            for item in results['failed']:
                lines.append(
                    f"  File: {item['filePath']}"
                )
                lines.append(
                    f"  Operation: {item.get('operation', 'unknown')}"
                )
                lines.append(
                    f"  Error: {item.get('errorType', 'Error')}: "
                    f"{item['reason']}"
                )
                if item.get('traceback'):
                    lines.extend(('', item['traceback'].rstrip()))

        return '\n'.join(lines)

    def _count_by_extension(self, corrupt_files):
        counts = {}
        for item in corrupt_files:
            extension = item['extension']
            counts[extension] = counts.get(extension, 0) + 1
        return counts

    def _write_results(self, text):
        self.results_box.configure(state='normal')
        self.results_box.delete('1.0', 'end')
        self.results_box.insert('1.0', text)
        self.results_box.configure(state='disabled')

    def _set_status(self, text):
        self.status_label.configure(text=text)
