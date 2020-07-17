import gc
import logging

import numpy as np
import pandas as pd

from src.data.control_cdr3_source import ControlCDR3Source


def add_negatives(
    df: pd.DataFrame, full_dataset_path: str, epitope_ratio: bool = False
):
    """Generate negative CDR3-epitope pairs through shuffling and add them to the DataFrame.

    Parameters
    ----------
    df : DataFrame
        A DataFrame containing CDR3 and epitope sequence pairs, derived from a relevant Stream object. Should only contain positives, as a "y" column with 1s.
    full_dataset_path : str
        Path to the entire cdr3-epitope dataset, before splitting into folds, restricting length or downsampling. Used to avoid generating false negatives during shuffling. Should only contain positive values. Will be merged with current train/val dataframe.
        Length trimming = OK
        CV folds =  not OK, in the grouped-kfold setting it does not matter, because when a certain CDR3 is paired with two different epitopes, and they end up in different folds, it's impossible for the CDR3 to be accidentally matched up to the other epitope again, because it's not available for selection. In the normal CV setting it could matter though.
        Downsampling = not OK, a CDR3 could lose representative samples of it being paired with specific epitopes, and could end up being paired with them again as false negatives during shuffling.
        MHC = OK, a few CDR3s occur for both classes, but none of the epitopes do. Consequently it's impossible for a CDR3 to be paired with an epitope that could be a false negative in the full dataset.
        TRAB = OK, none of the CDR3s are identical between TRA and TRB genes. Consequently it's impossible for a CDR3 to be paired with an epitope that could be a false negative in the full dataset.
    epitope_ratio : boolean
        When false, samples an epitope for each CDR3 sequence in the
        proportionally to its occurrence in the other epitope pairs. Does not
        preserve the ratio of positives and negatives within each epitope,
        but does result in every CDR3 sequence having exactly 1 positive and negative.
        When true, samples a set of CDR3 sequences with from the unique list of CDR3s
        for each epitope observation (per epitope), i.e. preserves exact ratio of positives and
        negatives for each epitope, at the expense of some CDR3s appearing more than once
        among the negatives and others only in positives pairs.

    Returns
    -------
    DataFrame
        A DataFrame with the original positive CDR3-epitope pairs, and new negative pairs created by shuffling the positive ones.
    """
    logger = logging.getLogger(__name__)

    logger.info(
        f"Generating {df.shape[0]} negatives by shuffling the positive sequence pairs."
    )
    logger.info(f"Using {full_dataset_path} to avoid generating false negatives.")

    # print warning and skip generation if there is only 1 epitope
    if len(df["antigen.epitope"].unique()) == 1:
        logger.warning(
            "Cannot generate negatives through shuffling when there is only 1 epitope present in a fold. Skipping generation..."
        )
        return df

    # read in full dataset and remove duplicates, used to avoid generating false negatives
    full_df = pd.read_csv(
        full_dataset_path, sep=";", usecols=["cdr3", "antigen.epitope"]
    )
    # merge the train/validation set with the full dataset and use this to check for false negatives
    # merging is important when the validation set is not contained in the full dataset (e.g. when using an external test set)
    full_df = (
        pd.concat([full_df, df[["cdr3", "antigen.epitope"]]])
        .drop_duplicates()
        .reset_index(drop=True)
    )

    # generate negative pairs through shuffling
    if epitope_ratio:
        logger.info(
            "Negatives will be generated by sampling CDR3 sequences for every observation with a given epitope."
        )
        # generate negative pairs by iterating over every sequence pair,
        # and each time match the current epitope with a randomly sampled CDR3
        # sequence from the rest of the dataset (excluding any CDR3s that are paired
        # with the current epitope as a positive example).
        np.random.seed(42)
        shuffled_df = sample_cdr3s_per_epitope(df=df, full_df=full_df)

    else:
        logger.info(
            "Negatives will be generated by sampling a single epitope for each CDR3 sequence."
        )
        # generate negative pairs by iterating over every sequence pair,
        # and each time match the current CDR3 with a randomly sampled epitope
        # from the rest of the dataset (excluding any epitopes that are paired
        # with the current CDR3 as a positive example).
        shuffled_pairs = [
            sample_epitope_per_cdr3(
                cdr3=cdr3,
                df=df,
                full_df=full_df,
                cdr3_column="cdr3",
                epitope_column="antigen.epitope",
                seed=seed
                # seed=seed + 3458,
            )
            for seed, cdr3 in enumerate(df["cdr3"])
        ]

        # convert list of tuples into dataframe and add class label
        shuffled_df = pd.DataFrame(shuffled_pairs, columns=["cdr3", "antigen.epitope"],)

    # add class label to shuffled observations
    shuffled_df["y"] = 0

    # merge with original positive data, ensuring positives are kept at the top of the dataframe
    df = df.append(shuffled_df).reset_index(drop=True)

    # extract duplicates
    # NOTE: because the sampling approach ensures that accidental duplicates of
    # positive pairs (i.e. false negatives) never occur, these will all be
    # accidental duplicate samples of negative pairs.
    # Therefore, keep="last" is redundant, but if this was not the case,
    # it would result in only the positive examples being stored in the
    # dataframe (marking the last (=positives) as True).
    # This is kept here for historical purposes, because before the epitope
    # was supplied alongside the cdr3 in a zip operation during sample
    # generation, and the associated positive epitope was used for exclusion
    # purposes.
    # NOTE: technically not required when sampling cdr3s per epitope,
    # because in that case cdr3s are sampled without replacement from
    # a list of unique sequences.
    to_do_df = df.loc[df.duplicated(subset=["cdr3", "antigen.epitope"], keep="last")]
    # make sure all duplicates are indeed all negatives (or there are none)
    assert (
        df.loc[df.duplicated(subset=["cdr3", "antigen.epitope"], keep=False), "y"]
        .unique()
        .size
        <= 1
    )

    # when sampling epitopes per cdr3 (= not epitope_ratio)
    # the following steps are still required
    if not epitope_ratio:
        # remove duplicates from merged dataframe
        df = df.drop_duplicates(
            subset=["cdr3", "antigen.epitope"],
            keep="first",
            # This "keep" should not be required, see previous NOTE
            # always keeps the original positive examples when duplicates
            # occur across pos/neg, i.e. removes false negatives
        ).reset_index(drop=True)

        # remove NaN to deal with any possible universal cdr3s
        df = df.dropna(axis=0, how="any", subset=["antigen.epitope"])

        # add negatives until required amount is reached
        # add fail safe in case it is mathematically impossible to do so
        n = 0
        while to_do_df.shape[0] > 0 and not epitope_ratio:
            n += 1
            if n > 100:
                logger.warning(
                    f"Could not create negative samples for {len(to_do_df)} CDR3 sequences, likely because they had too many different binding partners. Skipping these..."
                )
                logger.warning(to_do_df)
                break
            elif n == 50:
                logger.warning(
                    f"Could not create enough negative samples by matching every CDR3 sequence to another epitope exactly once. {len(to_do_df)} CDR3s will be sampled randomly from the positive set, leading them to be re-used and present in multiple negative pairs. Retrying this step 50 times before giving up. The CDR3s to be omitted are {to_do_df.cdr3}."
                )
            elif n > 50:
                # it is unlikely, but possible that certain CDR3 sequences will
                # be matched with the same epitope multiple times
                # so the sampling step is repeated 50 times.
                # if there are still duplicates after this, a warning is shown
                # and an equivalent amount of new cdr3s are randomly drawn,
                # and these are then attempted to be matched to
                # new epitopes as negatives.
                shuffled_pairs = [
                    sample_epitope_per_cdr3(
                        cdr3=cdr3,
                        df=df,
                        full_df=full_df,
                        cdr3_column="cdr3",
                        epitope_column="antigen.epitope",
                        seed=n,
                    )
                    for cdr3 in df.loc[df["y"] == 1, "cdr3"].sample(
                        n=len(to_do_df), random_state=42 + n
                    )
                ]

            else:
                # try to sample another epitope for the duplicate CDR3 sequences
                # i.e. those that were accidentally matched with the same epitope
                # combine the entire dataframe (current positives and negatives)
                # and use this to restrict the list of allowed epitopes
                shuffled_pairs = [
                    sample_epitope_per_cdr3(
                        cdr3=cdr3,
                        df=df,
                        full_df=full_df,
                        cdr3_column="cdr3",
                        epitope_column="antigen.epitope",
                        seed=n,
                    )
                    for cdr3 in to_do_df["cdr3"]
                ]
            shuffled_df = pd.DataFrame(
                shuffled_pairs, columns=["cdr3", "antigen.epitope"],
            )
            shuffled_df["y"] = 0
            df = df.append(shuffled_df).reset_index(drop=True)
            to_do_df = df.loc[
                df.duplicated(subset=["cdr3", "antigen.epitope"], keep="last")
            ]
            df = df.drop_duplicates(
                subset=["cdr3", "antigen.epitope"], keep="first",
            ).reset_index(drop=True)
            df = df.dropna(axis=0, how="any", subset=["antigen.epitope"])

    # assert there are no remaining duplicates and print info
    assert (
        df.duplicated(subset=["cdr3", "antigen.epitope"]).sum() == 0
    ), "Found duplicate sequence pairs after shuffling to generate negatives."
    n_pos = np.sum(df["y"] == 1)
    n_neg = np.sum(df["y"] == 0)
    logger.info(
        f"Generated {n_neg} negative sequence pairs by shuffling the {n_pos} positive pairs."
    )

    # clean up full dataset from memory
    del full_df
    full_df = ""
    del full_df
    gc.collect()

    return df


def sample_cdr3s_per_epitope(
    df: pd.DataFrame,
    full_df: pd.DataFrame,
    cdr3_column: str = "cdr3",
    epitope_column: str = "antigen.epitope",
):
    """
    Generate negative pairs by iterating over every sequence pair in the dataset,
    and each time match the current epitope with a randomly sampled CDR3
    sequence from the rest of the dataset, excluding any CDR3s that are paired
    with the current epitope as a positive example (false negatives).

    Preserves exact ratio of positives and negatives for each epitope,
    at the expense of some CDR3s appearing more than once among negatives, and others
    only in the positive pairs.

    CDR3s are sampled from the unique set of CDR3s, instead of the actual distribution.
    Should not matter in most cases since only a small minority of CDR3s occur more
    than once.

    NOTE: when the number of pairs for a given epitope is larger than the number
    of available unique CDR3 sequences associated with the other epitopes,
    the number of returned negatives for this epitope will be limited to this
    smaller number, causing a slight deviation from the desired per-epitope ratio.

    Parameters
    ----------
    df : pd.DataFrame
        A positive cdr3-epitope DataFrame with a "cdr3" and "antigen.epitope" column.
        Must have a class label column ("y") with "1" as the positive label.
    full_df : pd.DataFrame
        The entire cdr3-epitope DataFrame, before splitting into folds, restricting length or downsampling.
        Used to avoid generating false negatives. Should only contain positive values.
    cdr3_column : str
        The header for the cdr3 column in the DataFrame.
    epitope_column : str
        The header for the epitope column in the DataFrame.

    Returns
    -------
    pd.DataFrame
        A dataframe with negative cdr3 and epitope sequence pairs, of the same size as the input.
    """
    # full_df should only contain positive pairs, and consequently no y column should be present yet
    assert "y" not in full_df.columns

    # create list to store dataframes for every epitope
    negative_list = []

    # loop through every observation per epitope
    for epitope in df[epitope_column].unique():
        # extract number of required observations for current epitope
        n = df[df[epitope_column] == epitope].shape[0]

        # check which CDR3s occur as a positive partner for the current epitope in the full dataset
        cdr3_to_exclude = full_df.loc[(full_df[epitope_column] == epitope), cdr3_column]
        possible_cdr3 = df.loc[
            ~df[cdr3_column].isin(cdr3_to_exclude), cdr3_column
        ].unique()

        # check if list is empty => epitope binds to every CDR3 present
        if possible_cdr3.size == 0:
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Epitope sequence {epitope} is associated with every CDR3 sequence in the dataset and will be discarded from the negatives."
            )
            continue

        # When the number of required CDR3 sequences for the given epitope
        # is be larger than the number of available non-epitope sequence pairs
        # only sample this latter amount.
        if n > possible_cdr3.size:
            logger.warning(
                f"Epitope sequence {epitope} requires more CDR3 sequences than the number of available unique CDR3 sequences associated with other epitopes in the provided datasets ({possible_cdr3.size}). Only this many negatives will be generated for this epitope, instead of the expected {n}."
            )
            n = possible_cdr3.size

        # sample without replacement to avoid accidental duplicates
        # among the negatives for the given epitope
        sample_df = pd.DataFrame(
            np.random.choice(possible_cdr3, size=n, replace=False),
            columns=[cdr3_column],
        )

        sample_df[epitope_column] = epitope

        negative_list.append(sample_df)

    negative_df = pd.concat(negative_list)

    return negative_df


def sample_epitope_per_cdr3(
    cdr3: str,
    df: pd.DataFrame,
    full_df: pd.DataFrame,
    cdr3_column: str = "cdr3",
    epitope_column: str = "antigen.epitope",
    seed: int = 42,
) -> (str, str):
    """Sample an epitope for the given CDR3 sequence from the pool of other epitopes in the original positive dataset.

    Does not preserve the ratio of positives and negatives within each epitope,
    but does result in every CDR3 sequence having exactly 1 positive and negative.

    NOTE: do not use a fixed random_state for the sample function, since this will result in the same epitope
    being returned every time (for cdr3s with the same original epitope).

    Parameters
    ----------
    cdr3 : str
        The cdr3 sequence that should be matched with a negative epitope.
    df : pd.DataFrame
        A positive cdr3-epitope DataFrame with a "cdr3" and "antigen.epitope" column.
        Must have a class label column ("y") with "1" as the positive label.
    full_df : pd.DataFrame
        The entire cdr3-epitope DataFrame, before splitting into folds, restricting length or downsampling.
        Used to avoid generating false negatives. Should only contain positive values.
    cdr3_column : str
        The header for the cdr3 column in the DataFrame.
    epitope_column : str
        The header for the epitope column in the DataFrame.
    seed : int
        Random state to use for sampling. Must be incremented upon multiple uses or the same pair
        will be drawn every time.

    Returns
    -------
    Tuple
        A tuple of a negative cdr3 and epitope sequence pair.
    """

    # full_df should only contain positive pairs, and consequently no y column should be present yet
    assert "y" not in full_df.columns

    # TODO: instead of having to retry matching CDR3s 50 times if they fail to match with a valid epitope
    # add the negative cdr3-epitope pairs to the epitopes_to_exclude list. Then, if the possible_epitopes
    # list is empty, this means that all epitopes in the dataset are either present in a positive example of this cdr3,
    # or a negative one, but either way the set of epitopes is excluded. Then a warning can be printed
    # and this cdr3 can be rejected. Afterwards, all rejected (nans) should be counted,
    # and the same amount of new cdr3s should be drawn again, while printing a warning that certain cdr3s are being
    # re-used in order to achieve the 50:50 pos-neg balance.

    # check which epitopes occur as a positive partner for the current cdr3 in the full dataset
    epitopes_to_exclude = full_df.loc[(full_df[cdr3_column] == cdr3), epitope_column]
    # epitopes_to_exclude = df.loc[
    #     (df[cdr3_column] == cdr3) & (df["y"] == 1), epitope_column
    # ]
    # NOTE: for this to work, the original data source should either remain unmodified (to avoid epitopes paired with
    # the cdr3 as a negative example from showing up in this list), or by making sure the class labels are 1, in which
    # case the original dataframe should be given class labels before the sample_epitope_per_cdr3 function is called for the first time.

    # create pd.Series with all epitopes except for those that are positive partners of the current cdr3

    # isin is faster even if there' just a single epitope, so use it by default
    # %timeit df["antigen.epitope"].isin(["LGYGFVNYI"])
    # 410 µs ± 19.3 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)
    # %timeit df["antigen.epitope"] != "LGYGFVNYI"
    # 1.46 ms ± 24.9 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)

    possible_epitopes = df.loc[
        ~df[epitope_column].isin(epitopes_to_exclude), epitope_column,
    ]

    # check if list is empty => cdr3 binds to every epitope present
    if possible_epitopes.empty:
        logger = logging.getLogger(__name__)
        logger.warning(
            f"CDR3 sequence {cdr3} is associated with every epitope in the dataset and will be discarded from the negatives."
        )
        return cdr3, np.NaN

    # sample 1 epitope from this list to pair with the cdr3 as a negative example
    # sampling should happen uniformly across all epitopes in their original distributions,
    # because the negatives should have a similar epitope distribution to the positives, i.e.
    # the list of possible epitopes should not be deduplicated or uniqued.
    else:
        sampled_epitope = possible_epitopes.sample(n=1, random_state=seed).iloc[0]
        return cdr3, sampled_epitope


def augment_negatives(negative_source, df, cdr3_range, amount):

    epitopes = (
        df.loc[df["y"] == 1, "antigen.epitope"]
        .sample(n=amount, random_state=42)
        .reset_index(drop=True)
    )

    negative_source = ControlCDR3Source(
        filepath=negative_source, min_length=cdr3_range[0], max_length=cdr3_range[1],
    )

    cdr3 = (
        negative_source.data[negative_source.headers["cdr3_header"]]
        .sample(n=amount, random_state=42)
        .reset_index(drop=True)
        .rename("cdr3")
    )
    negative_df = pd.concat([cdr3, epitopes], axis=1)
    negative_df["y"] = 0

    df = df.append(negative_df).reset_index(drop=True)

    to_do_df = df.loc[df.duplicated(subset=["cdr3", "antigen.epitope"], keep="last")]

    # remove duplicates from merged dataframe
    df = df.drop_duplicates(
        subset=["cdr3", "antigen.epitope"], keep="first",
    ).reset_index(drop=True)

    amount = to_do_df.shape[0]
    seed = 42
    while amount > 0:
        seed += 1
        epitopes = (
            df.loc[df["y"] == 1, "y"]
            .sample(n=amount, random_state=seed)
            .reset_index(drop=True)
        )
        cdr3 = (
            negative_source.data[negative_source.headers["cdr3_header"]]
            .sample(n=amount, random_state=seed)
            .reset_index(drop=True)
            .rename("cdr3")
        )
        negative_df = pd.concat([cdr3, epitopes], axis=1)
        negative_df["y"] = 0
        df = df.append(negative_df).reset_index(drop=True)
        to_do_df = df.loc[
            df.duplicated(subset=["cdr3", "antigen.epitope"], keep="last")
        ]
        df = df.drop_duplicates(
            subset=["cdr3", "antigen.epitope"], keep="first",
        ).reset_index(drop=True)
        amount = to_do_df.shape[0]

    return df


# def sample_epitope_per_epitope(
#     df: pd.DataFrame,
#     full_df: pd.DataFrame,
#     cdr3_column: str = "cdr3",
#     epitope_column: str = "antigen.epitope",
# ):
#     """NOT USED. See second NOTE below.
#     """
#     # full_df should only contain positive pairs, and consequently no y column should be present yet
#     assert "y" not in full_df.columns

#     # create list to store dataframes for every epitope
#     negative_list = []

#     # loop through every observation per epitope
#     for epitope in df[epitope_column].unique():
#         # extract number of required observations for current epitope
#         n = df[df[epitope_column] == epitope].shape[0]

#         # extract the CDR3 sequences paired with this epitope
#         cdr3_list = df.loc[df[epitope_column] == epitope, cdr3_column]

#         # check which other epitopes occur as a positive partner for all the
#         # CDR3 sequences associated with the current epitope in the full dataset
#         # NOTE: this makes the assumption that, given the followning pairs:
#         # cdr3 A - epitope 1
#         # cdr3 B - epitope 1
#         # cdr3 A - epitope 2
#         # that cdr3 B should not be matched with epitope 2, because
#         # one of its partner CDR3s that binds the same epitope (1),
#         # can bind epitope 2 as well.
#         epitopes_to_exclude = full_df.loc[
#             full_df[cdr3_column].isin(cdr3_list), epitope_column
#         ].unique()

#         # NOTE: don't deduplicate this list to preserve as much of the epitope distribution as possible
#         possible_epitopes = df.loc[
#             ~df[epitope_column].isin(epitopes_to_exclude), epitope_column
#         ]

#         # check if list is empty => epitope binds to every CDR3 present
#         if possible_epitopes.size == 0:
#             logger = logging.getLogger(__name__)
#             logger.warning(
#                 f"No epitopes found that are not bound by at least some CDR3 sequences that also bind the current epitope {epitope}. This epitope and its CDR3 sequences will be discarded from the negatives."
#             )
#             continue

#         # sample with replacement if n is be larger than the number available non-epitope sequence pairs
#         if n > possible_epitopes.size:
#             logger.warning(
#                 f"CDR3 sequences associated with {epitope} require more negative epitopes than the number of available epitopes in the provided datasets ({possible_epitopes.size}). Only this many negatives will be generated for this epitope, instead of the expected {n}."
#             )
#             n = possible_epitopes.size

#         sample_df = pd.DataFrame(
#             np.random.choice(possible_epitopes, size=n, replace=False),
#             columns=[epitope_column],
#         )

#         sample_df[cdr3_column] = cdr3_list

#         negative_list.append(sample_df)

#     negative_df = pd.concat(negative_list)

#     return negative_df
