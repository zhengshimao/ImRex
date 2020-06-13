import logging

import numpy as np
import pandas as pd

from src.data.control_cdr3_source import ControlCDR3Source


def add_negatives(df, full_dataset_path):
    """Generate negative CDR3-epitope pairs through shuffling and add them to the DataFrame.

    Parameters
    ----------
    df : DataFrame
        A DataFrame containing CDR3 and epitope sequence pairs, derived from a relevant Stream object. Should only contain positives, as a "y" column with 1s.
    full_dataset_path : [type]
        Path to the entire cdr3-epitope dataset, before splitting into folds, restricting length or downsampling. Used to avoid generating false negatives during shuffling. Should only contain positive values.

    Returns
    -------
    DataFrame
        A DataFrame with the original positive CDR3-epitope pairs, and new negative pairs created by shuffling the positive ones.
    """
    logger = logging.getLogger(__name__)

    # print warning and skip generation if there is only 1 epitope
    if len(df["antigen.epitope"].unique()) == 1:
        logger.warning(
            "Cannot generate negatives through shuffling when there is only 1 epitope present in a fold. Skipping generation..."
        )
        return df

    # read in full dataset and remove duplicates to avoid generating false negatives
    full_df = (
        pd.read_csv(full_dataset_path)
        .filter(["cdr3", "antigen.epitope"])
        .drop_duplicates()
        .reset_index(drop=True)
    )

    # generate negative pairs from list of all cdr3s in positive pairs
    shuffled_pairs = [
        sample_pairs(
            cdr3=cdr3,
            df=df,
            full_df=full_df,
            cdr3_column="cdr3",
            epitope_column="antigen.epitope",
            seed=seed,
        )
        for seed, cdr3 in enumerate(df["cdr3"])
    ]

    # convert list of tuples into dataframe and add class label
    shuffled_df = pd.DataFrame(shuffled_pairs, columns=["cdr3", "antigen.epitope"],)
    shuffled_df["y"] = 0

    # merge with original positive data, ensuring positives are kept at the top of the dataframe
    df = df.append(shuffled_df).reset_index(drop=True)

    # extract duplicates
    # NOTE: because the sampling approach ensures that accidental duplicates of positive pairs (i.e. false negatives)
    #       never occur, these will all be accidental duplicate samples of negatives. Therefore, keep="last" is redundant,
    #       but it would result in the positive examples being stored in the dataframe (marking the last (=positives) as True).
    #       This is kept here for historical purposes, because before the epitope was supplied alongside the cdr3 in a zip operation
    #       during sample generation, and the associated positive epitope was used for exclusion purposes.
    to_do_df = df.loc[df.duplicated(subset=["cdr3", "antigen.epitope"], keep="last")]

    # remove duplicates from merged dataframe
    df = df.drop_duplicates(
        subset=["cdr3", "antigen.epitope"],
        keep="first",  # This should not be required, see previous NOTE: always keep the original positive examples when duplicates occur across pos/neg, i.e. remove false negatives
    ).reset_index(drop=True)

    # remove NaN to deal with any possible universal cdr3s
    df = df.dropna(axis=0, how="any", subset=["antigen.epitope"])

    # add negatives until required amount is reached
    # add fail safe in case it is mathematically impossible to do so
    n = 0
    while to_do_df.shape[0] > 0:
        n += 1
        if n > 50:
            shuffled_pairs = [
                sample_pairs(
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
            logger.warning(
                f"Could not create enough negative samples by matching every CDR3 sequence to another epitope exactly once. {len(to_do_df)} CDR3's will be re-used."
            )
        else:
            shuffled_pairs = [
                sample_pairs(
                    cdr3=cdr3,
                    df=df,
                    full_df=full_df,
                    cdr3_column="cdr3",
                    epitope_column="antigen.epitope",
                    seed=n,
                )
                for cdr3 in to_do_df["cdr3"]
            ]
        shuffled_df = pd.DataFrame(shuffled_pairs, columns=["cdr3", "antigen.epitope"],)
        shuffled_df["y"] = 0
        df = df.append(shuffled_df).reset_index(drop=True)
        to_do_df = df.loc[
            df.duplicated(subset=["cdr3", "antigen.epitope"], keep="last")
        ]
        df = df.drop_duplicates(
            subset=["cdr3", "antigen.epitope"], keep="first",
        ).reset_index(drop=True)
        df = df.dropna(axis=0, how="any", subset=["antigen.epitope"])

    return df


def sample_pairs(
    cdr3: str,
    df: pd.DataFrame,
    full_df: pd.DataFrame,
    cdr3_column: str = "cdr3",
    epitope_column: str = "antigen.epitope",
    seed: int = 42,
) -> (str, str):
    """Sample an epitope for the given CDR3 sequence from the pool of other epitopes in the original positive dataset.

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
        The entire cdr3-epitope DataFrame, before splitting into folds, restricting length or downsampling. Used to avoid
        generating false negatives. Should only contain positive values.
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

    # check which epitopes occur as a positive partner for the current cdr3 in the full dataset
    epitopes_to_exclude = full_df.loc[(full_df[cdr3_column] == cdr3), epitope_column]
    # epitopes_to_exclude = df.loc[
    #     (df[cdr3_column] == cdr3) & (df["y"] == 1), epitope_column
    # ]
    # NOTE: for this to work, the original data source should either remain unmodified (to avoid epitopes paired with
    # the cdr3 as a negative example from showing up in this list), or by making sure the class labels are 1, in which
    # case the original dataframe should be given class labels before the sample_pairs function is called for the first time.

    # create pd.Series with all epitopes except for those that are positive partners of the current cdr3

    ## isin is faster even if there' just a single epitope, so use it by default
    ## %timeit df["antigen.epitope"].isin(["LGYGFVNYI"])
    ## 410 µs ± 19.3 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)

    ## %timeit df["antigen.epitope"] != "LGYGFVNYI"
    ## 1.46 ms ± 24.9 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)

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
        sampled_epitope = possible_epitopes.sample(n=1, random_state=seed).reset_index(
            drop=True
        )[0]
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
