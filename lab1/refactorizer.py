import json
import re
from secrets import token_bytes
from tokenize import Token
import pandas as pd
from collections import Counter

"""
Refactorizer - модуль формирования готового датасета, анализа в виде "TOP-20" и сохранения обработанных данных в отдельный CSV-файл.
Авторство: Тюлин Константин, МТ-201
"""

class Refactorizer:
    def __init__(self, output_path="clean_messages.csv"):
        self.output_path = output_path
        self.dataset = None

    @staticmethod
    def _normalize_obj(obj):
        if obj is None:
            return []
        if hasattr(obj, "group"):
            return [obj.group()]
        if isinstance(obj, str) and obj != "":
            return [obj]
        if isinstance(obj, list):
            res = []
            for item in obj:
                if hasattr(item, "group"):
                    res.append(item.group())
                elif item:
                    res.append(str(item))
            return res
        return []

    def process_message(self,
        message_id,
        channel,
        created_at,
        original_text,
        anon_text="",
        clean_text="",
        tokens=None,
        lemmas=None,
        urls=None,
        phones=None,
        emails=None,
        dates=None,
        prices=None,
    ):
        if tokens is None:
            tokens = []
        if lemmas is None:
            lemmas = []

        urls_list = self._normalize_obj(urls)
        phones_list = self._normalize_obj(phones)
        emails_list = self._normalize_obj(emails)
        dates_list = self._normalize_obj(dates)
        prices_list = self._normalize_obj(prices)

        row = {
            "message_id": message_id,
            "channel": channel,
            "created_at": created_at,
            "original_text": original_text,
            "urls": json.dumps(urls_list, ensure_ascii=False),
            "phones": json.dumps(phones_list, ensure_ascii=False),
            "emails": json.dumps(emails_list, ensure_ascii=False),
            "dates": json.dumps(dates_list, ensure_ascii=False),
            "prices": json.dumps(prices_list, ensure_ascii=False),
            "tokens": json.dumps(tokens, ensure_ascii=False),
            "lemmas": json.dumps(lemmas, ensure_ascii=False),
            "anonymized_text": anon_text,
            "clean_text": clean_text,
        }
        return row

    def process_dataset(self, parser, tokenizator):
        df = parser.data_frame
        rows = []

        for i in range(len(df)):
            msg_id = df["message_id"].iloc[i]
            channel = df["channel"].iloc[i]
            created_at = df["created_at"].iloc[i]
            orig_text = df["message"].iloc[i]

            tok_res = tokenizator.process(orig_text)
            anon = tok_res["anonymized_text"]
            tokens = tok_res["tokens"]
            lemmas = tok_res["lemmas"]
            clean_text = " ".join(tokens)

            u = parser._urls[i] if i < len(parser._urls) else None
            p = parser._phones[i] if i < len(parser._phones) else None
            e = parser._emails[i] if i < len(parser._emails) else None
            d = parser._dates[i] if i < len(parser._dates) else None
            pr = parser._prices[i] if i < len(parser._prices) else None

            row = self.process_message(
                message_id=msg_id,
                channel=channel,
                created_at=created_at,
                original_text=orig_text,
                clean_text=clean_text,
                anon_text=anon,
                tokens=tokens,
                lemmas=lemmas,
                urls=u,
                phones=p,
                emails=e,
                dates=d,
                prices=pr
            )
            rows.append(row)

        self.dataset = pd.DataFrame(rows)
        return self.dataset

    def build_top_words(self, n=20):
        if self.dataset is None:
            print("вызовите, пожалуйста, process_dataset()")
            return None

        words_before = []
        for text in self.dataset["original_text"]:
            words = re.findall(r"[а-яa-z]+", text.lower())
            words_before.extend(words)

        lemmas_after = []
        for item in self.dataset["lemmas"]:
            if isinstance(item, str):
                item_list = json.loads(item)
            else:
                item_list = item
            lemmas_after.extend(item_list)

        top_before = Counter(words_before).most_common(n)
        top_after = Counter(lemmas_after).most_common(n)

        comparison_rows = []
        for i in range(n):
            word_b, count_b = top_before[i]
            lemma_a, count_a = top_after[i]
            comparison_rows.append({
                "Ранг": i + 1,
                "До очистки (слово)": word_b,
                "Частота (до)": count_b,
                "После очистки (лемма)": lemma_a,
                "Частота (после)": count_a
            })
        df_top = pd.DataFrame(comparison_rows)

        print(f"Топ-{n} слов до и после чистки\n")
        print(df_top.to_string(index=False))

        return df_top

    def save(self, output_path=None):
        path = output_path or self.output_path
        if self.dataset is None:
            print("вызовите, пожалуйста, process_dataset()")
            return
        self.dataset.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"Сохранение файла в {path}")




if __name__ == "__main__":
    from parser import Parser
    from tokenizator import Tokenizator
    p = Parser()
    p.open("data/source.csv")
    p.analyze()
    p.extract()

    tok = Tokenizator()

    ref = Refactorizer("clean_msgs.csv")
    ref.process_dataset(p, tok)
    ref.build_top_words(20)
    ref.save()