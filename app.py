import sys
from pathlib import Path

import pymupdf

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QSplitter,
    QScrollArea,
    QTextEdit,
    QSpinBox,
)


from search_engine import search_documents


class DocumentViewer(QWidget):
    """
    Flexible document preview component.

    Supports:
        - JPG
        - JPEG
        - PNG
        - PDF
        - TXT

    Controls:
        - Zoom In
        - Zoom Out
        - 100%
        - Fit Page
        - Fit Width
        - Actual Size
        - Fullscreen
        - PDF page navigation
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_file = None
        self.file_type = None

        # Image state
        self.image_pixmap = None

        # PDF state
        self.pdf_document = None
        self.pdf_page_number = 0
        self.pdf_page_count = 0

        # Zoom
        self.zoom_factor = 1.0

        # Fullscreen
        self.is_fullscreen = False

        self.setup_ui()

    # =========================================================
    # UI
    # =========================================================

    def setup_ui(self):

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        # -----------------------------------------------------
        # TOOLBAR
        # -----------------------------------------------------

        toolbar = QHBoxLayout()
        toolbar.setSpacing(5)

        self.zoom_out_button = QPushButton("−")
        self.zoom_out_button.setToolTip("Zoom Out")

        self.zoom_label = QLabel("100%")
        self.zoom_label.setAlignment(Qt.AlignCenter)
        self.zoom_label.setMinimumWidth(55)

        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setToolTip("Zoom In")

        self.fit_page_button = QPushButton("Fit Page")
        self.fit_width_button = QPushButton("Fit Width")
        self.actual_size_button = QPushButton("Actual Size")

        self.previous_button = QPushButton("◀")
        self.previous_button.setToolTip("Previous Page")

        self.page_label = QLabel("Page 0 / 0")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setMinimumWidth(90)

        self.next_button = QPushButton("▶")
        self.next_button.setToolTip("Next Page")

        self.fullscreen_button = QPushButton("⛶")
        self.fullscreen_button.setToolTip(
            "Fullscreen Preview"
        )

        toolbar.addWidget(
            self.zoom_out_button
        )

        toolbar.addWidget(
            self.zoom_label
        )

        toolbar.addWidget(
            self.zoom_in_button
        )

        toolbar.addSpacing(10)

        toolbar.addWidget(
            self.fit_page_button
        )

        toolbar.addWidget(
            self.fit_width_button
        )

        toolbar.addWidget(
            self.actual_size_button
        )

        toolbar.addSpacing(10)

        toolbar.addWidget(
            self.previous_button
        )

        toolbar.addWidget(
            self.page_label
        )

        toolbar.addWidget(
            self.next_button
        )

        toolbar.addStretch()

        toolbar.addWidget(
            self.fullscreen_button
        )

        main_layout.addLayout(toolbar)

        # -----------------------------------------------------
        # SCROLL AREA
        # -----------------------------------------------------

        self.scroll_area = QScrollArea()

        self.scroll_area.setWidgetResizable(True)

        self.scroll_area.setAlignment(
            Qt.AlignCenter
        )

        self.content_widget = QWidget()

        self.content_layout = QVBoxLayout(
            self.content_widget
        )

        self.content_layout.setAlignment(
            Qt.AlignCenter
        )

        self.scroll_area.setWidget(
            self.content_widget
        )

        main_layout.addWidget(
            self.scroll_area
        )

        self.setLayout(main_layout)

        # -----------------------------------------------------
        # BUTTON CONNECTIONS
        # -----------------------------------------------------

        self.zoom_out_button.clicked.connect(
            self.zoom_out
        )

        self.zoom_in_button.clicked.connect(
            self.zoom_in
        )

        self.fit_page_button.clicked.connect(
            self.fit_page
        )

        self.fit_width_button.clicked.connect(
            self.fit_width
        )

        self.actual_size_button.clicked.connect(
            self.actual_size
        )

        self.previous_button.clicked.connect(
            self.previous_pdf_page
        )

        self.next_button.clicked.connect(
            self.next_pdf_page
        )

        self.fullscreen_button.clicked.connect(
            self.toggle_fullscreen
        )

        # Initially disabled until a PDF is loaded.
        self.set_pdf_controls_enabled(False)

    # =========================================================
    # OPEN FILE
    # =========================================================

    def open_file(self, file_path: str):
        """
        Open a file in the appropriate viewer.
        """

        self.clear_viewer()

        path = Path(file_path)

        if not path.exists():

            self.show_message(
                "File does not exist."
            )

            return

        self.current_file = str(path)

        extension = path.suffix.lower()

        if extension in {
            ".jpg",
            ".jpeg",
            ".png",
        }:

            self.file_type = "image"

            self.open_image(
                str(path)
            )

        elif extension == ".pdf":

            self.file_type = "pdf"

            self.open_pdf(
                str(path)
            )

        elif extension == ".txt":

            self.file_type = "text"

            self.open_text(
                str(path)
            )

        else:

            self.file_type = "unsupported"

            self.show_message(
                "Preview for this file type "
                "will be added next."
            )

    # =========================================================
    # CLEAR
    # =========================================================

    def clear_viewer(self):
        """
        Remove current preview.
        """

        self.current_file = None
        self.file_type = None

        self.image_pixmap = None

        if self.pdf_document is not None:

            self.pdf_document.close()

        self.pdf_document = None

        self.pdf_page_number = 0
        self.pdf_page_count = 0

        self.zoom_factor = 1.0

        self.page_label.setText(
            "Page 0 / 0"
        )

        self.set_pdf_controls_enabled(
            False
        )

        while self.content_layout.count():

            item = self.content_layout.takeAt(0)

            widget = item.widget()

            if widget:
                widget.deleteLater()

    # =========================================================
    # IMAGE
    # =========================================================

    def open_image(
        self,
        file_path: str
    ):
        """
        Load an image.
        """

        pixmap = QPixmap(
            file_path
        )

        if pixmap.isNull():

            self.show_message(
                "Unable to load image."
            )

            return

        self.image_pixmap = pixmap

        self.zoom_factor = 1.0

        self.set_pdf_controls_enabled(
            False
        )

        self.display_image()

    def display_image(self):
        """
        Display the image using the current zoom.
        """

        if self.image_pixmap is None:
            return

        image_label = self.get_or_create_image_label()

        if self.zoom_factor == -1:

            # Fit page
            viewport = (
                self.scroll_area.viewport()
            )

            target_width = max(
                viewport.width() - 30,
                100
            )

            target_height = max(
                viewport.height() - 30,
                100
            )

            scaled = self.image_pixmap.scaled(
                target_width,
                target_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

        elif self.zoom_factor == -2:

            # Fit width
            viewport = (
                self.scroll_area.viewport()
            )

            target_width = max(
                viewport.width() - 30,
                100
            )

            scaled = self.image_pixmap.scaledToWidth(
                target_width,
                Qt.SmoothTransformation
            )

        else:

            # Explicit zoom
            width = int(
                self.image_pixmap.width()
                * self.zoom_factor
            )

            height = int(
                self.image_pixmap.height()
                * self.zoom_factor
            )

            scaled = self.image_pixmap.scaled(
                width,
                height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

        image_label.setPixmap(
            scaled
        )

        self.update_zoom_label()

    # =========================================================
    # IMAGE LABEL
    # =========================================================

    def get_or_create_image_label(self):

        if hasattr(
            self,
            "image_label"
        ):

            return self.image_label

        self.image_label = QLabel()

        self.image_label.setAlignment(
            Qt.AlignCenter
        )

        self.content_layout.addWidget(
            self.image_label
        )

        return self.image_label

    # =========================================================
    # PDF
    # =========================================================

    def open_pdf(
        self,
        file_path: str
    ):
        """
        Open a PDF.
        """

        try:

            self.pdf_document = pymupdf.open(
                file_path
            )

            self.pdf_page_count = (
                len(self.pdf_document)
            )

            if self.pdf_page_count == 0:

                self.show_message(
                    "PDF contains no pages."
                )

                return

            self.pdf_page_number = 0

            self.zoom_factor = -1

            self.set_pdf_controls_enabled(
                True
            )

            self.display_pdf_page()

        except Exception as error:

            self.show_message(
                f"Could not open PDF:\n{error}"
            )

    # =========================================================
    # DISPLAY PDF PAGE
    # =========================================================

    def display_pdf_page(self):
        """
        Render the current PDF page.
        """

        if self.pdf_document is None:
            return

        page = self.pdf_document[
            self.pdf_page_number
        ]

        # Render PDF at high resolution.
        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(
                2,
                2
            ),
            alpha=False
        )

        image = QPixmap()

        image.loadFromData(
            pixmap.tobytes("png")
        )

        self.pdf_pixmap = image

        page_label = self.get_or_create_pdf_label()

        if self.zoom_factor == -1:

            # Fit page
            viewport = (
                self.scroll_area.viewport()
            )

            target_width = max(
                viewport.width() - 30,
                100
            )

            target_height = max(
                viewport.height() - 30,
                100
            )

            scaled = image.scaled(
                target_width,
                target_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

        elif self.zoom_factor == -2:

            # Fit width
            viewport = (
                self.scroll_area.viewport()
            )

            target_width = max(
                viewport.width() - 30,
                100
            )

            scaled = image.scaledToWidth(
                target_width,
                Qt.SmoothTransformation
            )

        else:

            width = int(
                image.width()
                * self.zoom_factor
            )

            height = int(
                image.height()
                * self.zoom_factor
            )

            scaled = image.scaled(
                width,
                height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

        page_label.setPixmap(
            scaled
        )

        self.page_label.setText(
            f"Page {self.pdf_page_number + 1} "
            f"/ {self.pdf_page_count}"
        )

        self.update_zoom_label()

    # =========================================================
    # PDF LABEL
    # =========================================================

    def get_or_create_pdf_label(self):

        if hasattr(
            self,
            "pdf_page_label"
        ):

            return self.pdf_page_label

        self.pdf_page_label = QLabel()

        self.pdf_page_label.setAlignment(
            Qt.AlignCenter
        )

        self.content_layout.addWidget(
            self.pdf_page_label
        )

        return self.pdf_page_label

    # =========================================================
    # TEXT
    # =========================================================

    def open_text(
        self,
        file_path: str
    ):
        """
        Open TXT file.
        """

        try:

            text = Path(
                file_path
            ).read_text(
                encoding="utf-8",
                errors="ignore"
            )

            self.text_editor = QTextEdit()

            self.text_editor.setReadOnly(
                True
            )

            self.text_editor.setPlainText(
                text
            )

            font = QFont()
            font.setPointSize(12)

            self.text_editor.setFont(
                font
            )

            self.content_layout.addWidget(
                self.text_editor
            )

            self.text_editor.setFocus()

            self.zoom_factor = 1.0

            self.update_zoom_label()

        except Exception as error:

            self.show_message(
                f"Could not open text file:\n{error}"
            )

    # =========================================================
    # ZOOM IN
    # =========================================================

    def zoom_in(self):

        if self.file_type not in {
            "image",
            "pdf",
            "text",
        }:

            return

        # For Fit modes, start at 100%.
        if self.zoom_factor < 0:

            self.zoom_factor = 1.0

        else:

            self.zoom_factor += 0.25

        self.zoom_factor = min(
            self.zoom_factor,
            5.0
        )

        self.refresh_view()

    # =========================================================
    # ZOOM OUT
    # =========================================================

    def zoom_out(self):

        if self.file_type not in {
            "image",
            "pdf",
            "text",
        }:

            return

        if self.zoom_factor < 0:

            self.zoom_factor = 1.0

        else:

            self.zoom_factor -= 0.25

        self.zoom_factor = max(
            self.zoom_factor,
            0.25
        )

        self.refresh_view()

    # =========================================================
    # 100%
    # =========================================================

    def actual_size(self):

        if self.file_type not in {
            "image",
            "pdf",
            "text",
        }:

            return

        self.zoom_factor = 1.0

        if self.file_type == "text":

            self.set_text_font_size(
                12
            )

        self.refresh_view()

    # =========================================================
    # FIT PAGE
    # =========================================================

    def fit_page(self):

        if self.file_type not in {
            "image",
            "pdf",
        }:

            return

        self.zoom_factor = -1

        self.refresh_view()

    # =========================================================
    # FIT WIDTH
    # =========================================================

    def fit_width(self):

        if self.file_type not in {
            "image",
            "pdf",
        }:

            return

        self.zoom_factor = -2

        self.refresh_view()

    # =========================================================
    # REFRESH
    # =========================================================

    def refresh_view(self):

        if self.file_type == "image":

            self.display_image()

        elif self.file_type == "pdf":

            self.display_pdf_page()

        elif self.file_type == "text":

            self.update_text_zoom()

        self.update_zoom_label()

    # =========================================================
    # TEXT ZOOM
    # =========================================================

    def update_text_zoom(self):

        if not hasattr(
            self,
            "text_editor"
        ):

            return

        if self.zoom_factor < 0:

            self.zoom_factor = 1.0

        font_size = int(
            12 * self.zoom_factor
        )

        font_size = max(
            8,
            min(font_size, 48)
        )

        self.set_text_font_size(
            font_size
        )

    def set_text_font_size(
        self,
        font_size: int
    ):

        if not hasattr(
            self,
            "text_editor"
        ):

            return

        font = self.text_editor.font()

        font.setPointSize(
            font_size
        )

        self.text_editor.setFont(
            font
        )

    # =========================================================
    # UPDATE ZOOM LABEL
    # =========================================================

    def update_zoom_label(self):

        if self.zoom_factor == -1:

            self.zoom_label.setText(
                "Fit"
            )

        elif self.zoom_factor == -2:

            self.zoom_label.setText(
                "Fit Width"
            )

        else:

            percentage = int(
                self.zoom_factor * 100
            )

            self.zoom_label.setText(
                f"{percentage}%"
            )

    # =========================================================
    # PREVIOUS PDF PAGE
    # =========================================================

    def previous_pdf_page(self):

        if self.file_type != "pdf":
            return

        if self.pdf_page_number <= 0:
            return

        self.pdf_page_number -= 1

        self.display_pdf_page()

    # =========================================================
    # NEXT PDF PAGE
    # =========================================================

    def next_pdf_page(self):

        if self.file_type != "pdf":
            return

        if (
            self.pdf_page_number
            >= self.pdf_page_count - 1
        ):

            return

        self.pdf_page_number += 1

        self.display_pdf_page()

    # =========================================================
    # PDF CONTROLS
    # =========================================================

    def set_pdf_controls_enabled(
        self,
        enabled: bool
    ):

        self.previous_button.setEnabled(
            enabled
        )

        self.next_button.setEnabled(
            enabled
        )

        self.page_label.setVisible(
            enabled
        )

    # =========================================================
    # FULLSCREEN
    # =========================================================

    def toggle_fullscreen(self):

        if self.is_fullscreen:

            self.showNormal()

            self.is_fullscreen = False

            self.fullscreen_button.setText(
                "⛶"
            )

        else:

            self.showFullScreen()

            self.is_fullscreen = True

            self.fullscreen_button.setText(
                "🗗"
            )

    # =========================================================
    # MESSAGE
    # =========================================================

    def show_message(
        self,
        message: str
    ):

        label = QLabel(
            message
        )

        label.setAlignment(
            Qt.AlignCenter
        )

        label.setWordWrap(
            True
        )

        label.setStyleSheet(
            """
            QLabel {
                font-size: 16px;
                padding: 20px;
            }
            """
        )

        self.content_layout.addWidget(
            label
        )

    # =========================================================
    # WINDOW RESIZE
    # =========================================================

    def resizeEvent(self, event):

        super().resizeEvent(
            event
        )

        if self.file_type in {
            "image",
            "pdf",
        }:

            if self.zoom_factor in {
                -1,
                -2,
            }:

                self.refresh_view()


# =============================================================
# MAIN APPLICATION
# =============================================================


class DocumentFinderApp(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "Smart Document Fetch"
        )

        self.resize(
            1300,
            800
        )

        self.setup_ui()

    # =========================================================
    # MAIN UI
    # =========================================================

    def setup_ui(self):

        main_layout = QVBoxLayout()

        main_layout.setContentsMargins(
            15,
            15,
            15,
            15
        )

        main_layout.setSpacing(
            10
        )

        # -----------------------------------------------------
        # TITLE
        # -----------------------------------------------------

        title = QLabel(
            "Smart Document Fetch"
        )

        title.setStyleSheet(
            """
            QLabel {
                font-size: 30px;
                font-weight: bold;
                padding: 5px;
            }
            """
        )

        main_layout.addWidget(
            title
        )

        # -----------------------------------------------------
        # SEARCH BAR
        # -----------------------------------------------------

        search_layout = QHBoxLayout()

        self.search_box = QLineEdit()

        self.search_box.setPlaceholderText(
            "Example: give me my PAN card"
        )

        self.search_box.setMinimumHeight(
            40
        )

        self.search_button = QPushButton(
            "Search"
        )

        self.search_button.setMinimumHeight(
            40
        )

        self.search_box.returnPressed.connect(
            self.perform_search
        )

        self.search_button.clicked.connect(
            self.perform_search
        )

        search_layout.addWidget(
            self.search_box
        )

        search_layout.addWidget(
            self.search_button
        )

        main_layout.addLayout(
            search_layout
        )

        # -----------------------------------------------------
        # SPLITTER
        # -----------------------------------------------------

        splitter = QSplitter(
            Qt.Horizontal
        )

        # =====================================================
        # LEFT: RESULTS
        # =====================================================

        results_container = QWidget()

        results_layout = QVBoxLayout()

        results_title = QLabel(
            "Search Results"
        )

        results_title.setStyleSheet(
            """
            QLabel {
                font-size: 20px;
                font-weight: bold;
            }
            """
        )

        results_layout.addWidget(
            results_title
        )

        self.results_list = QListWidget()

        self.results_list.setSpacing(
            5
        )

        self.results_list.itemClicked.connect(
            self.preview_selected_file
        )

        results_layout.addWidget(
            self.results_list
        )

        results_container.setLayout(
            results_layout
        )

        # =====================================================
        # RIGHT: VIEWER
        # =====================================================

        preview_container = QWidget()

        preview_layout = QVBoxLayout()

        preview_title = QLabel(
            "Document Preview"
        )

        preview_title.setStyleSheet(
            """
            QLabel {
                font-size: 20px;
                font-weight: bold;
            }
            """
        )

        preview_layout.addWidget(
            preview_title
        )

        self.document_viewer = (
            DocumentViewer()
        )

        preview_layout.addWidget(
            self.document_viewer
        )

        preview_container.setLayout(
            preview_layout
        )

        splitter.addWidget(
            results_container
        )

        splitter.addWidget(
            preview_container
        )

        splitter.setSizes(
            [
                400,
                900
            ]
        )

        main_layout.addWidget(
            splitter,
            1
        )

        # -----------------------------------------------------
        # STATUS
        # -----------------------------------------------------

        self.status_label = QLabel(
            "Enter a query and click Search."
        )

        self.status_label.setAlignment(
            Qt.AlignCenter
        )

        self.status_label.setStyleSheet(
            """
            QLabel {
                padding: 5px;
            }
            """
        )

        main_layout.addWidget(
            self.status_label
        )

        self.setLayout(
            main_layout
        )

    # =========================================================
    # SEARCH
    # =========================================================

    def perform_search(self):

        query = (
            self.search_box
            .text()
            .strip()
        )

        if not query:

            QMessageBox.warning(
                self,
                "Empty Search",
                "Please enter a document query."
            )

            return

        self.results_list.clear()

        self.document_viewer.clear_viewer()

        self.status_label.setText(
            "Searching..."
        )

        QApplication.processEvents()

        try:

            results = search_documents(
                query
            )

            if not results:

                self.status_label.setText(
                    "No matching documents found."
                )

                return

            for result in results:

                item_text = (
                    f"{result['name']} "
                    f"({result['extension']})\n"
                    f"{result['path']}"
                )

                item = QListWidgetItem(
                    item_text
                )

                item.setData(
                    Qt.UserRole,
                    result
                )

                self.results_list.addItem(
                    item
                )

            self.status_label.setText(
                f"{len(results)} result(s) found. "
                "Click a file to preview it."
            )

        except Exception as error:

            self.status_label.setText(
                "Search failed."
            )

            QMessageBox.critical(
                self,
                "Search Error",
                str(error)
            )

    # =========================================================
    # PREVIEW
    # =========================================================

    def preview_selected_file(
        self,
        item
    ):

        result = item.data(
            Qt.UserRole
        )

        if not result:
            return

        file_path = result["path"]

        self.document_viewer.open_file(
            file_path
        )


# =============================================================
# MAIN
# =============================================================


def main():

    app = QApplication(
        sys.argv
    )

    window = DocumentFinderApp()

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()