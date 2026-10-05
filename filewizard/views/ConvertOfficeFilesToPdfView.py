import queue
import threading
from tkinter import filedialog

import customtkinter as ctk

from filewizard.services.ConvertOfficeFilesToPdfService import (
    ConvertToPdfService,
)


class ConvertOfficeFilesToPdfView(ctk.CTkFrame):

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

        self.includeSubfolders = ctk.StringVar(
            value='no'
        )

        self.dryRun = ctk.StringVar(
            value='yes'
        )

        self.deleteOriginal = ctk.StringVar(
            value='no'
        )

        self.overwriteExisting = ctk.StringVar(
            value='no'
        )

        self.fileTypeVars = {
            key: ctk.BooleanVar(
                value=True
            )
            for key in ConvertToPdfService.FILE_TYPES
        }

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

    # ========================================================
    # LIFECYCLE
    # ========================================================

    def onShow(self):
        self._resetView()

    def _resetView(self):
        if self.running:
            return

        self.folderPath.set('')

        self.includeSubfolders.set(
            'no'
        )

        self.dryRun.set(
            'yes'
        )

        self.deleteOriginal.set(
            'no'
        )

        self.overwriteExisting.set(
            'no'
        )

        for variable in self.fileTypeVars.values():
            variable.set(True)

        self.progressBar.set(0)

        self._clearProgressQueue()

        self._writeResults(
            'Results will appear here.\n'
        )

        self._setStatus(
            'Ready'
        )

    def _clearProgressQueue(self):
        while True:
            try:
                self.progressQueue.get_nowait()

            except queue.Empty:
                break

    # ========================================================
    # HEADER
    # ========================================================

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
            text='Convert to PDF',
            font=ctk.CTkFont(
                size=22,
                weight='bold',
            ),
        ).pack(
            side='left',
            padx=16,
        )

    # ========================================================
    # BODY
    # ========================================================

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
        self._buildFileTypesSection(body)
        self._buildActionSection(body)
        self._buildResultsSection(body)

    # ========================================================
    # FOLDER
    # ========================================================

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
            placeholder_text='Choose a folder...',
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

    # ========================================================
    # OPTIONS
    # ========================================================

    def _buildOptionsSection(self, parent):
        card = self._card(
            parent,
            'Options',
        )

        self._radioRow(
            card,
            'Apply to subfolders?',
            self.includeSubfolders,
            (
                'Yes converts files in the selected '
                'folder and all nested folders. '
                'No only converts files directly '
                'inside the selected folder.'
            ),
        )

        self._radioRow(
            card,
            'Dry run?',
            self.dryRun,
            (
                'Yes previews the files that would '
                'be converted without changing anything. '
                'No performs the conversion.'
            ),
        )

        self._radioRow(
            card,
            'Delete original files after conversion?',
            self.deleteOriginal,
            (
                'Yes deletes the original Office file '
                'only after its PDF has been successfully '
                'created. No keeps the original file.'
            ),
        )

        self._radioRow(
            card,
            'Overwrite existing PDF files?',
            self.overwriteExisting,
            (
                'Yes replaces an existing PDF. '
                'No keeps the existing PDF and creates '
                'a unique name such as name_2.pdf.'
            ),
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

    # ========================================================
    # FILE TYPES
    # ========================================================

    def _buildFileTypesSection(self, parent):
        card = self._card(
            parent,
            'File Types',
        )

        container = ctk.CTkFrame(
            card,
            fg_color='transparent',
        )

        container.pack(
            fill='x',
            padx=16,
            pady=(0, 16),
        )

        container.grid_columnconfigure(
            0,
            weight=1,
        )

        container.grid_columnconfigure(
            1,
            weight=1,
        )

        self._buildFileTypeGroup(
            container,
            'Word',
            ConvertToPdfService.WORD_FILE_TYPES,
            0,
        )

        self._buildFileTypeGroup(
            container,
            'PowerPoint',
            ConvertToPdfService.POWERPOINT_FILE_TYPES,
            1,
        )

    def _buildFileTypeGroup(
        self,
        parent,
        title,
        fileTypes,
        column,
    ):
        group = ctk.CTkFrame(
            parent,
            fg_color='transparent',
        )

        group.grid(
            row=0,
            column=column,
            sticky='nw',
            padx=8,
        )

        ctk.CTkLabel(
            group,
            text=title,
            font=ctk.CTkFont(
                size=14,
                weight='bold',
            ),
            anchor='w',
        ).pack(
            fill='x',
            pady=(0, 6),
        )

        for key, extension in fileTypes.items():
            ctk.CTkCheckBox(
                group,
                text=extension,
                variable=self.fileTypeVars[key],
            ).pack(
                anchor='w',
                pady=3,
            )

    def _getSelectedFileTypes(self):
        return [
            key
            for key, variable in self.fileTypeVars.items()
            if variable.get()
        ]

    # ========================================================
    # ACTIONS
    # ========================================================

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
            text='Run Conversion',
            height=40,
            command=self._startConversion,
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

    # ========================================================
    # RESULTS
    # ========================================================

    def _buildResultsSection(self, parent):
        card = self._card(
            parent,
            'Results',
        )

        self.resultsBox = ctk.CTkTextbox(
            card,
            height=260,
        )

        self.resultsBox.pack(
            fill='both',
            expand=True,
            padx=16,
            pady=(0, 16),
        )

        self.resultsBox.insert(
            '1.0',
            'Results will appear here.\n'
        )

        self.resultsBox.configure(
            state='disabled'
        )

    # ========================================================
    # UI HELPERS
    # ========================================================

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

    # ========================================================
    # CONVERSION
    # ========================================================

    def _startConversion(self):
        if self.running:
            return

        folder = self.folderPath.get().strip()

        fileTypes = self._getSelectedFileTypes()

        if not folder:
            self._setStatus(
                'Choose a folder first.'
            )
            return

        if not fileTypes:
            self._setStatus(
                'Select at least one file type.'
            )
            return

        self.running = True

        self.runButton.configure(
            state='disabled'
        )

        self.progressBar.set(0)

        self._setStatus(
            'Preparing...'
        )

        self._writeResults(
            'Starting...\n'
        )

        options = {
            'folderPath': folder,
            'includeSubfolders': (
                self.includeSubfolders.get()
                == 'yes'
            ),
            'dryRun': (
                self.dryRun.get()
                == 'yes'
            ),
            'deleteOriginal': (
                self.deleteOriginal.get()
                == 'yes'
            ),
            'overwriteExisting': (
                self.overwriteExisting.get()
                == 'yes'
            ),
            'fileTypes': fileTypes,
        }

        worker = threading.Thread(
            target=self._runConversion,
            args=(options,),
            daemon=True,
        )

        worker.start()

    def _runConversion(self, options):
        try:
            service = ConvertToPdfService(
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

    # ========================================================
    # PROGRESS QUEUE
    # ========================================================

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

    # ========================================================
    # COMPLETION
    # ========================================================

    def _finishSuccess(self, results):
        self.running = False

        self.runButton.configure(
            state='normal'
        )

        self.progressBar.set(1)

        converted = results.get(
            'converted',
            [],
        )

        skipped = results.get(
            'skipped',
            [],
        )

        failed = results.get(
            'failed',
            [],
        )

        deleted = results.get(
            'deleted',
            [],
        )

        dryRun = results.get(
            'dryRun',
            False,
        )

        if dryRun:
            self._setStatus(
                f'Dry run finished. '
                f'{len(converted)} files would '
                f'be converted.'
            )
        else:
            self._setStatus(
                f'Finished. '
                f'{len(converted)} files converted.'
            )

        if failed:
            self._setStatus(
                f'Finished with '
                f'{len(failed)} failed.'
            )

        self._writeResults(
            self._formatResults(
                results
            )
        )

    def _finishError(self, message):
        self.running = False

        self.runButton.configure(
            state='normal'
        )

        self.progressBar.set(0)

        self._setStatus(
            'Stopped with an error.'
        )

        self._writeResults(
            f'Error: {message}\n'
        )

    # ========================================================
    # RESULT FORMATTING
    # ========================================================

    def _formatResults(self, results):
        folderPath = results.get(
            'folderPath',
            '',
        )

        total = results.get(
            'total',
            0,
        )

        converted = results.get(
            'converted',
            [],
        )

        skipped = results.get(
            'skipped',
            [],
        )

        failed = results.get(
            'failed',
            [],
        )

        deleted = results.get(
            'deleted',
            [],
        )

        dryRun = results.get(
            'dryRun',
            False,
        )

        lines = [
            f'Folder: {folderPath}',
            (
                'Mode: '
                f'{"dry run" if dryRun else "live"}'
            ),
            f'Files found: {total}',
            f'Converted: {len(converted)}',
            f'Skipped: {len(skipped)}',
            f'Failed: {len(failed)}',
            f'Deleted originals: {len(deleted)}',
            '',
        ]

        if converted:
            if dryRun:
                lines.append(
                    'Would convert:'
                )
            else:
                lines.append(
                    'Converted:'
                )

            for item in converted:
                lines.append(
                    f"  {item['sourcePath']}"
                )

                lines.append(
                    f"    -> {item['outputPath']}"
                )

            lines.append('')

        if skipped:
            lines.append(
                'Skipped:'
            )

            for item in skipped:
                lines.append(
                    f"  {item.get('filePath', '')}"
                )

                lines.append(
                    f"    {item.get('reason', '')}"
                )

            lines.append('')

        if failed:
            lines.append(
                'Failed:'
            )

            for item in failed:
                lines.append(
                    f"  {item.get('filePath', '')}"
                )

                lines.append(
                    f"    {item.get('reason', '')}"
                )

            lines.append('')

        if deleted:
            lines.append(
                'Deleted originals:'
            )

            for path in deleted:
                lines.append(
                    f'  {path}'
                )

            lines.append('')

        if (
            not converted
            and not skipped
            and not failed
        ):
            lines.append(
                'No matching files found.'
            )

        return '\n'.join(lines)

    def _writeResults(self, text):
        self.resultsBox.configure(
            state='normal'
        )

        self.resultsBox.delete(
            '1.0',
            'end',
        )

        self.resultsBox.insert(
            '1.0',
            text,
        )

        self.resultsBox.configure(
            state='disabled'
        )

    def _setStatus(self, text):
        self.statusLabel.configure(
            text=text
        )
