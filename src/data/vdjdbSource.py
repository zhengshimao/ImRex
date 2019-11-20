# from collections import defaultdict

import pandas as pd

from src.data.data_source import DataSource


VDJDB_PATH = "../data/vdjdb_TRB.csv"


class VdjdbSource(DataSource):
    def __init__(self, filepath=VDJDB_PATH):
        super().__init__()
        self.filepath = filepath
        self.data = pd.read_csv(self.filepath, sep=";")

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        # data = pd.read_csv(self.filepath, sep=';')

        # lengths1 = defaultdict(int)
        # lengths2 = defaultdict(int)

        for index, row in self.data.iterrows():
            pep1 = row["CDR3"]
            pep2 = row["Epitope"]
            # lengths1[len(pep1)] += 1
            # lengths2[len(pep2)] += 1
            yield (pep1, pep2), 1

        # print("lengths1")
        # for k, v in sorted(lengths1.items()):
        #     print(k, v)
        # print("lengths2")
        # for k, v in sorted(lengths2.items()):
        #     print(k, v)
