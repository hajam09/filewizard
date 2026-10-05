import multiprocessing
import os
import queue

import pythoncom
import win32com.client


class ConvertToPdfService:

    WORD_FILE_TYPES = {
        'doc': '.doc',
        'docx': '.docx',
        'docm': '.docm',
        'dot': '.dot',
        'dotx': '.dotx',
        'rtf': '.rtf',
        'odt': '.odt',
    }

    POWERPOINT_FILE_TYPES = {
        'ppt': '.ppt',
        'pptx': '.pptx',
        'pps': '.pps',
        'ppsx': '.ppsx',
        'pot': '.pot',
        'potx': '.potx',
        'odp': '.odp',
    }

    FILE_TYPES = {
        **WORD_FILE_TYPES,
        **POWERPOINT_FILE_TYPES,
    }

    WORD_EXTENSIONS = set(
        WORD_FILE_TYPES.values()
    )

    POWERPOINT_EXTENSIONS = set(
        POWERPOINT_FILE_TYPES.values()
    )

    WORD_PDF_FORMAT = 17
    POWERPOINT_PDF_FORMAT = 32

    DEFAULT_CONVERSION_TIMEOUT = 60

    def __init__(
        self,
        folderPath,
        includeSubfolders=False,
        dryRun=True,
        deleteOriginal=False,
        overwriteExisting=False,
        fileTypes=None,
        progressCallback=None,
        conversionTimeout=DEFAULT_CONVERSION_TIMEOUT,
    ):
        self.folderPath = os.path.abspath(
            folderPath
        )

        self.includeSubfolders = (
            includeSubfolders
        )

        self.dryRun = dryRun

        self.deleteOriginal = (
            deleteOriginal
        )

        self.overwriteExisting = (
            overwriteExisting
        )

        self.fileTypes = fileTypes

        self.progressCallback = (
            progressCallback
        )

        self.conversionTimeout = (
            conversionTimeout
        )

    # ========================================================
    # PUBLIC
    # ========================================================

    def execute(self):
        self._validateFolder()

        extensions = self._getExtensions()

        files = self._collectFiles(
            extensions
        )

        results = self._createResults(
            files
        )

        if self.dryRun:
            return self._executeDryRun(
                files,
                results,
            )

        return self._executeConversion(
            files,
            results,
        )

    # ========================================================
    # VALIDATION
    # ========================================================

    def _validateFolder(self):
        if not os.path.isdir(
            self.folderPath
        ):
            raise ValueError(
                f'Folder does not exist: '
                f'{self.folderPath}'
            )

    def _getExtensions(self):
        if not self.fileTypes:
            return set(
                self.FILE_TYPES.values()
            )

        normalizedFileTypes = {
            str(fileType)
            .lower()
            .lstrip('.')
            for fileType in self.fileTypes
        }

        invalidTypes = (
            normalizedFileTypes
            - set(self.FILE_TYPES.keys())
        )

        if invalidTypes:
            raise ValueError(
                'Unsupported file types: '
                f'{sorted(invalidTypes)}'
            )

        return {
            self.FILE_TYPES[fileType]
            for fileType in normalizedFileTypes
        }

    # ========================================================
    # FILE COLLECTION
    # ========================================================

    def _collectFiles(self, extensions):
        files = []

        if self.includeSubfolders:

            for root, _directories, fileNames in os.walk(
                self.folderPath
            ):
                for fileName in fileNames:

                    if self._shouldProcessFile(
                        fileName,
                        extensions,
                    ):
                        files.append(
                            os.path.join(
                                root,
                                fileName,
                            )
                        )

        else:

            try:

                for fileName in os.listdir(
                    self.folderPath
                ):
                    filePath = os.path.join(
                        self.folderPath,
                        fileName,
                    )

                    if not os.path.isfile(
                        filePath
                    ):
                        continue

                    if self._shouldProcessFile(
                        fileName,
                        extensions,
                    ):
                        files.append(
                            filePath
                        )

            except OSError as exception:

                raise OSError(
                    f'Unable to read folder '
                    f'{self.folderPath}: {exception}'
                ) from exception

        files.sort()

        return files

    def _shouldProcessFile(
        self,
        fileName,
        extensions,
    ):
        # Ignore temporary Office files.
        if fileName.startswith('~$'):
            return False

        extension = os.path.splitext(
            fileName
        )[1].lower()

        return extension in extensions

    # ========================================================
    # RESULTS
    # ========================================================

    def _createResults(self, files):
        return {
            'folderPath': self.folderPath,
            'total': len(files),
            'converted': [],
            'skipped': [],
            'failed': [],
            'deleted': [],
            'dryRun': self.dryRun,
        }

    # ========================================================
    # DRY RUN
    # ========================================================

    def _executeDryRun(
        self,
        files,
        results,
    ):
        total = len(files)

        for current, inputPath in enumerate(
            files,
            start=1,
        ):
            outputPath = self._getOutputPath(
                inputPath
            )

            if self.progressCallback:
                self.progressCallback(
                    current,
                    total,
                    inputPath,
                )

            results['converted'].append({
                'sourcePath': inputPath,
                'outputPath': outputPath,
            })

        return results

    # ========================================================
    # REAL CONVERSION
    # ========================================================

    def _executeConversion(
        self,
        files,
        results,
    ):
        total = len(files)

        for current, inputPath in enumerate(
            files,
            start=1,
        ):
            if self.progressCallback:
                self.progressCallback(
                    current,
                    total,
                    inputPath,
                )

            result = self._convertFile(
                inputPath
            )

            self._processResult(
                inputPath,
                result,
                results,
            )

        return results

    # ========================================================
    # SINGLE FILE CONVERSION
    # ========================================================

    def _convertFile(self, inputPath):
        outputPath = self._getOutputPath(
            inputPath
        )

        extension = os.path.splitext(
            inputPath
        )[1].lower()

        if extension not in (
            self.WORD_EXTENSIONS
            | self.POWERPOINT_EXTENSIONS
        ):
            return {
                'status': 'skipped',
                'reason': (
                    f'Unsupported file type: '
                    f'{extension}'
                ),
            }

        # ====================================================
        # EXISTING PDF
        # ====================================================

        if os.path.exists(outputPath):

            if self.overwriteExisting:

                try:
                    os.remove(
                        outputPath
                    )

                except OSError as exception:

                    return {
                        'status': 'failed',
                        'stage': (
                            'remove_existing_pdf'
                        ),
                        'reason': str(
                            exception
                        ),
                    }

            else:

                outputPath = (
                    self._getUniquePdfPath(
                        outputPath
                    )
                )

        # ====================================================
        # WORKER PROCESS
        # ====================================================

        resultQueue = multiprocessing.Queue()

        process = multiprocessing.Process(
            target=_conversionWorker,
            args=(
                inputPath,
                outputPath,
                resultQueue,
            ),
        )

        process.start()

        # ====================================================
        # WAIT FOR WORKER
        # ====================================================

        process.join(
            self.conversionTimeout
        )

        # ====================================================
        # WORKER FINISHED
        # ====================================================

        if not process.is_alive():

            try:
                result = (
                    resultQueue.get_nowait()
                )

            except queue.Empty:

                result = {
                    'status': 'failed',
                    'stage': 'worker',
                    'reason': (
                        'Conversion worker exited '
                        'without returning a result.'
                    ),
                }

            resultQueue.close()
            resultQueue.join_thread()

            return result

        # ====================================================
        # TIMEOUT
        # ====================================================

        process.terminate()

        process.join(10)

        if process.is_alive():
            process.kill()
            process.join()

        resultQueue.close()
        resultQueue.join_thread()

        return {
            'status': 'timeout',
            'stage': 'conversion',
            'reason': (
                'Conversion exceeded '
                f'{self.conversionTimeout} seconds.'
            ),
        }

    # ========================================================
    # RESULT HANDLING
    # ========================================================

    def _processResult(
        self,
        inputPath,
        result,
        results,
    ):
        status = result.get(
            'status'
        )

        # ====================================================
        # CONVERTED
        # ====================================================

        if status == 'converted':

            outputPath = result[
                'outputPath'
            ]

            results['converted'].append({
                'sourcePath': inputPath,
                'outputPath': outputPath,
            })

            if self.deleteOriginal:
                self._deleteOriginal(
                    inputPath,
                    results,
                )

            return

        # ====================================================
        # TIMEOUT
        # ====================================================

        if status == 'timeout':

            results['failed'].append({
                'filePath': inputPath,
                'stage': 'conversion',
                'reason': (
                    'Conversion timed out after '
                    f'{self.conversionTimeout} seconds. '
                    'The Office process was terminated. '
                    'The file may be password protected '
                    'or otherwise causing Office to hang.'
                ),
            })

            return

        # ====================================================
        # FAILED
        # ====================================================

        if status == 'failed':

            results['failed'].append({
                'filePath': inputPath,
                'stage': result.get(
                    'stage',
                    'conversion',
                ),
                'reason': result.get(
                    'reason',
                    'Unknown conversion error',
                ),
            })

            return

        # ====================================================
        # SKIPPED
        # ====================================================

        if status == 'skipped':

            results['skipped'].append({
                'filePath': inputPath,
                'reason': result.get(
                    'reason',
                    'Skipped',
                ),
            })

    # ========================================================
    # DELETE ORIGINAL
    # ========================================================

    def _deleteOriginal(
        self,
        inputPath,
        results,
    ):
        try:

            os.remove(
                inputPath
            )

            results['deleted'].append(
                inputPath
            )

        except OSError as exception:

            results['failed'].append({
                'filePath': inputPath,
                'stage': 'delete',
                'reason': str(
                    exception
                ),
            })

    # ========================================================
    # PDF PATH HELPERS
    # ========================================================

    def _getOutputPath(self, inputPath):
        return (
            os.path.splitext(
                inputPath
            )[0]
            + '.pdf'
        )

    def _getUniquePdfPath(
        self,
        outputPath,
    ):
        if not os.path.exists(
            outputPath
        ):
            return outputPath

        base, extension = os.path.splitext(
            outputPath
        )

        index = 2

        while True:

            candidate = (
                f'{base}_{index}{extension}'
            )

            if not os.path.exists(
                candidate
            ):
                return candidate

            index += 1


# ============================================================
# OFFICE WORKER
# ============================================================

def _conversionWorker(
    inputPath,
    outputPath,
    resultQueue,
):
    """
    Runs inside a separate process.

    This must remain a module-level function
    because multiprocessing on Windows uses
    the spawn start method.
    """

    pythoncom.CoInitialize()

    wordApplication = None
    powerpointApplication = None

    document = None
    presentation = None

    try:

        extension = os.path.splitext(
            inputPath
        )[1].lower()

        # ====================================================
        # WORD
        # ====================================================

        if extension in (
            ConvertToPdfService.WORD_EXTENSIONS
        ):

            wordApplication = (
                win32com.client.DispatchEx(
                    'Word.Application'
                )
            )

            wordApplication.Visible = False
            wordApplication.DisplayAlerts = False

            try:
                wordApplication.AutomationSecurity = 3
            except Exception:
                pass

            # ------------------------------------------------
            # IMPORTANT:
            #
            # Use positional arguments here rather than
            # UpdateLinks=..., ReadOnly=..., etc.
            #
            # Some pywin32 Word installations do not expose
            # every COM argument as a Python keyword.
            # ------------------------------------------------

            document = (
                wordApplication.Documents.Open(
                    inputPath,
                    ReadOnly=True,
                    AddToRecentFiles=False,
                    ConfirmConversions=False,
                )
            )

            document.ExportAsFixedFormat(
                OutputFileName=outputPath,
                ExportFormat=(
                    ConvertToPdfService.WORD_PDF_FORMAT
                ),
            )

            document.Close(False)
            document = None

        # ====================================================
        # POWERPOINT
        # ====================================================

        elif extension in (
            ConvertToPdfService.POWERPOINT_EXTENSIONS
        ):

            powerpointApplication = (
                win32com.client.DispatchEx(
                    'PowerPoint.Application'
                )
            )

            powerpointApplication.DisplayAlerts = False

            presentation = (
                powerpointApplication
                .Presentations.Open(
                    inputPath,
                    ReadOnly=True,
                    WithWindow=False,
                )
            )

            presentation.SaveAs(
                outputPath,
                ConvertToPdfService.POWERPOINT_PDF_FORMAT,
            )

            presentation.Close()
            presentation = None

        # ====================================================
        # UNSUPPORTED
        # ====================================================

        else:

            resultQueue.put({
                'status': 'skipped',
                'reason': (
                    f'Unsupported file type: '
                    f'{extension}'
                ),
            })

            return

        # ====================================================
        # VERIFY OUTPUT
        # ====================================================

        if not os.path.isfile(
            outputPath
        ):

            raise RuntimeError(
                'Office reported success, but the PDF '
                'was not created.'
            )

        resultQueue.put({
            'status': 'converted',
            'outputPath': outputPath,
        })

    except Exception as exception:

        resultQueue.put({
            'status': 'failed',
            'stage': 'conversion',
            'reason': (
                f'{type(exception).__name__}: '
                f'{exception}'
            ),
        })

    finally:

        # ====================================================
        # CLOSE WORD DOCUMENT
        # ====================================================

        if document is not None:

            try:
                document.Close(
                    False
                )
            except Exception:
                pass

        # ====================================================
        # CLOSE POWERPOINT PRESENTATION
        # ====================================================

        if presentation is not None:

            try:
                presentation.Close()
            except Exception:
                pass

        # ====================================================
        # QUIT WORD
        # ====================================================

        if wordApplication is not None:

            try:
                wordApplication.Quit()
            except Exception:
                pass

        # ====================================================
        # QUIT POWERPOINT
        # ====================================================

        if powerpointApplication is not None:

            try:
                powerpointApplication.Quit()
            except Exception:
                pass

        # ====================================================
        # COM CLEANUP
        # ====================================================

        pythoncom.CoUninitialize()


# ============================================================
# WINDOWS ENTRY POINT
# ============================================================

if __name__ == '__main__':
    multiprocessing.freeze_support()
