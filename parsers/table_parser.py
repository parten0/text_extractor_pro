import pandas as pd

class TableParser:
    def parse(self, page):
        tables = []
        raw_tables = page.extract_tables()

        for table in raw_tables:
            df = pd.DataFrame(table)
            df.columns = df.iloc[0]
            df = df.iloc[1:]

            tables.append(df.to_dict(orient="records"))

        return tables
