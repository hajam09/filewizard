import os
import shutil


class OrganizeFilesService:

    def __init__(
        self,
        folderPath,
        includeSubfolders=False,
        dryRun=True,
        progressCallback=None,
    ):
        self.folderPath = os.path.abspath(
            folderPath
        )

        self.includeSubfolders = (
            includeSubfolders
        )

        self.dryRun = dryRun

        self.progressCallback = (
            progressCallback
        )

        self.filesFolder = os.path.join(
            self.folderPath,
            'files',
        )

    def execute(self):
        self._validateFolder()

        files = self._getFiles()

        totalFiles = len(files)

        organized = []
        failed = []

        for current, filePath in enumerate(
            files,
            start=1,
        ):
            fileName = os.path.basename(
                filePath
            )

            extension = self._getFileExtension(
                fileName
            )

            destinationFolder = os.path.join(
                self.filesFolder,
                extension,
            )

            destinationPath = (
                self._getAvailablePath(
                    destinationFolder,
                    fileName,
                )
            )

            if self.progressCallback:
                self.progressCallback(
                    current,
                    totalFiles,
                    filePath,
                )

            if self.dryRun:
                organized.append({
                    'filePath': filePath,
                    'fileName': fileName,
                    'destination': destinationPath,
                    'newName': os.path.basename(
                        destinationPath
                    ),
                })
                continue

            try:
                os.makedirs(
                    self.long_path(destinationFolder),
                    exist_ok=True,
                )

                shutil.move(
                    self.long_path(filePath),
                    self.long_path(destinationPath),
                )

                organized.append({
                    'filePath': filePath,
                    'fileName': fileName,
                    'destination': destinationPath,
                    'newName': os.path.basename(
                        destinationPath
                    ),
                })

            except OSError as exception:
                failed.append({
                    'filePath': filePath,
                    'reason': str(exception),
                })

        return {
            'folderPath': self.folderPath,
            'total': totalFiles,
            'organized': organized,
            'failed': failed,
            'dryRun': self.dryRun,
            'includeSubfolders': (
                self.includeSubfolders
            ),
        }

    def _validateFolder(self):
        if not os.path.isdir(
            self.long_path(self.folderPath)
        ):
            raise ValueError(
                f'Folder does not exist: '
                f'{self.folderPath}'
            )

    def _getFiles(self):
        files = []

        filesFolderPath = os.path.abspath(
            self.filesFolder
        )

        if self.includeSubfolders:
            for root, dirs, fileNames in os.walk(
                self.long_path(self.folderPath)
            ):
                currentRoot = os.path.abspath(
                    root
                )

                dirs[:] = [
                    directory
                    for directory in dirs
                    if os.path.abspath(
                        os.path.join(
                            currentRoot,
                            directory,
                        )
                    ) != filesFolderPath
                ]

                for fileName in fileNames:
                    filePath = os.path.join(
                        currentRoot,
                        fileName,
                    )

                    if os.path.isfile(
                        self.long_path(filePath)
                    ):
                        files.append(
                            filePath
                        )

        else:
            try:
                for fileName in os.listdir(
                    self.long_path(self.folderPath)
                ):
                    filePath = os.path.join(
                        self.folderPath,
                        fileName,
                    )

                    if os.path.isfile(
                        self.long_path(filePath)
                    ):
                        files.append(
                            filePath
                        )

            except OSError as exception:
                raise OSError(
                    f'Unable to read folder '
                    f'{self.folderPath}: {exception}'
                ) from exception

        return files

    def _getFileExtension(self, fileName):
        extension = os.path.splitext(
            fileName
        )[1].lower().lstrip('.')

        if not extension:
            return 'no_extension'

        return extension

    def _getAvailablePath(
        self,
        destinationFolder,
        fileName,
    ):
        destinationPath = os.path.join(
            destinationFolder,
            fileName,
        )

        if not os.path.exists(
            self.long_path(destinationPath)
        ):
            return destinationPath

        baseName, extension = os.path.splitext(
            fileName
        )

        counter = 1

        while True:
            newName = (
                f'{baseName}_{counter}'
                f'{extension}'
            )

            destinationPath = os.path.join(
                destinationFolder,
                newName,
            )

            if not os.path.exists(
                self.long_path(destinationPath)
            ):
                return destinationPath

            counter += 1


    def long_path(self, path):
        path = os.path.abspath(path)

        if not path.startswith(
            '\\\\?\\'
        ):
            return '\\\\?\\' + path

        return path
