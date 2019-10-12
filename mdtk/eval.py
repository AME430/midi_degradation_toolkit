"""Module containing methods to evaluate performance on Error Correction"""
from mir_eval.transcription import precision_recall_f1_overlap


def helpfulness(corrected_df, degraded_df, clean_df, time_increment=40):
    """
    Get the helpfulness of an excerpt, given the degraded and clean versions.

    Parameters
    ----------
    corrected_df : pd.DataFrame
        The data frame of the corrected excerpt as output by a model.

    degraded_df : pd.DataFrame
        The degraded excerpt given as input to the model.

    clean_df : pd.DataFrame
        The clean excerpt expected as output.

    time_increment : int
        The length of a frame to use when performing evaluations.

    Returns
    -------
    helpfulness : float
        The helpfulness of the given correction, defined as follows:
        -- First, take the mean of the note-based and frame-based F-measures
           of corrected and degraded.
        -- If degraded's score is 1, the mean of note-based and frame-based
           F-measures of corrected vs clean is the output.
        -- Else, using 0.0 == 0.0, degraded == 0.5 and clean == 1.0 as anchor
           points, place corrected's score on that scale.
    """
    # Use this for note-based F-measure
    #precision_recall_f1_overlap(ref_intervals, ref_pitches, est_intervals, est_pitches, onset_tolerance=0.05, pitch_tolerance=50.0, offset_ratio=0.2, offset_min_tolerance=0.05, strict=False, beta=1.0)
    corrected_fm = 0 # TODO: Get F-measure
    # TODO: also get frame-based

    if corrected_fm == 0 or corrected_fm == 1 or degraded_df.equals(clean_df):
        return corrected_fm

    degraded_fm = 0 # TODO: Calculate this
    # TODO: Also get frame-based

    if corrected_fm < degraded_fm:
        return 0.5 * corrected_fm / degraded_fm
    else:
        return 1 - 0.5 * (1 - corrected_fm) / (1 - degraded_fm)
