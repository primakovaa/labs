import re
import pandas as pd

"""
Parser - класс для парсинга и нормализации CSV документа. Возвращает нормализованный датасет и хранит в себе важную информацию (Email, телефоны и прочее)
Авторство: Кравченко Д.А, МТ-201
"""

EMAIL_PATTERN = (
    r"[A-Za-zА-Яа-я0-9._%+-]+"
    r"@[A-Za-zА-Яа-я0-9.-]+\.[A-Za-zА-Яа-я]{2,}"
)
PHONE_PATTERN = r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"
URL_PATTERN = r"(?i)(?:https?://|www\.)[a-z0-9.-]+\.[a-z]{2,}(?:/[^\s<>,\"'\)]*)?"
DATE_PATTERN = r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b"
PRICE_PATTERN = r"(?:\d{1,3}(?:\s?\d{3})*|\d+)\s*(?:руб\.|₽|RUB|р\.|рублей|руб|Rub|Руб|РУБ|р|)"
class Parser:
    def __init__(self):
        self.messages = []
        self.normalize_messages = []
        self.values = []
        self.data_frame = None

        self._emails = []
        self._phones = []
        self._urls = []
        self._dates = []
        self._prices = []
    def open(self, file):
        self.data_frame = pd.read_csv(file)
    def analyze(self):
        if self.data_frame is None:
            raise ValueError("DataFrame is not loaded, please call open() first.")
        self.data_types = self.data_frame.dtypes
        for value in self.data_frame.values:
            self.messages.append(value[3])
            self.values.append(value)
    def normalize(self):
        for message in self.messages:
            message = message.lower()
            message = message.replace("ё", "е")
            message = re.sub(r"[^\w\s]", " ", message)
            message = re.sub(r"_", " ", message)
            message = re.sub(r"\s+", " ", message)
            message = message.strip()
            self.normalize_messages.append(message)
    def extract(self):
        for i, message in enumerate(self.messages):
            email = re.search(EMAIL_PATTERN, str(message))
            self._emails.append(email)
            message = re.sub(EMAIL_PATTERN, "[EMAIL]", message)
            phone = re.search(PHONE_PATTERN, str(message))
            self._phones.append(phone)
            message = re.sub(PHONE_PATTERN, "[PHONE]", message)
            date = re.search(DATE_PATTERN, str(message))
            self._dates.append(date)
            message = re.sub(DATE_PATTERN, "[DATE]", message)
            price = re.search(PRICE_PATTERN, str(message))
            self._prices.append(price)
            message = re.sub(PRICE_PATTERN, "[PRICE]", message)
            url = re.search(URL_PATTERN, str(message))
            self._urls.append(url)
            message = re.sub(URL_PATTERN, "[URL]", message)
            self.messages[i] = message
