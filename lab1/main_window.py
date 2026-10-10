import os
import json
from collections import Counter
import pandas as pd

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTabWidget,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QStatusBar,
    QGroupBox,
)

from worker import ProcessingWorker
from refactorizer import Refactorizer
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.path.join(BASE_DIR, "data")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Текстовый процессор | PyQt6 NLP Studio")
        self.resize(1100, 750)
        self.setMinimumSize(850, 600)
        self.data_dir = DEFAULT_DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)

        self.worker: ProcessingWorker | None = None
        self.refactorizer: Refactorizer | None = None
        self.top_df = None
        self.token_frequencies = []

        self._init_ui()
        self._populate_available_csvs()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        file_group = QGroupBox("Источник данных")
        file_layout = QHBoxLayout(file_group)

        file_label = QLabel("CSV в папке data:")
        self.csv_combo = QComboBox()
        self.csv_combo.setMinimumWidth(280)

        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.setToolTip("Пересканировать папку data/")
        refresh_btn.clicked.connect(self._populate_available_csvs)

        import_btn = QPushButton("📁 Выбрать другой CSV...")
        import_btn.clicked.connect(self._import_csv_dialog)

        file_layout.addWidget(file_label)
        file_layout.addWidget(self.csv_combo, stretch=1)
        file_layout.addWidget(refresh_btn)
        file_layout.addWidget(import_btn)
        main_layout.addWidget(file_group)
        actions_group = QGroupBox("Управление конвейером обработки")
        actions_layout = QHBoxLayout(actions_group)

        self.process_btn = QPushButton("▶ Запустить обработку")
        self.process_btn.setStyleSheet(
            "font-weight: bold; background-color: #2b78e4; color: white; padding: 6px 12px;"
        )
        self.process_btn.clicked.connect(self._start_processing)

        self.export_tokens_btn = QPushButton("💾 Экспорт токенов...")
        self.export_tokens_btn.setEnabled(False)
        self.export_tokens_btn.clicked.connect(self._export_tokens_dialog)

        self.export_dataset_btn = QPushButton("💾 Экспорт очищенного CSV...")
        self.export_dataset_btn.setEnabled(False)
        self.export_dataset_btn.clicked.connect(self._export_dataset_dialog)

        actions_layout.addWidget(self.process_btn)
        actions_layout.addWidget(self.export_tokens_btn)
        actions_layout.addWidget(self.export_dataset_btn)
        main_layout.addWidget(actions_group)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)
        main_layout.addWidget(self.progress_bar)
        self.tabs = QTabWidget()
        tokens_tab = QWidget()
        tokens_layout = QVBoxLayout(tokens_tab)
        tokens_search_bar = QHBoxLayout()

        self.token_search_input = QLineEdit()
        self.token_search_input.setPlaceholderText("Поиск токена/леммы по вхождению...")
        self.token_search_input.textChanged.connect(self._filter_tokens_table)

        self.token_type_filter = QComboBox()
        self.token_type_filter.addItems(["Все", "Только леммы", "Только токены"])
        self.token_type_filter.currentTextChanged.connect(self._filter_tokens_table)

        self.token_count_label = QLabel("Всего элементов: 0")

        tokens_search_bar.addWidget(QLabel("Поиск:"))
        tokens_search_bar.addWidget(self.token_search_input, stretch=1)
        tokens_search_bar.addWidget(self.token_type_filter)
        tokens_search_bar.addWidget(self.token_count_label)
        tokens_layout.addLayout(tokens_search_bar)

        self.tokens_table = QTableWidget()
        self.tokens_table.setColumnCount(3)
        self.tokens_table.setHorizontalHeaderLabels(["Слово / Единица", "Тип", "Частота"])
        self.tokens_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tokens_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tokens_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        tokens_layout.addWidget(self.tokens_table)
        messages_tab = QWidget()
        messages_layout = QVBoxLayout(messages_tab)
        msg_search_bar = QHBoxLayout()

        self.msg_search_input = QLineEdit()
        self.msg_search_input.setPlaceholderText("Фильтрация сообщений по ключевому слову...")
        self.msg_search_input.textChanged.connect(self._filter_messages_table)
        msg_search_bar.addWidget(QLabel("Поиск по тексту:"))
        msg_search_bar.addWidget(self.msg_search_input)
        messages_layout.addLayout(msg_search_bar)

        self.messages_table = QTableWidget()
        self.messages_table.setColumnCount(7)
        self.messages_table.setHorizontalHeaderLabels([
            "ID", "Канал", "Дата", "Оригинал", "Обезличенный текст", "Токены", "Леммы"
        ])
        self.messages_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.messages_table.horizontalHeader().setStretchLastSection(True)
        messages_layout.addWidget(self.messages_table)
        top_tab = QWidget()
        top_layout = QVBoxLayout(top_tab)
        self.top_table = QTableWidget()
        self.top_table.setColumnCount(5)
        self.top_table.setHorizontalHeaderLabels([
            "Ранг", "До очистки (слово)", "Частота (до)", "После очистки (лемма)", "Частота (после)"
        ])
        self.top_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        top_layout.addWidget(self.top_table)

        self.tabs.addTab(tokens_tab, "🔤 База токенов и лемм")
        self.tabs.addTab(messages_tab, "💬 Обработанные сообщения")
        self.tabs.addTab(top_tab, "📊 Топ-20 сравнение")
        main_layout.addWidget(self.tabs)

        # 5. Статусная строка
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готово к работе")

    def _populate_available_csvs(self):
        """Сканирует папку data/ и наполняет QComboBox."""
        prev_path = self.csv_combo.currentData()
        self.csv_combo.clear()

        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)

        csv_files = [f for f in os.listdir(self.data_dir) if f.lower().endswith(".csv")]
        if csv_files:
            for filename in sorted(csv_files):
                full_path = os.path.join(self.data_dir, filename)
                self.csv_combo.addItem(filename, full_path)
            for idx in range(self.csv_combo.count()):
                if self.csv_combo.itemData(idx) == prev_path:
                    self.csv_combo.setCurrentIndex(idx)
                    break

            self.status_bar.showMessage(f"Найдено CSV в папке data: {len(csv_files)}")
        else:
            self.status_bar.showMessage("В папке data/ нет CSV файлов. Добавьте файлы или выберите через импорт.")

    def _import_csv_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите CSV файл",
            self.data_dir,
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            existing_idx = -1
            for idx in range(self.csv_combo.count()):
                if self.csv_combo.itemData(idx) == file_path:
                    existing_idx = idx
                    break

            if existing_idx != -1:
                self.csv_combo.setCurrentIndex(existing_idx)
            else:
                display_name = os.path.basename(file_path)
                self.csv_combo.addItem(f"{display_name} (внешний)", file_path)
                self.csv_combo.setCurrentIndex(self.csv_combo.count() - 1)

            self.status_bar.showMessage(f"Выбран файл: {os.path.basename(file_path)}")

    def _start_processing(self):
        file_path = self.csv_combo.currentData()
        if not file_path:
            raw_text = self.csv_combo.currentText().strip()
            file_path = os.path.join(self.data_dir, raw_text)

        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Внимание", "Выбранный CSV-файл не найден на диске.")
            return

        self.process_btn.setEnabled(False)
        self.progress_bar.setVisible(True)

        self.worker = ProcessingWorker(file_path)
        self.worker.progress.connect(self.status_bar.showMessage)
        self.worker.finished_success.connect(self._on_processing_success)
        self.worker.failed.connect(self._on_processing_failed)
        self.worker.start()

    def _on_processing_failed(self, error_message: str):
        self.progress_bar.setVisible(False)
        self.process_btn.setEnabled(True)
        self.status_bar.showMessage("Ошибка выполнения.")
        QMessageBox.critical(
            self,
            "Ошибка конвейера",
            f"Не удалось обработать файл:\n{error_message}\n\n"
            "Проверьте наличие колонок message_id, channel, created_at, message."
        )

    def _on_processing_success(self, refactorizer: Refactorizer, top_df):
        self.refactorizer = refactorizer
        self.top_df = top_df

        self.progress_bar.setVisible(False)
        self.process_btn.setEnabled(True)
        self.export_tokens_btn.setEnabled(True)
        self.export_dataset_btn.setEnabled(True)

        self._build_tokens_database()
        self._populate_messages_table()
        self._populate_top_table()

        self.status_bar.showMessage(
            f"Завершено. Сообщений: {len(self.refactorizer.dataset)}. "
            f"Уникальных токенов/лемм: {len(self.token_frequencies)}"
        )
        QMessageBox.information(self, "Успех", "Датасет успешно обработан!")

    def _build_tokens_database(self):
        if self.refactorizer is None or self.refactorizer.dataset is None:
            return

        all_tokens = []
        all_lemmas = []
        for _, row in self.refactorizer.dataset.iterrows():
            tokens = json.loads(row["tokens"]) if isinstance(row["tokens"], str) else row["tokens"]
            lemmas = json.loads(row["lemmas"]) if isinstance(row["lemmas"], str) else row["lemmas"]
            all_tokens.extend(tokens)
            all_lemmas.extend(lemmas)

        token_counter = Counter(all_tokens)
        lemma_counter = Counter(all_lemmas)

        self.token_frequencies = []
        for lemma, count in lemma_counter.items():
            self.token_frequencies.append((lemma, "Лемма", count))
        for token, count in token_counter.items():
            self.token_frequencies.append((token, "Токен", count))

        self.token_frequencies.sort(key=lambda x: x[2], reverse=True)
        self._filter_tokens_table()

    def _filter_tokens_table(self):
        query = self.token_search_input.text().strip().lower()
        type_filter = self.token_type_filter.currentText()

        filtered = []
        for word, w_type, count in self.token_frequencies:
            if query and query not in word.lower():
                continue
            if type_filter == "Только леммы" and w_type != "Лемма":
                continue
            if type_filter == "Только токены" and w_type != "Токен":
                continue
            filtered.append((word, w_type, count))

        self.tokens_table.setRowCount(len(filtered))
        for row_idx, (word, w_type, count) in enumerate(filtered):
            self.tokens_table.setItem(row_idx, 0, QTableWidgetItem(str(word)))
            self.tokens_table.setItem(row_idx, 1, QTableWidgetItem(str(w_type)))
            self.tokens_table.setItem(row_idx, 2, QTableWidgetItem(str(count)))

        self.token_count_label.setText(f"Отображено: {len(filtered)} из {len(self.token_frequencies)}")

    def _populate_messages_table(self):
        df = self.refactorizer.dataset
        self.messages_table.setRowCount(len(df))
        for row_idx, (_, row) in enumerate(df.iterrows()):
            self.messages_table.setItem(row_idx, 0, QTableWidgetItem(str(row["message_id"])))
            self.messages_table.setItem(row_idx, 1, QTableWidgetItem(str(row["channel"])))
            self.messages_table.setItem(row_idx, 2, QTableWidgetItem(str(row["created_at"])))
            self.messages_table.setItem(row_idx, 3, QTableWidgetItem(str(row["original_text"])))
            self.messages_table.setItem(row_idx, 4, QTableWidgetItem(str(row["anonymized_text"])))
            self.messages_table.setItem(row_idx, 5, QTableWidgetItem(str(row["tokens"])))
            self.messages_table.setItem(row_idx, 6, QTableWidgetItem(str(row["lemmas"])))

    def _filter_messages_table(self):
        query = self.msg_search_input.text().strip().lower()
        for row in range(self.messages_table.rowCount()):
            if not query:
                self.messages_table.setRowHidden(row, False)
                continue
            orig = self.messages_table.item(row, 3).text().lower()
            clean = self.messages_table.item(row, 4).text().lower()
            tokens = self.messages_table.item(row, 5).text().lower()
            lemmas = self.messages_table.item(row, 6).text().lower()

            match = (query in orig) or (query in clean) or (query in tokens) or (query in lemmas)
            self.messages_table.setRowHidden(row, not match)

    def _populate_top_table(self):
        if self.top_df is None:
            return
        self.top_table.setRowCount(len(self.top_df))
        for row_idx, (_, row) in enumerate(self.top_df.iterrows()):
            self.top_table.setItem(row_idx, 0, QTableWidgetItem(str(row["Ранг"])))
            self.top_table.setItem(row_idx, 1, QTableWidgetItem(str(row["До очистки (слово)"])))
            self.top_table.setItem(row_idx, 2, QTableWidgetItem(str(row["Частота (до)"])))
            self.top_table.setItem(row_idx, 3, QTableWidgetItem(str(row["После очистки (лемма)"])))
            self.top_table.setItem(row_idx, 4, QTableWidgetItem(str(row["Частота (после)"])))

    def _export_tokens_dialog(self):
        if not self.token_frequencies:
            QMessageBox.information(self, "Инфо", "База токенов пуста.")
            return

        default_save_path = os.path.join(self.data_dir, "tokens_vocabulary.csv")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт токенов", default_save_path, "CSV Files (*.csv);;Text Files (*.txt)"
        )
        if not file_path:
            return

        try:
            if file_path.endswith(".txt"):
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("СЛОВО\tТИП\tЧАСТОТА\n")
                    for word, w_type, count in self.token_frequencies:
                        f.write(f"{word}\t{w_type}\t{count}\n")
            else:
                export_df = pd.DataFrame(self.token_frequencies, columns=["Слово", "Тип", "Частота"])
                export_df.to_csv(file_path, index=False, encoding="utf-8-sig")

            QMessageBox.information(self, "Успех", f"Файл сохранен:\n{file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {exc}")

    def _export_dataset_dialog(self):
        if self.refactorizer is None or self.refactorizer.dataset is None:
            QMessageBox.information(self, "Инфо", "Датасет еще не готов.")
            return

        default_save_path = os.path.join(self.data_dir, "clean_messages.csv")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт датасета", default_save_path, "CSV Files (*.csv)"
        )
        if not file_path:
            return

        try:
            self.refactorizer.save(file_path)
            QMessageBox.information(self, "Успех", f"Датасет сохранен:\n{file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {exc}")