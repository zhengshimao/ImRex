""" Scenario for neural network. """
import src.bacli as bacli
from src.data.vdjdbSource import VdjdbSource
from src.models.modelNetTCR import ModelNetTCR
from src.neural.trainer import Trainer
from src.processing.kfolds import (
    EpitopeStratifiedFoldSplitter,
    FoldIterator,
    RandomFoldSplitter,
)
from src.processing.net_tcr_batch_generator import NetTCRBatchGenerator
from src.processing.splitter import Splitter

bacli.setDescription(__doc__)


@bacli.command
def run(
    batch_size: int = 128,
    val_split: float = None,
    epochs: int = 40,
    neg_ratio: float = 0.5,
    min_group: int = 32,
    name: str = "",
    nrFolds: int = 5,
    early_stop=False,
    data_path="../data/vdjdb_TRB.csv",
    stratified: bool = False,
):

    dataSource = VdjdbSource(filepath=data_path)

    trainer = Trainer(epochs, includeEarlyStop=early_stop)
    model = ModelNetTCR(nameSuffix=name)

    if val_split is not None:
        train, val = Splitter(dataSource, ratio=val_split)
        iterations = [(train, val)]
    else:
        FoldSplitter = (
            EpitopeStratifiedFoldSplitter if stratified else RandomFoldSplitter
        )
        folds = FoldSplitter(dataSource, nrFolds)
        iterations = FoldIterator(folds)
    for index, (train, val) in enumerate(iterations):
        print("Iteration:", index)
        print("train set", len(train))
        print("val set", len(val))
        print("batch size", batch_size)

        trainStream = NetTCRBatchGenerator(train, neg_ratio, batch_size, min_group)
        valStream = NetTCRBatchGenerator(val, neg_ratio, batch_size, min_group)

        trainer.train(model, trainStream, valStream, iteration=index)
