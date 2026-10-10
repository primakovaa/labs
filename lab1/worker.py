from PyQt6.QtCore import QThread, pyqtSignal
from parser import Parser
from tokenizator import Tokenizator
from refactorizer import Refactorizer


class ProcessingWorker(QThread):
    progress = pyqtSignal(str)
    finished_success = pyqtSignal(object, object)  
    failed = pyqtSignal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            self.progress.emit("Загрузка и чтение CSV-файла...")
            parser = Parser()
            parser.open(self.file_path)

            self.progress.emit("Анализ структуры и сбор сообщений...")
            parser.analyze()

            self.progress.emit("Нормализация текста...")
            parser.normalize()

            self.progress.emit("Маскирование сущностей...")
            parser.extract()

            self.progress.emit("Инициализация токенизатора и лемматизатора...")
            tokenizator = Tokenizator()

            self.progress.emit("Токенизация, лемматизация и сборка датасета...")
            refactorizer = Refactorizer()
            refactorizer.process_dataset(parser, tokenizator)

            self.progress.emit("Формирование Топ-20 слов...")
            top_df = refactorizer.build_top_words(20)

            self.finished_success.emit(refactorizer, top_df)
        except Exception as exc:
            self.failed.emit(str(exc))