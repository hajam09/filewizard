import os
import queue
import threading
from tkinter import filedialog, ttk

import customtkinter as ctk

from filewizard.services.RenamePhotoFilesWithDateService import (
    RenamePhotoFilesWithDateService,
)


class RenamePhotoFilesWithDateView(ctk.CTkFrame):

    def __init__(self, master, on_back):
        super().__init__(master, fg_color='transparent')

        self.onBack = on_back
        self.progressQueue = queue.Queue()
        self.running = False
        self.folderPath = ctk.StringVar(value='')
        self.includeSubfolders = ctk.StringVar(value='no')
        self.dryRun = ctk.StringVar(value='yes')

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._buildHeader()
        self._buildBody()
        self.after(100, self._drainProgressQueue)

    def _buildHeader(self):
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.grid(
            row=0,
            column=0,
            sticky='ew',
            padx=28,
            pady=(24, 8),
        )

        ctk.CTkButton(
            header,
            text='< Home',
            width=110,
            command=self.onBack,
        ).pack(side='left')

        ctk.CTkLabel(
            header,
            text='Rename Photos with Date Taken',
            font=ctk.CTkFont(size=22, weight='bold'),
        ).pack(side='left', padx=16)

    def _buildBody(self):
        body = ctk.CTkScrollableFrame(self, fg_color='transparent')
        body.grid(
            row=1,
            column=0,
            sticky='nsew',
            padx=20,
            pady=(0, 20),
        )
        body.grid_columnconfigure(0, weight=1)

        folderCard = self._card(body, 'Folder')
        pathRow = ctk.CTkFrame(folderCard, fg_color='transparent')
        pathRow.pack(fill='x', padx=16, pady=(0, 16))
        pathRow.grid_columnconfigure(0, weight=1)

        ctk.CTkEntry(
            pathRow,
            textvariable=self.folderPath,
            height=36,
            placeholder_text='Choose a folder...',
        ).grid(row=0, column=0, sticky='ew', padx=(0, 8))

        ctk.CTkButton(
            pathRow,
            text='Browse',
            width=110,
            command=self._browseFolder,
        ).grid(row=0, column=1)

        optionsCard = self._card(body, 'Options')
        self._radioRow(
            optionsCard,
            'Apply to subfolders?',
            self.includeSubfolders,
            'Yes scans the selected folder and all nested folders.',
        )
        self._radioRow(
            optionsCard,
            'Dry run?',
            self.dryRun,
            'Yes previews proposed names without changing files. '
            'No renames the matching photo files.',
        )

        actions = ctk.CTkFrame(body, fg_color='transparent')
        actions.pack(fill='x', pady=(4, 12))

        self.runButton = ctk.CTkButton(
            actions,
            text='Start',
            height=40,
            command=self._startRename,
        )
        self.runButton.pack(side='left')

        self.statusLabel = ctk.CTkLabel(
            actions,
            text='Ready',
            text_color=('gray20', 'gray70'),
        )
        self.statusLabel.pack(side='left', padx=16)

        self.progressBar = ctk.CTkProgressBar(body)
        self.progressBar.pack(fill='x', pady=(0, 12))
        self.progressBar.set(0)

        self._buildResultsTable(body)

    def _buildResultsTable(self, parent):
        card = self._card(parent, 'Results')
        tableFrame = ctk.CTkFrame(card, fg_color='transparent')
        tableFrame.pack(fill='both', expand=True, padx=16, pady=(0, 16))
        tableFrame.grid_rowconfigure(0, weight=1)
        tableFrame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.configure(
            'PhotoRename.Treeview',
            rowheight=30,
            font=('TkDefaultFont', 10),
        )
        style.configure(
            'PhotoRename.Treeview.Heading',
            font=('TkDefaultFont', 10, 'bold'),
        )

        self.resultsTable = ttk.Treeview(
            tableFrame,
            columns=('original', 'newName', 'status', 'details'),
            show='headings',
            height=12,
            style='PhotoRename.Treeview',
        )

        for column, title in (
            ('original', 'Original File'),
            ('newName', 'New Name'),
            ('status', 'Status'),
            ('details', 'Details'),
        ):
            self.resultsTable.heading(column, text=title)

        self.resultsTable.column('original', width=340, minwidth=180, anchor='w')
        self.resultsTable.column('newName', width=250, minwidth=160, anchor='w')
        self.resultsTable.column(
            'status',
            width=130,
            minwidth=110,
            anchor='center',
            stretch=False,
        )
        self.resultsTable.column('details', width=300, minwidth=180, anchor='w')

        self.resultsTable.tag_configure('success', foreground='#2e7d32')
        self.resultsTable.tag_configure('preview', foreground='#1565c0')
        self.resultsTable.tag_configure('failed', foreground='#c62828')
        self.resultsTable.tag_configure('skipped', foreground='#757575')

        self.resultsTable.grid(row=0, column=0, sticky='nsew')

        verticalScrollbar = ttk.Scrollbar(
            tableFrame,
            orient='vertical',
            command=self.resultsTable.yview,
        )
        verticalScrollbar.grid(row=0, column=1, sticky='ns')

        horizontalScrollbar = ttk.Scrollbar(
            tableFrame,
            orient='horizontal',
            command=self.resultsTable.xview,
        )
        horizontalScrollbar.grid(row=1, column=0, sticky='ew')

        self.resultsTable.configure(
            yscrollcommand=verticalScrollbar.set,
            xscrollcommand=horizontalScrollbar.set,
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

    def _radioRow(self, parent, label, variable, hint):
        row = ctk.CTkFrame(parent, fg_color='transparent')
        row.pack(fill='x', padx=16, pady=(0, 14))

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

        for labelText, value in (('Yes', 'yes'), ('No', 'no')):
            ctk.CTkRadioButton(
                choices,
                text=labelText,
                variable=variable,
                value=value,
            ).pack(side='left', padx=(0, 16) if value == 'yes' else 0)

    def _browseFolder(self):
        selected = filedialog.askdirectory(title='Choose a folder')
        if selected:
            self.folderPath.set(selected)

    def _startRename(self):
        if self.running:
            return

        folder = self.folderPath.get().strip()
        if not folder:
            self._setStatus('Choose a folder first.')
            return

        self.running = True
        self.runButton.configure(state='disabled')
        self.progressBar.set(0)
        self._clearResultsTable()
        self._setStatus('Preparing...')

        options = {
            'folderPath': folder,
            'includeSubfolders': self.includeSubfolders.get() == 'yes',
            'dryRun': self.dryRun.get() == 'yes',
        }
        worker = threading.Thread(
            target=self._runRename,
            args=(options,),
            daemon=True,
        )
        worker.start()

    def _runRename(self, options):
        try:
            service = RenamePhotoFilesWithDateService(
                progressCallback=self._onProgress,
                **options,
            )
            self.progressQueue.put(('done', service.execute()))
        except Exception as exception:
            self.progressQueue.put(('error', str(exception)))

    def _onProgress(self, current, total, path):
        self.progressQueue.put(('progress', current, total, path))

    def _drainProgressQueue(self):
        while True:
            try:
                item = self.progressQueue.get_nowait()
            except queue.Empty:
                break

            if item[0] == 'progress':
                _, current, total, path = item
                self.progressBar.set(current / total if total else 0)
                self._setStatus(f'{current} / {total}  {path}')
            elif item[0] == 'done':
                self._finishSuccess(item[1])
            elif item[0] == 'error':
                self._finishError(item[1])

        self.after(100, self._drainProgressQueue)

    def _finishSuccess(self, results):
        self.running = False
        self.runButton.configure(state='normal')
        self.progressBar.set(1)
        self._populateResultsTable(results)

        renamedCount = sum(
            not item.get('unchanged')
            for item in results['renamed']
        )
        failedCount = len(results['failed'])
        skippedCount = len(results['skipped'])

        if results['dryRun']:
            status = f'Dry run complete. {renamedCount} photos would be renamed.'
        else:
            status = f'Finished. {renamedCount} photos renamed.'

        if skippedCount or failedCount:
            status += f' {skippedCount} skipped, {failedCount} failed.'

        self._setStatus(status)

    def _finishError(self, message):
        self.running = False
        self.runButton.configure(state='normal')
        self.progressBar.set(0)
        self._clearResultsTable()
        self._addResultRow('', '', 'Error', message, 'failed')
        self._setStatus('Stopped with an error.')

    def _populateResultsTable(self, results):
        self._clearResultsTable()

        for item in results['renamed']:
            if item.get('unchanged'):
                status = 'Unchanged'
                tag = 'skipped'
            elif results['dryRun']:
                status = 'Would rename'
                tag = 'preview'
            else:
                status = 'Renamed'
                tag = 'success'

            self._addResultRow(
                item['filePath'],
                item['newName'],
                status,
                item['dateTaken'].strftime('%Y-%m-%d %H:%M:%S'),
                tag,
            )

        for item in results['skipped']:
            self._addResultRow(
                item['filePath'],
                '',
                'Skipped',
                item['reason'],
                'skipped',
            )

        for item in results['failed']:
            self._addResultRow(
                item['filePath'],
                '',
                'Failed',
                item['reason'],
                'failed',
            )

        if not results['renamed'] and not results['skipped'] and not results['failed']:
            self._addResultRow('', '', 'Info', 'No photo files found.', 'skipped')

    def _addResultRow(self, original, newName, status, details, tag):
        self.resultsTable.insert(
            '',
            'end',
            values=(original, newName, status, details),
            tags=(tag,),
        )

    def _clearResultsTable(self):
        if not hasattr(self, 'resultsTable'):
            return
        for item in self.resultsTable.get_children():
            self.resultsTable.delete(item)

    def _setStatus(self, text):
        self.statusLabel.configure(text=text)
