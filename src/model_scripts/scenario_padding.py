""" Scenario for neural network. """
import datetime
import logging

import src.bacli as bacli
from src.bio.feature_builder import CombinedPeptideFeatureBuilder
from src.bio.peptide_feature import parse_features, parse_operator
from src.config import LOG_DIR, PROJECT_ROOT
from src.data.control_cdr3_source import ControlCDR3Source
from src.data.vdjdb_source import VdjdbSource
from src.models.model_padded import ModelPadded
from src.neural.trainer import Trainer
from src.processing.cv_folds import cv_splitter
from src.processing.inverse_map import InverseMap
from src.processing.padded_batch_generator import padded_batch_generator
from src.processing.splitter import splitter

bacli.set_description(__doc__)


@bacli.command
def run(
    batch_size: int = 128,
    epochs: int = 40,
    neg_ref: bool = False,
    neg_ratio: float = 0.5,
    val_split: float = None,  # the proportion of the dataset to include in the test split.
    epitope_grouped_cv: bool = False,
    neg_shuffle_in_cv: bool = True,
    n_folds: int = 5,
    min_length_cdr3: int = 10,
    max_length_cdr3: int = 20,
    min_length_epitope: int = 8,
    max_length_epitope: int = 13,
    name: str = "",
    features: str = "hydrophob,isoelectric,mass,hydrophil,charge",  # can be any str listed in peptide_feature.featuresMap
    operator: str = "absdiff",  # can be: prod, diff, absdiff, layer or best
    early_stop=False,
    include_learning_rate_reduction: bool = False,
    data_path=PROJECT_ROOT
    / "data/interim/vdjdb-2019-08-08/vdjdb-human-tra-trb-no10x.csv",
    optimizer: str = "rmsprop",  # can be any of: rmsprop, adam or SGD
    learning_rate: bool = False,
    # dense_activation: str = "tanh",
):

    # create run name by appending time and date
    run_name = name + datetime.datetime.now().strftime("_%Y%m%d_%H-%M-%S")
    # create filepath for log
    log_file = LOG_DIR / run_name
    log_file = log_file.with_suffix(".log")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    # create file logger
    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(filename=log_file, level=logging.INFO, format=log_fmt)
    # apply settings to root logger, so that loggers in modules can inherit both the file and console logger
    logger = logging.getLogger()
    # add console logger
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(log_fmt))
    logger.addHandler(console)

    # log utilised function arguments that were used for logging purposes
    logger.info(locals())

    # read (positive) data
    data_source = VdjdbSource(
        filepath=data_path,
        headers={"cdr3_header": "cdr3", "epitope_header": "antigen.epitope"},
    )

    # get list of features and operator based on input arguments
    features_list = parse_features(features)
    operator = parse_operator(operator)
    feature_builder = CombinedPeptideFeatureBuilder(features_list, operator)

    # check argument compatability
    if epitope_grouped_cv and val_split is not None:
        raise RuntimeError("Can't test epitope-grouped without k folds")

    logger.info("features: " + str(features_list))
    logger.info("operator: " + str(operator))
    logger.info("neg_ref: " + str(neg_ref))
    logger.info("epitope_grouped_cv: " + str(epitope_grouped_cv))
    logger.info("neg_shuffle_in_cv: " + str(neg_shuffle_in_cv))

    inverse_map = InverseMap()

    # store range restrictions for cdr3 and epitope
    cdr3_range = (min_length_cdr3, max_length_cdr3)
    epitope_range = (min_length_epitope, max_length_epitope)
    logger.info(f"cdr3 range restrictions: {cdr3_range}")
    logger.info(f"epitope range restrictions: {epitope_range}")

    trainer = Trainer(
        epochs,
        include_learning_rate_reduction=include_learning_rate_reduction,
        include_early_stop=early_stop,
        lookup=inverse_map,
    )

    model = ModelPadded(
        width=max_length_cdr3,
        height=max_length_epitope,
        name_suffix=run_name,
        channels=feature_builder.get_number_layers(),
        optimizer=optimizer,
        learning_rate=learning_rate,
    )
    logger.info(f"Built model {model.base_name}:")
    # model.summary() is logged inside trainer.py

    # if a fixed train-test split ratio is provided...
    if val_split is not None:
        train, val = splitter(data_source, test_size=val_split)
        # if a negative reference set is provided, use it
        if neg_ref:
            negative_source = ControlCDR3Source(
                min_length=min_length_cdr3, max_length=max_length_cdr3
            )
            neg_train, neg_val = splitter(negative_source, test_size=val_split)
            iterations = [((train, neg_train), (val, neg_val))]
        # else, generate negatives through shuffling
        else:
            # generate negatives through shuffling within each cv iteration
            if neg_shuffle_in_cv:
                iterations = [(train, val)]
            # generate negatives once on the entire dataset
            else:
                # TODO: shuffle cdr3/epitope pairs, remove positives, present as negatives
                iterations = [(train, val)]

    # ...otherwise use a cross validation scheme
    else:
        iterations = cv_splitter(
            data_source=data_source,
            n_folds=n_folds,
            epitope_grouped=epitope_grouped_cv,
            run_name=run_name,
        )

        # if a negative reference set is provided, use it
        if neg_ref:
            negative_source = ControlCDR3Source(
                min_length=min_length_cdr3, max_length=max_length_cdr3
            )
            neg_ref_fold_path = run_name + "_cdr3_ref"
            neg_iterations = cv_splitter(
                data_source=negative_source,
                n_folds=n_folds,
                epitope_grouped=False,  # CDR3 reference cannot be grouped on epitope
                run_name=neg_ref_fold_path,
            )
            iterations = [
                ((train, neg_train), (val, neg_val))
                for (train, val), (neg_train, neg_val) in zip(
                    iterations, neg_iterations
                )
            ]

    for iteration, (train, val) in enumerate(iterations):

        neg_train, neg_val = None, None
        logger.info(f"Iteration: {iteration}")
        logger.info(f"batch size: {batch_size}")
        if neg_ref:
            train, neg_train = train
            val, neg_val = val
            logger.info(f"neg train set: {len(neg_train)}")
            logger.info(f"neg val set: {len(neg_val)}")

        logger.info(f"train set: {len(train)}")
        logger.info(f"val set: {len(val)}")

        train_stream = padded_batch_generator(
            data_stream=train,
            feature_builder=feature_builder,
            neg_ratio=neg_ratio,
            batch_size=batch_size,
            cdr3_range=cdr3_range,
            epitope_range=epitope_range,
            negative_stream=neg_train,
        )
        val_stream = padded_batch_generator(
            data_stream=val,
            feature_builder=feature_builder,
            neg_ratio=neg_ratio,
            batch_size=batch_size,
            cdr3_range=cdr3_range,
            epitope_range=epitope_range,
            inverse_map=inverse_map,
            negative_stream=neg_val,
        )

        trainer.train(model, train_stream, val_stream, iteration=iteration)
