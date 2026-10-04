import queue
import threading
from tkinter import filedialog

import customtkinter as ctk

from filewizard.services.DeleteEmptyFolderService import DeleteEmptyFolderService


class DeleteEmptyFoldersView(ctk.CTkFrame):
    def __init__(self, master, on_back):
        super().__init__(master, fg_color='transparent')

        self.on_back = on_back
        self.progress_queue = queue.Queue()
        self.running = False

        self.folder_path = ctk.StringVar(value='')
        self.include_subfolders = ctk.StringVar(value='no')
        self.dry_run = ctk.StringVar(value='yes')

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
            text='Delete Empty Folders',
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

        # Folder
        path_card = self._card(body, 'Folder')

        path_row = ctk.CTkFrame(
            path_card,
            fg_color='transparent',
        )
        path_row.pack(
            fill='x',
            padx=16,
            pady=(0, 16),
        )
        path_row.grid_columnconfigure(0, weight=1)

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

        # Options
        options_card = self._card(body, 'Options')

        self._radio_row(
            options_card,
            'Apply to subfolders?',
            self.include_subfolders,
            hint='Yes checks this folder and every nested folder.',
        )

        self._radio_row(
            options_card,
            'Dry run?',
            self.dry_run,
            hint='Yes only lists folders that would be deleted. No deletes them.',
        )

        # Actions
        actions = ctk.CTkFrame(
            body,
            fg_color='transparent',
        )
        actions.pack(
            fill='x',
            pady=(4, 12),
        )

        self.run_button = ctk.CTkButton(
            actions,
            text='Start',
            height=40,
            command=self._start_deletion,
        )
        self.run_button.pack(side='left')

        self.status_label = ctk.CTkLabel(
            actions,
            text='Ready',
            text_color=('gray20', 'gray70'),
        )
        self.status_label.pack(
            side='left',
            padx=16,
        )

        self.progress_bar = ctk.CTkProgressBar(body)
        self.progress_bar.pack(
            fill='x',
            pady=(0, 12),
        )
        self.progress_bar.set(0)

        # Results
        log_card = self._card(body, 'Results')

        self.results_box = ctk.CTkTextbox(
            log_card,
            height=220,
        )
        self.results_box.pack(
            fill='both',
            expand=True,
            padx=16,
            pady=(0, 16),
        )

        self.results_box.insert(
            '1.0',
            'Deleted folders will appear here.\n',
        )
        self.results_box.configure(state='disabled')

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

    def _radio_row(self, parent, label, variable, hint):
        row = ctk.CTkFrame(
            parent,
            fg_color='transparent',
        )
        row.pack(
            fill='x',
            padx=16,
            pady=(0, 12),
        )

        ctk.CTkLabel(
            row,
            text=label,
            font=ctk.CTkFont(
                size=14,
                weight='bold',
            ),
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
        ).pack(
            fill='x',
            pady=(0, 6),
        )

        choices = ctk.CTkFrame(
            row,
            fg_color='transparent',
        )
        choices.pack(anchor='w')

        ctk.CTkRadioButton(
            choices,
            text='Yes',
            variable=variable,
            value='yes',
        ).pack(
            side='left',
            padx=(0, 16),
        )

        ctk.CTkRadioButton(
            choices,
            text='No',
            variable=variable,
            value='no',
        ).pack(side='left')

    def _browse_folder(self):
        selected = filedialog.askdirectory(
            title='Choose a folder',
        )

        if selected:
            self.folder_path.set(selected)

    def _start_deletion(self):
        if self.running:
            return

        folder = self.folder_path.get().strip()

        if not folder:
            self._set_status('Choose a folder first.')
            return

        self.running = True
        self.run_button.configure(state='disabled')
        self.progress_bar.set(0)
        self._set_status('Working...')
        self._write_results('Starting...\n')

        options = {
            'folderPath': folder,
            'includeSubfolders': (
                    self.include_subfolders.get() == 'yes'
            ),
            'dryRun': (
                    self.dry_run.get() == 'yes'
            ),
        }

        worker = threading.Thread(
            target=self._run_deletion,
            args=(options,),
            daemon=True,
        )
        worker.start()

    def _run_deletion(self, options):
        try:
            service = DeleteEmptyFolderService(
                progressCallback=self._on_progress,
                **options,
            )

            results = service.execute()

            self.progress_queue.put(
                ('done', results)
            )

        except Exception as exception:
            self.progress_queue.put(
                ('error', str(exception))
            )

    def _on_progress(self, current, total, path):
        self.progress_queue.put(
            ('progress', current, total, path)
        )

    def _drain_progress_queue(self):
        while True:
            try:
                item = self.progress_queue.get_nowait()

            except queue.Empty:
                break

            kind = item[0]

            if kind == 'progress':
                _kind, current, total, path = item

                fraction = (
                    current / total
                    if total
                    else 1
                )

                self.progress_bar.set(fraction)

                self._set_status(
                    f'{current} / {total}  {path}'
                )

            elif kind == 'done':
                self._finish_success(item[1])

            elif kind == 'error':
                self._finish_error(item[1])

        self.after(
            100,
            self._drain_progress_queue,
        )

    def _finish_success(self, results):
        self.running = False
        self.run_button.configure(state='normal')
        self.progress_bar.set(1)

        deleted = results.get('deleted', [])
        dry_run = results.get('dryRun', False)

        if dry_run:
            self._set_status(
                f'Dry run finished. '
                f'{len(deleted)} empty folders found.'
            )
        else:
            self._set_status(
                f'Finished. '
                f'{len(deleted)} folders deleted.'
            )

        self._write_results(
            self._format_results(results)
        )

    def _finish_error(self, message):
        self.running = False
        self.run_button.configure(state='normal')

        self._set_status(
            'Stopped with an error.'
        )

        self._write_results(
            f'Error: {message}\n'
        )

    def _format_results(self, results):
        deleted = results.get('deleted', [])
        dry_run = results.get('dryRun', False)

        if dry_run:
            lines = [
                'Empty folders that would be deleted:',
                '',
            ]
        else:
            lines = [
                'Folders deleted:',
                '',
            ]

        if deleted:
            for path in deleted:
                lines.append(f'  {path}')
        else:
            if dry_run:
                lines.append(
                    'No empty folders found.'
                )
            else:
                lines.append(
                    'No folders were deleted.'
                )

        return '\n'.join(lines)

    def _write_results(self, text):
        self.results_box.configure(
            state='normal'
        )

        self.results_box.delete(
            '1.0',
            'end',
        )

        self.results_box.insert(
            '1.0',
            text,
        )

        self.results_box.configure(
            state='disabled'
        )

    def _set_status(self, text):
        self.status_label.configure(
            text=text
        )
