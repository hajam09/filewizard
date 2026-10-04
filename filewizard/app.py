import customtkinter as ctk

from filewizard.features import FEATURES
from filewizard.views.FilesCounterView import FilesCounterView
from filewizard.views.coming_soon import ComingSoonView
from filewizard.views.convert_pdf_view import ConvertPdfView
from filewizard.views.DeleteEmptyFoldersView import DeleteEmptyFoldersView
from filewizard.views.home import HomeView


class FileWizardApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title('File Wizard')
        self.geometry('980x720')
        self.minsize(840, 620)

        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('blue')

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.views = {}
        self._build_views()
        self.show_view('home')

    def _build_views(self):
        self.views['home'] = HomeView(
            self,
            features=FEATURES,
            on_open_feature=self.open_feature,
        )
        self.views['conver_office_files_to_pdf'] = ConvertPdfView(
            self,
            on_back=lambda: self.show_view('home'),
        )
        self.views['delete_empty_folders'] = DeleteEmptyFoldersView(
            self,
            on_back=lambda: self.show_view('home'),
        )

        self.views['files_counter'] = FilesCounterView(
            self,
            on_back=lambda: self.show_view('home'),
        )

        for feature in FEATURES:
            if feature['ready']:
                continue

            self.views[feature['id']] = ComingSoonView(
                self,
                title=feature['title'],
                on_back=lambda: self.show_view('home'),
            )

        for view in self.views.values():
            view.grid(row=0, column=0, sticky='nsew')

    def open_feature(self, feature_id):
        self.show_view(feature_id)

    def show_view(self, view_name):
        view = self.views[view_name]
        view.tkraise()
        view.focus_set()


def main():
    app = FileWizardApp()
    app.mainloop()
