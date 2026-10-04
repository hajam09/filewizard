import os


class DeleteEmptyFolderService:

    def __init__(
        self,
        folderPath,
        includeSubfolders=False,
        dryRun=True,
        progressCallback=None,
    ):
        self.folderPath = os.path.abspath(folderPath)
        self.includeSubfolders = includeSubfolders
        self.dryRun = dryRun
        self.progressCallback = progressCallback

    def _findEmptyFolders(self):
        emptyFolders = []

        for dirPath, dirNames, fileNames in os.walk(
            self.folderPath,
            topdown=False,
        ):
            if dirPath == self.folderPath:
                continue

            if not dirNames and not fileNames:
                emptyFolders.append(dirPath)

        return emptyFolders

    def _isFolderEmpty(self, folderPath):
        try:
            with os.scandir(folderPath) as entries:
                return next(entries, None) is None
        except OSError:
            return False

    def _reportProgress(self, current, total, folderPath):
        if self.progressCallback:
            self.progressCallback(
                current,
                total,
                folderPath,
            )

    def _createResults(self):
        return {
            "folderPath": self.folderPath,
            "total": 0,
            "deleted": [],
            "failed": [],
            "dryRun": self.dryRun,
        }

    def _checkRootFolder(self, results):
        if not self._isFolderEmpty(self.folderPath):
            return results

        results["total"] = 1

        self._reportProgress(
            1,
            1,
            self.folderPath,
        )

        if self.dryRun:
            results["deleted"].append(self.folderPath)
            return results

        try:
            os.rmdir(self.folderPath)
            results["deleted"].append(self.folderPath)
        except OSError as exception:
            results["failed"].append({
                "filePath": self.folderPath,
                "reason": str(exception),
            })

        return results

    def _deleteEmptyFolders(self, emptyFolders, results):
        total = len(emptyFolders)

        for current, emptyFolder in enumerate(
            emptyFolders,
            start=1,
        ):
            self._reportProgress(
                current,
                total,
                emptyFolder,
            )

            try:
                os.rmdir(emptyFolder)
                results["deleted"].append(emptyFolder)
                results["total"] += 1
            except OSError as exception:
                results["failed"].append({
                    "filePath": emptyFolder,
                    "reason": str(exception),
                })

    def execute(self):
        if not os.path.isdir(self.folderPath):
            raise ValueError(
                f"Folder does not exist: {self.folderPath}"
            )

        results = self._createResults()

        if not self.includeSubfolders:
            return self._checkRootFolder(results)

        if self.dryRun:
            emptyFolders = self._findEmptyFolders()
            results["total"] = len(emptyFolders)

            for current, emptyFolder in enumerate(
                emptyFolders,
                start=1,
            ):
                self._reportProgress(
                    current,
                    len(emptyFolders),
                    emptyFolder,
                )

                results["deleted"].append(emptyFolder)

            return results

        while True:
            emptyFolders = self._findEmptyFolders()

            if not emptyFolders:
                break

            self._deleteEmptyFolders(
                emptyFolders,
                results,
            )

        return results
