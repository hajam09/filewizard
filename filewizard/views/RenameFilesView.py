import os
import queue
import random
import string
import threading
from tkinter import filedialog, ttk

import customtkinter as ctk

from filewizard.services.RenameFilesService import (
    RenameFilesService,
)


class RenameFilesView(ctk.CTkFrame):

    def __init__(self, master, on_back):
        super().__init__(
            master,
            fg_color='transparent',
        )

        self.onBack = on_back
        self.progressQueue = queue.Queue()
        self.running = False

        self.folderPath = ctk.StringVar(
            value=''
        )

        self.prefix = ctk.StringVar(
            value=self._generatePrefix()
        )

        self.sortBy = ctk.StringVar(
            value='Keep Current'
        )

        self.includeSubfolders = ctk.StringVar(
            value='no'
        )

        self.dryRun = ctk.StringVar(
            value='yes'
        )

        self.grid_rowconfigure(
            1,
            weight=1,
        )

        self.grid_columnconfigure(
            0,
            weight=1,
        )

        self._buildHeader()
        self._buildBody()

        self.after(
            100,
            self._drainProgressQueue,
        )

    def onShow(self):
        self._resetView()

    def _resetView(self):
        if self.running:
            return

        self.folderPath.set('')

        self.prefix.set(
            self._generatePrefix()
        )

        self.sortBy.set(
            'Keep Current'
        )

        self.includeSubfolders.set(
            'no'
        )

        self.dryRun.set(
            'yes'
        )

        self.progressBar.set(0)

        self._clearResultsTable()

        self._clearProgressQueue()

        self._setStatus(
            'Ready'
        )

    def _clearProgressQueue(self):
        while True:
            try:
                self.progressQueue.get_nowait()
            except queue.Empty:
                break

    def _buildHeader(self):
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
            command=self.onBack,
        ).pack(
            side='left'
        )

        ctk.CTkLabel(
            header,
            text='Rename Files',
            font=ctk.CTkFont(
                size=22,
                weight='bold',
            ),
        ).pack(
            side='left',
            padx=16,
        )

    def _buildBody(self):
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

        self._buildFolderSection(body)
        self._buildOptionsSection(body)
        self._buildActionSection(body)
        self._buildResultsSection(body)

    def _buildFolderSection(self, parent):
        card = self._card(
            parent,
            'Folder',
        )

        pathRow = ctk.CTkFrame(
            card,
            fg_color='transparent',
        )

        pathRow.pack(
            fill='x',
            padx=16,
            pady=(0, 16),
        )

        pathRow.grid_columnconfigure(
            0,
            weight=1,
        )

        ctk.CTkEntry(
            pathRow,
            textvariable=self.folderPath,
            height=36,
        ).grid(
            row=0,
            column=0,
            sticky='ew',
            padx=(0, 8),
        )

        ctk.CTkButton(
            pathRow,
            text='Browse',
            width=110,
            command=self._browseFolder,
        ).grid(
            row=0,
            column=1,
        )

    def _buildOptionsSection(self, parent):
        card = self._card(
            parent,
            'Options',
        )

        self._buildPrefixRow(card)

        self._dropdownRow(
            card,
            'Sort files by',
            self.sortBy,
            [
                'Keep Current',
                'File type (A-Z)',
                'File size (smallest first)',
                'File size (largest first)',
            ],
            (
                'Keep Current uses the files in their '
                'current folder order. Other options '
                'sort the files before numbering them.'
            ),
        )

        self._radioRow(
            card,
            'Apply to subfolders?',
            self.includeSubfolders,
            (
                'Yes renames files in the selected '
                'folder and all nested folders.'
            ),
        )

        self._radioRow(
            card,
            'Dry run?',
            self.dryRun,
            (
                'Yes previews the changes without '
                'renaming any files.'
            ),
        )

    def _buildPrefixRow(self, parent):
        row = ctk.CTkFrame(
            parent,
            fg_color='transparent',
        )

        row.pack(
            fill='x',
            padx=16,
            pady=(0, 14),
        )

        ctk.CTkLabel(
            row,
            text='File prefix',
            font=ctk.CTkFont(
                size=14,
                weight='bold',
            ),
            anchor='w',
        ).pack(
            fill='x'
        )

        ctk.CTkLabel(
            row,
            text=(
                'A prefix is generated automatically. '
                'You can edit it before starting. '
                'Leave it empty to let the service '
                'generate a prefix.'
            ),
            font=ctk.CTkFont(
                size=12,
            ),
            text_color=(
                'gray20',
                'gray70',
            ),
            wraplength=760,
            justify='left',
            anchor='w',
        ).pack(
            fill='x',
            pady=(0, 6),
        )

        prefixRow = ctk.CTkFrame(
            row,
            fg_color='transparent',
        )

        prefixRow.pack(
            fill='x'
        )

        prefixRow.grid_columnconfigure(
            0,
            weight=1,
        )

        self.prefixEntry = ctk.CTkEntry(
            prefixRow,
            textvariable=self.prefix,
            height=36,
            placeholder_text='Example: IMG',
        )

        self.prefixEntry.grid(
            row=0,
            column=0,
            sticky='ew',
            padx=(0, 8),
        )

        self.prefixPreviewLabel = ctk.CTkLabel(
            prefixRow,
            text=f'Using: {self.prefix.get()}',
            font=ctk.CTkFont(
                size=12,
            ),
            text_color=(
                'gray20',
                'gray70',
            ),
        )

        self.prefixPreviewLabel.grid(
            row=0,
            column=1,
        )

        self.prefix.trace_add(
            'write',
            self._onPrefixChanged,
        )

    def _dropdownRow(
        self,
        parent,
        label,
        variable,
        values,
        hint,
    ):
        row = ctk.CTkFrame(
            parent,
            fg_color='transparent',
        )

        row.pack(
            fill='x',
            padx=16,
            pady=(0, 14),
        )

        ctk.CTkLabel(
            row,
            text=label,
            font=ctk.CTkFont(
                size=14,
                weight='bold',
            ),
            anchor='w',
        ).pack(
            fill='x'
        )

        ctk.CTkLabel(
            row,
            text=hint,
            font=ctk.CTkFont(
                size=12,
            ),
            text_color=(
                'gray20',
                'gray70',
            ),
            wraplength=760,
            justify='left',
            anchor='w',
        ).pack(
            fill='x',
            pady=(0, 6),
        )

        ctk.CTkOptionMenu(
            row,
            variable=variable,
            values=values,
            width=320,
        ).pack(
            anchor='w'
        )

    def _radioRow(
        self,
        parent,
        label,
        variable,
        hint,
    ):
        row = ctk.CTkFrame(
            parent,
            fg_color='transparent',
        )

        row.pack(
            fill='x',
            padx=16,
            pady=(0, 14),
        )

        ctk.CTkLabel(
            row,
            text=label,
            font=ctk.CTkFont(
                size=14,
                weight='bold',
            ),
            anchor='w',
        ).pack(
            fill='x'
        )

        ctk.CTkLabel(
            row,
            text=hint,
            font=ctk.CTkFont(
                size=12,
            ),
            text_color=(
                'gray20',
                'gray70',
            ),
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

        choices.pack(
            anchor='w'
        )

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
        ).pack(
            side='left'
        )

    def _buildActionSection(self, parent):
        actions = ctk.CTkFrame(
            parent,
            fg_color='transparent',
        )

        actions.pack(
            fill='x',
            pady=(4, 12),
        )

        self.runButton = ctk.CTkButton(
            actions,
            text='Start',
            height=40,
            command=self._startRename,
        )

        self.runButton.pack(
            side='left'
        )

        self.statusLabel = ctk.CTkLabel(
            actions,
            text='Ready',
            text_color=(
                'gray20',
                'gray70',
            ),
        )

        self.statusLabel.pack(
            side='left',
            padx=16,
        )

        self.progressBar = ctk.CTkProgressBar(
            parent
        )

        self.progressBar.pack(
            fill='x',
            pady=(0, 12),
        )

        self.progressBar.set(0)

    def _buildResultsSection(self, parent):
        card = self._card(
            parent,
            'Results',
        )

        tableFrame = ctk.CTkFrame(
            card,
            fg_color='transparent',
        )

        tableFrame.pack(
            fill='both',
            expand=True,
            padx=16,
            pady=(0, 16),
        )

        tableFrame.grid_rowconfigure(
            0,
            weight=1,
        )

        tableFrame.grid_columnconfigure(
            0,
            weight=1,
        )

        style = ttk.Style()

        try:
            style.configure(
                'FileWizard.Treeview',
                rowheight=30,
                font=(
                    'TkDefaultFont',
                    10,
                ),
            )

            style.configure(
                'FileWizard.Treeview.Heading',
                font=(
                    'TkDefaultFont',
                    10,
                    'bold',
                ),
            )

        except Exception:
            pass

        columns = (
            'number',
            'original',
            'new',
            'status',
        )

        self.resultsTable = ttk.Treeview(
            tableFrame,
            columns=columns,
            show='headings',
            style='FileWizard.Treeview',
            height=12,
        )

        self.resultsTable.heading(
            'number',
            text='#',
        )

        self.resultsTable.heading(
            'original',
            text='Original Name',
        )

        self.resultsTable.heading(
            'new',
            text='New Name',
        )

        self.resultsTable.heading(
            'status',
            text='Status',
        )

        self.resultsTable.column(
            'number',
            width=60,
            minwidth=50,
            anchor='center',
            stretch=False,
        )

        self.resultsTable.column(
            'original',
            width=280,
            minwidth=160,
            anchor='w',
        )

        self.resultsTable.column(
            'new',
            width=280,
            minwidth=160,
            anchor='w',
        )

        self.resultsTable.column(
            'status',
            width=130,
            minwidth=100,
            anchor='center',
            stretch=False,
        )

        self.resultsTable.grid(
            row=0,
            column=0,
            sticky='nsew',
        )

        verticalScrollbar = ttk.Scrollbar(
            tableFrame,
            orient='vertical',
            command=self.resultsTable.yview,
        )

        verticalScrollbar.grid(
            row=0,
            column=1,
            sticky='ns',
        )

        horizontalScrollbar = ttk.Scrollbar(
            tableFrame,
            orient='horizontal',
            command=self.resultsTable.xview,
        )

        horizontalScrollbar.grid(
            row=1,
            column=0,
            sticky='ew',
        )

        self.resultsTable.configure(
            yscrollcommand=(
                verticalScrollbar.set
            ),
            xscrollcommand=(
                horizontalScrollbar.set
            ),
        )

        self.resultsTable.tag_configure(
            'success',
            foreground='#2e7d32',
        )

        self.resultsTable.tag_configure(
            'preview',
            foreground='#1565c0',
        )

        self.resultsTable.tag_configure(
            'failed',
            foreground='#c62828',
        )

        self.resultsTable.tag_configure(
            'unchanged',
            foreground='#757575',
        )

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

    def _browseFolder(self):
        selected = filedialog.askdirectory(
            title='Choose a folder',
        )

        if selected:
            self.folderPath.set(
                selected
            )

    def _startRename(self):
        if self.running:
            return

        folder = self.folderPath.get().strip()

        if not folder:
            self._setStatus(
                'Choose a folder first.'
            )
            return

        self.running = True

        self.runButton.configure(
            state='disabled'
        )

        self.progressBar.set(0)

        self._clearResultsTable()

        self._setStatus(
            'Preparing...'
        )

        options = {
            'folderPath': folder,
            'prefix': self.prefix.get().strip(),
            'sortBy': self._getSortValue(),
            'includeSubfolders': (
                self.includeSubfolders.get()
                == 'yes'
            ),
            'dryRun': (
                self.dryRun.get()
                == 'yes'
            ),
        }

        worker = threading.Thread(
            target=self._runRename,
            args=(options,),
            daemon=True,
        )

        worker.start()

    def _runRename(self, options):
        try:
            service = RenameFilesService(
                progressCallback=self._onProgress,
                **options,
            )

            results = service.execute()

            self.progressQueue.put(
                (
                    'done',
                    results,
                )
            )

        except Exception as exception:
            self.progressQueue.put(
                (
                    'error',
                    str(exception),
                )
            )

    def _onProgress(
        self,
        current,
        total,
        path,
    ):
        self.progressQueue.put(
            (
                'progress',
                current,
                total,
                path,
            )
        )

    def _drainProgressQueue(self):
        while True:
            try:
                item = (
                    self.progressQueue
                    .get_nowait()
                )

            except queue.Empty:
                break

            kind = item[0]

            if kind == 'progress':
                _, current, total, path = item

                fraction = (
                    current / total
                    if total
                    else 0
                )

                self.progressBar.set(
                    fraction
                )

                self._setStatus(
                    f'{current} / {total}  '
                    f'{path}'
                )

            elif kind == 'done':
                self._finishSuccess(
                    item[1]
                )

            elif kind == 'error':
                self._finishError(
                    item[1]
                )

        self.after(
            100,
            self._drainProgressQueue,
        )

    def _finishSuccess(self, results):
        self.running = False

        self.runButton.configure(
            state='normal'
        )

        renamed = results.get(
            'renamed',
            [],
        )

        failed = results.get(
            'failed',
            [],
        )

        dryRun = results.get(
            'dryRun',
            False,
        )

        self.progressBar.set(1)

        self._clearResultsTable()

        self._populateResultsTable(
            results
        )

        if dryRun:
            self._setStatus(
                f'Dry run complete. '
                f'{len(renamed)} files would '
                f'be renamed.'
            )
        else:
            self._setStatus(
                f'Finished. '
                f'{len(renamed)} files renamed.'
            )

        if failed:
            self._setStatus(
                f'Finished with '
                f'{len(failed)} failed.'
            )

    def _finishError(self, message):
        self.running = False

        self.runButton.configure(
            state='normal'
        )

        self.progressBar.set(0)

        self._clearResultsTable()

        self._addTableRow(
            number='',
            original=message,
            new='',
            status='Error',
            tag='failed',
        )

        self._setStatus(
            'Stopped with an error.'
        )

    def _populateResultsTable(self, results):
        renamed = results.get(
            'renamed',
            [],
        )

        failed = results.get(
            'failed',
            [],
        )

        dryRun = results.get(
            'dryRun',
            False,
        )

        rowNumber = 1

        for item in renamed:
            if dryRun:
                status = 'Would rename'
                tag = 'preview'
            else:
                status = 'Renamed'
                tag = 'success'

            self._addTableRow(
                number=rowNumber,
                original=item.get(
                    'oldName',
                    '',
                ),
                new=item.get(
                    'newName',
                    '',
                ),
                status=status,
                tag=tag,
            )

            rowNumber += 1

        for item in failed:
            self._addTableRow(
                number=rowNumber,
                original=os.path.basename(
                    item.get(
                        'filePath',
                        '',
                    )
                ),
                new='',
                status='Failed',
                tag='failed',
            )

            rowNumber += 1

        if not renamed and not failed:
            self._addTableRow(
                number='',
                original='No files found.',
                new='',
                status='Info',
                tag='unchanged',
            )

    def _addTableRow(
        self,
        number,
        original,
        new,
        status,
        tag='',
    ):
        self.resultsTable.insert(
            '',
            'end',
            values=(
                number,
                original,
                new,
                status,
            ),
            tags=(tag,),
        )

    def _clearResultsTable(self):
        if not hasattr(
            self,
            'resultsTable',
        ):
            return

        for item in (
            self.resultsTable.get_children()
        ):
            self.resultsTable.delete(
                item
            )

    def _getSortValue(self):
        values = {
            'Keep Current': (
                RenameFilesService
                .SORT_NONE
            ),
            'File type (A-Z)': (
                RenameFilesService
                .SORT_FILE_TYPE
            ),
            'File size (smallest first)': (
                RenameFilesService
                .SORT_SIZE_ASC
            ),
            'File size (largest first)': (
                RenameFilesService
                .SORT_SIZE_DESC
            ),
        }

        return values[
            self.sortBy.get()
        ]

    def _generatePrefix(self):
        return ''.join(
            random.choices(
                string.ascii_uppercase,
                k=3,
            )
        )

    def _onPrefixChanged(self, *_):
        prefix = self.prefix.get().strip()

        if prefix:
            self.prefixPreviewLabel.configure(
                text=f'Using: {prefix}'
            )
        else:
            self.prefixPreviewLabel.configure(
                text='Auto-generated prefix'
            )

    def _setStatus(self, text):
        self.statusLabel.configure(
            text=text
        )
