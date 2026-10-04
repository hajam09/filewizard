import os
import random
import string


class RenameFilesService:

    SORT_NONE = 'none'
    SORT_FILE_TYPE = 'file_type'
    SORT_SIZE_ASC = 'size_asc'
    SORT_SIZE_DESC = 'size_desc'

    def __init__(
        self,
        folderPath,
        prefix='',
        sortBy=SORT_NONE,
        includeSubfolders=False,
        dryRun=True,
        progressCallback=None,
    ):
        self.folderPath = os.path.abspath(
            folderPath
        )

        self.prefix = prefix.strip()

        self.sortBy = sortBy

        self.includeSubfolders = (
            includeSubfolders
        )

        self.dryRun = dryRun

        self.progressCallback = (
            progressCallback
        )

    def execute(self):
        self._validateFolder()

        folders = self._getFolders()

        prefix = (
            self.prefix
            or self._generatePrefix()
        )

        renamed = []
        failed = []

        filesByFolder = []

        for folderPath in folders:
            files = self._getFiles(
                folderPath
            )

            if not files:
                continue

            files = self._sortFiles(
                files,
                folderPath,
            )

            filesByFolder.append(
                (
                    folderPath,
                    files,
                )
            )

        totalFiles = sum(
            len(files)
            for _, files in filesByFolder
        )

        current = 0

        for folderPath, files in filesByFolder:
            for index, fileName in enumerate(
                files,
                start=1,
            ):
                current += 1

                filePath = os.path.join(
                    folderPath,
                    fileName,
                )

                newName = self._buildNewName(
                    prefix,
                    index,
                    fileName,
                )

                newPath = os.path.join(
                    folderPath,
                    newName,
                )

                if self.progressCallback:
                    self.progressCallback(
                        current,
                        totalFiles,
                        filePath,
                    )

                if fileName == newName:
                    renamed.append({
                        'filePath': filePath,
                        'oldName': fileName,
                        'newName': newName,
                    })
                    continue

                if self.dryRun:
                    renamed.append({
                        'filePath': filePath,
                        'oldName': fileName,
                        'newName': newName,
                    })
                    continue

                try:
                    if os.path.exists(newPath):
                        raise FileExistsError(
                            f'Target file already exists: '
                            f'{newPath}'
                        )

                    os.rename(
                        filePath,
                        newPath,
                    )

                    renamed.append({
                        'filePath': newPath,
                        'oldName': fileName,
                        'newName': newName,
                    })

                except OSError as exception:
                    failed.append({
                        'filePath': filePath,
                        'reason': str(exception),
                    })

        return {
            'folderPath': self.folderPath,
            'total': totalFiles,
            'renamed': renamed,
            'failed': failed,
            'dryRun': self.dryRun,
            'prefix': prefix,
            'sortBy': self.sortBy,
            'includeSubfolders': (
                self.includeSubfolders
            ),
        }

    def _validateFolder(self):
        if not os.path.isdir(
            self.folderPath
        ):
            raise ValueError(
                f'Folder does not exist: '
                f'{self.folderPath}'
            )

    def _getFolders(self):
        if not self.includeSubfolders:
            return [
                self.folderPath
            ]

        folders = []

        for root, _, _ in os.walk(
            self.folderPath
        ):
            folders.append(root)

        return folders

    def _getFiles(self, folderPath):
        files = []

        try:
            for fileName in os.listdir(
                folderPath
            ):
                filePath = os.path.join(
                    folderPath,
                    fileName,
                )

                if os.path.isfile(
                    filePath
                ):
                    files.append(
                        fileName
                    )

        except OSError as exception:
            raise OSError(
                f'Unable to read folder '
                f'{folderPath}: {exception}'
            ) from exception

        return files

    def _sortFiles(
        self,
        files,
        folderPath,
    ):
        if self.sortBy == self.SORT_NONE:
            return files

        if self.sortBy == self.SORT_FILE_TYPE:
            return sorted(
                files,
                key=lambda fileName: (
                    self._getFileExtension(
                        fileName
                    ),
                    fileName.lower(),
                ),
            )

        if self.sortBy == self.SORT_SIZE_ASC:
            return sorted(
                files,
                key=lambda fileName: (
                    self._getFileSize(
                        folderPath,
                        fileName,
                    ),
                    fileName.lower(),
                ),
            )

        if self.sortBy == self.SORT_SIZE_DESC:
            return sorted(
                files,
                key=lambda fileName: (
                    self._getFileSize(
                        folderPath,
                        fileName,
                    ),
                    fileName.lower(),
                ),
                reverse=True,
            )

        raise ValueError(
            f'Unknown sort option: '
            f'{self.sortBy}'
        )

    def _getFileExtension(self, fileName):
        extension = os.path.splitext(
            fileName
        )[1]

        if not extension:
            return ''

        return extension.lower()

    def _getFileSize(
        self,
        folderPath,
        fileName,
    ):
        filePath = os.path.join(
            folderPath,
            fileName,
        )

        try:
            return os.path.getsize(
                filePath
            )

        except OSError:
            return 0

    def _buildNewName(
        self,
        prefix,
        index,
        fileName,
    ):
        extension = os.path.splitext(
            fileName
        )[1]

        return (
            f'{prefix}-{index}{extension}'
        )

    def _generatePrefix(self):
        return ''.join(
            random.choices(
                string.ascii_uppercase,
                k=3,
            )
        )
