""" Scenario for neural network with interaction map input. """
import logging

import src.bacli as bacli
from src.bio.feature_builder import CombinedPeptideFeatureBuilder
from src.bio.peptide_feature import parse_features, parse_operator
from src.config import PROJECT_ROOT
from src.data.control_cdr3_source import ControlCDR3Source
from src.data.vdjdb_source import VdjdbSource
from src.model_scripts import pipeline
from src.neural.trainer import get_output_path, Trainer
from src.processing.cv_folds import cv_splitter
from src.processing.inverse_map import InverseMap
from src.processing.padded_dataset_generator import padded_dataset_generator
from src.processing.splitter import splitter

bacli.set_description(__doc__)


@bacli.command
def run(
    batch_size: int = 128,
    epochs: int = 40,
    neg_ref: str = None,  # whether to generate negatives from CDR3 reference sequences or by shuffling positive examples
    neg_ratio: float = 0.5,  # proportion of positive to negative samples.
    val_split: float = None,  # the proportion of the dataset to include in the test split.
    epitope_grouped_cv: bool = False,  # when val_split is None, indicates whether to use normal k-fold cv or an epitope-grouped cv
    one_epitope_out_cv: bool = False,  # when val_split is None and epitope_grouped_cv is True, indicates whether to use leave-1-epitope-out cv
    neg_shuffle_in_cv: bool = True,  # when True, negatives will be generated through shuffling within each train/test set, otherwise the entire dataset will be shuffled, which can cause individual cdr3/epitope sequences to appear in both train and test sets.
    n_folds: int = 5,
    # these lengths are used for both size filtering and padding. Should be compatible with any preprocessing steps.
    min_length_cdr3: int = 10,
    max_length_cdr3: int = 20,
    min_length_epitope: int = 8,
    max_length_epitope: int = 13,
    name: str = "",  # name under which the model and log files will be stored, appended with the date-time.
    features: str = "hydrophob,isoelectric,mass,hydrophil,charge",  # can be any str listed in peptide_feature.featuresMap
    operator: str = "absdiff",  # can be: prod, diff, absdiff, layer or best
    early_stop: bool = False,  # whether to terminate model training when the performance metric stops improving (tf.keras.callbacks.EarlyStopping)
    include_learning_rate_reduction: bool = False,  # whether to reduce the learning rate when the performance metric has stopped improving (tf.keras.callbacks.ReduceLROnPlateau)
    data_path=PROJECT_ROOT
    / "data/interim/vdjdb-2019-08-08/vdjdb-human-tra-trb-no10x.csv",  # input data csv, as supplied by preprocess_vdjdb
    optimizer: str = "rmsprop",  # can be any of: rmsprop, adam or SGD
    learning_rate: float = None,  # learning rate supplied to the selected optimizer
    model: str = "model_padded",
    depth1: int = None,
    depth2: int = None,
    dropout1: float = None,
    dropout2: float = None,
    gap: bool = False,
):

    # create logger and log file
    run_name = pipeline.create_run_name(name)
    pipeline.create_logger(run_name)
    logger = logging.getLogger(__name__)

    # log utilised function arguments that were used
    logger.info(locals())

    # read (positive) data
    data_source = VdjdbSource(
        filepath=data_path,
        headers={"cdr3_header": "cdr3", "epitope_header": "antigen.epitope"},
    )

    # filter on size
    data_source.length_filter(
        min_length_cdr3, max_length_cdr3, min_length_epitope, max_length_epitope
    )

    # get list of features and operator based on input arguments
    features_list = parse_features(features)
    operator = parse_operator(operator)
    feature_builder = CombinedPeptideFeatureBuilder(features_list, operator)

    # check argument compatability
    if epitope_grouped_cv and val_split is not None:
        raise RuntimeError("Cannot test epitope-grouped without k folds.")

    logger.info("features: " + str(features_list))
    logger.info("operator: " + str(operator))
    logger.info("neg_ref: " + str(neg_ref))
    logger.info("epitope_grouped_cv: " + str(epitope_grouped_cv))
    logger.info("neg_shuffle_in_cv: " + str(neg_shuffle_in_cv))

    inverse_map = InverseMap()

    # store range restrictions for cdr3 and epitope
    cdr3_range = (min_length_cdr3, max_length_cdr3)
    epitope_range = (min_length_epitope, max_length_epitope)
    logger.info(f"Filtered CDR3 sequences to length: {cdr3_range}")
    logger.info(f"Filtered epitope sequences to length: {epitope_range}")

    trainer = Trainer(
        epochs,
        include_learning_rate_reduction=include_learning_rate_reduction,
        include_early_stop=early_stop,
        lookup=inverse_map,
    )

    if model == "model_padded":
        from src.models.model_padded import ModelPadded

        model = ModelPadded(
            width=max_length_cdr3,
            height=max_length_epitope,
            name=run_name,
            channels=feature_builder.get_number_layers(),
            optimizer=optimizer,
            learning_rate=learning_rate,
        )
    elif model == "model_selu":
        from src.models.model_padded_selu import ModelPaddedSelu

        model = ModelPaddedSelu(
            width=max_length_cdr3,
            height=max_length_epitope,
            name=run_name,
            channels=feature_builder.get_number_layers(),
            optimizer=optimizer,
            learning_rate=learning_rate,
        )
    elif model == "model_small":
        from src.models.model_padded_small import ModelPaddedSmall

        model = ModelPaddedSmall(
            width=max_length_cdr3,
            height=max_length_epitope,
            name=run_name,
            channels=feature_builder.get_number_layers(),
            optimizer=optimizer,
            learning_rate=learning_rate,
            depth1=depth1,
            depth2=depth2,
            dropout1=dropout1,
            dropout2=dropout2,
            gap=gap,
        )
    elif model == "model_small_selu":
        from src.models.model_padded_small_selu import ModelPaddedSmallSelu

        model = ModelPaddedSmallSelu(
            width=max_length_cdr3,
            height=max_length_epitope,
            name=run_name,
            channels=feature_builder.get_number_layers(),
            optimizer=optimizer,
            learning_rate=learning_rate,
            depth1=depth1,
            depth2=depth2,
            dropout1=dropout1,
            dropout2=dropout2,
            gap=gap,
        )

    logger.info(f"Built model {model.base_name}:")
    # model.summary() is logged inside trainer.py

    # if negative reference dataset is provided, draw negatives from it
    if neg_ref:
        logger.info(f"Generating negative examples from negative reference CDR3 set.")
        negative_source = ControlCDR3Source(
            filepath=neg_ref, min_length=min_length_cdr3, max_length=max_length_cdr3
        )
        data_source.generate_negatives_from_ref(negative_source)
        neg_shuffle = False

    # otherwise, generate negatives through shuffling
    else:
        # if neg_shuffle_in_cv is False, generate negatives once on the entire dataset
        if not neg_shuffle_in_cv:
            logger.info(
                f"Generating negative examples through shuffling on the entire dataset prior to train/test fold creation."
            )
            data_source.generate_negatives()
            neg_shuffle = False

        # otherwise, generate negatives within each train/test set during tf dataset creation
        else:
            logger.info(
                f"Generating negative examples through shuffling within each train/test fold."
            )
            neg_shuffle = True

    # if a fixed train-test split ratio is provided...
    if val_split is not None:
        train, val = splitter(data_source, test_size=val_split)
        iterations = [(train, val)]

    # ...otherwise use the specified cross validation scheme
    else:
        iterations = cv_splitter(
            data_source=data_source,
            n_folds=n_folds,
            epitope_grouped=epitope_grouped_cv,
            one_out=one_epitope_out_cv,
        )

    for iteration, (train, val) in enumerate(iterations):

        logger.info(f"Iteration: {iteration}")
        logger.info(f"batch size: {batch_size}")
        logger.info(f"train set: {len(train)}")
        logger.info(f"val set: {len(val)}")

        # retrieve model output directory and create data directory to store generated datasets with positive and negative examples
        train_fold_output, test_fold_output = (
            get_output_path(
                base_name=run_name,
                file_name=f"train_fold_{iteration}.csv",
                iteration=iteration,
            ),
            get_output_path(
                base_name=run_name,
                file_name=f"test_fold_{iteration}.csv",
                iteration=iteration,
            ),
        )

        train_data = padded_dataset_generator(
            data_stream=train,
            feature_builder=feature_builder,
            cdr3_range=cdr3_range,
            epitope_range=epitope_range,
            neg_shuffle=neg_shuffle,
            export_path=train_fold_output,
        )
        val_data = padded_dataset_generator(
            data_stream=val,
            feature_builder=feature_builder,
            cdr3_range=cdr3_range,
            epitope_range=epitope_range,
            inverse_map=inverse_map,
            neg_shuffle=neg_shuffle,
            export_path=test_fold_output,
        )

        # shuffle and batch train data
        train_data = train_data.shuffle(
            # buffer equals size of dataset, because positives and negatives are grouped
            buffer_size=train_data.reduce(0, lambda x, _: x + 1).numpy(),
            seed=42,
            # reshuffle to make each epoch see a different order of examples
            reshuffle_each_iteration=True,
        ).batch(batch_size)

        # batch validation data
        val_data = val_data.batch(batch_size)

        trainer.train(model, train_data, val_data, iteration=iteration)
