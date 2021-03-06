import itertools

import numpy as np
import pandas as pd
import pytest

import mdtk.degradations as deg

EMPTY_DF = pd.DataFrame({"onset": [], "track": [], "pitch": [], "dur": []})

# test_join_notes() uses its own df, defined in the function
# Create a garbled df with indices: [0, 2, 2, 4]
BASIC_DF = pd.DataFrame(
    {
        "onset": [0, 100, 200, 200, 200],
        "track": [0, 1, 0, 1, 1],
        "pitch": [10, 20, 30, 40, 40],
        "dur": [100, 100, 100, 100, 100],
    }
)
BASIC_DF = pd.concat([BASIC_DF.iloc[[0, 2]], BASIC_DF.iloc[[2, 4]]])
BASIC_DF.iloc[1]["onset"] = 100
BASIC_DF.iloc[1]["track"] = 1
BASIC_DF.iloc[1]["pitch"] = 20
BASIC_DF.iloc[1]["dur"] = 100

# This version will not change
BASIC_DF_FINAL = BASIC_DF

# Create an unsorted BASIC_DF
UNSORTED_DF = BASIC_DF.iloc[[0, 2, 3, 1]]


def assert_none(res, msg=""):
    assert res is None, f"{msg}\nExpected None, but got:\n{res}"


def assert_warned(caplog, msg=None):
    assert caplog.records[-1].levelname == "WARNING", "Warning not logged."
    if msg:
        assert msg in caplog.text, "Warning message incorrect."
    caplog.clear()


def test_pre_process():
    basic_res = pd.DataFrame(
        {
            "onset": [0, 100, 200, 200],
            "track": [0, 1, 0, 1],
            "pitch": [10, 20, 30, 40],
            "dur": [100, 100, 100, 100],
        }
    )

    unsorted_res = pd.DataFrame(
        {
            "onset": [0, 200, 200, 100],
            "track": [0, 0, 1, 1],
            "pitch": [10, 30, 40, 20],
            "dur": [100, 100, 100, 100],
        }
    )

    res = deg.pre_process(UNSORTED_DF)
    assert res.equals(unsorted_res), (
        f"Pre-processing \n{UNSORTED_DF}\n resulted in \n{res}\n"
        f"instead of \n{unsorted_res}"
    )

    res = deg.pre_process(UNSORTED_DF, sort=True)
    assert res.equals(basic_res), (
        f"Pre-processing \n{UNSORTED_DF}\n with sort=True resulted in "
        f"\n{res}\ninstead of \n{basic_res}"
    )

    float_df = pd.DataFrame(
        {
            "track": [0, 1, 0, 1.5],
            "onset": [0.5, 100.5, 200.5, 200.5],
            "pitch": [10, 20, 30.5, 40],
            "dur": [100, 100, 100.5, 100],
            "extra": [5, 5, "apple", None],
        }
    )
    float_res = pd.DataFrame(
        {
            "onset": [0, 100, 200, 200],
            "track": [0, 1, 0, 2],
            "pitch": [10, 20, 30, 40],
            "dur": [100, 100, 100, 100],
        }
    )
    res = deg.pre_process(float_df)
    assert res.equals(float_res), (
        f"Pre-processing \n{float_df}\n resulted in \n{res}\n"
        f"instead of \n{float_res}"
    )

    # Check not correct columns raises ValueError
    invalid_df = pd.DataFrame({"track": [0, 1], "onset": [0, 50], "pitch": [10, 20]})
    with pytest.raises(ValueError):
        deg.pre_process(invalid_df)


def test_post_process():
    basic_res = pd.DataFrame(
        {
            "onset": [0, 100, 200, 200],
            "track": [0, 1, 0, 1],
            "pitch": [10, 20, 30, 40],
            "dur": [100, 100, 100, 100],
        }
    )

    unsorted_res = pd.DataFrame(
        {
            "onset": [0, 200, 200, 100],
            "track": [0, 0, 1, 1],
            "pitch": [10, 30, 40, 20],
            "dur": [100, 100, 100, 100],
        }
    )

    res = deg.post_process(UNSORTED_DF, sort=False)
    assert res.equals(unsorted_res), (
        f"Post-processing \n{UNSORTED_DF}\n resulted in \n{res}\n"
        f"instead of \n{unsorted_res}\n with sort=False"
    )

    res = deg.post_process(UNSORTED_DF, sort=True)
    assert res.equals(basic_res), (
        f"Post-processing \n{UNSORTED_DF}\n with sort=True resulted in "
        f"\n{res}\ninstead of \n{basic_res}"
    )


def test_overlaps():
    fixed_basic = deg.pre_process(BASIC_DF)
    assert not deg.overlaps(
        fixed_basic, 0
    ), f"Overlaps incorrectly returned True for:\n{fixed_basic}."

    fixed_basic.loc[0, "onset"] = 50
    assert not deg.overlaps(
        fixed_basic, 0
    ), f"Overlaps incorrectly returned True for:\n{fixed_basic}."

    fixed_basic.loc[0, "pitch"] = 20
    assert not deg.overlaps(
        fixed_basic, 0
    ), f"Overlaps incorrectly returned True for:\n{fixed_basic}."

    fixed_basic.loc[0, "track"] = 1
    fixed_basic.loc[0, "onset"] = 0
    assert not deg.overlaps(
        fixed_basic, 0
    ), f"Overlaps incorrectly returned True for:\n{fixed_basic}."

    fixed_basic.loc[0, "onset"] = 50
    assert deg.overlaps(
        fixed_basic, 0
    ), f"Overlaps incorrectly returned False for:\n{fixed_basic}."

    fixed_basic.loc[0, "onset"] = 150
    assert deg.overlaps(
        fixed_basic, 0
    ), f"Overlaps incorrectly returned False for:\n{fixed_basic}."

    fixed_basic.loc[0, "dur"] = 25
    assert deg.overlaps(
        fixed_basic, 0
    ), f"Overlaps incorrectly returned False for:\n{fixed_basic}."

    fixed_basic.loc[0, "dur"] = 150
    fixed_basic.loc[0, "onset"] = 75
    assert deg.overlaps(
        fixed_basic, 0
    ), f"Overlaps incorrectly returned False for:\n{fixed_basic}."


def test_unsorted(caplog):
    global BASIC_DF
    BASIC_DF = UNSORTED_DF

    test_pitch_shift(caplog)
    test_time_shift(caplog)
    test_onset_shift(caplog)
    test_offset_shift(caplog)
    test_remove_note(caplog)
    test_add_note(caplog)
    test_split_note(caplog)

    BASIC_DF = BASIC_DF_FINAL


def test_pitch_shift(caplog):
    res = deg.pitch_shift(EMPTY_DF)
    assert_none(res, msg="Pitch shifting with empty data frame did not return None.")
    assert_warned(caplog)

    if BASIC_DF.equals(BASIC_DF_FINAL):
        # Deterministic testing
        for i in range(2):
            res = deg.pitch_shift(BASIC_DF, seed=1)

            basic_res = pd.DataFrame(
                {
                    "onset": [0, 100, 200, 200],
                    "track": [0, 1, 0, 1],
                    "pitch": [10, 33, 30, 40],
                    "dur": [100, 100, 100, 100],
                }
            )

            assert res.equals(basic_res), (
                f"Pitch shifting \n{BASIC_DF}\n resulted in \n{res}\n"
                f"instead of \n{basic_res}"
            )

            assert not BASIC_DF.equals(res), "Note_df was not copied."

    # Test if tries works
    df = pd.DataFrame({"onset": [0], "pitch": [10], "track": [0], "dur": [100]})
    res = deg.pitch_shift(df, min_pitch=10, max_pitch=10)
    assert_none(res, msg="Pitch shift should run out of tries.")
    assert_warned(caplog, msg=deg.TRIES_WARN_MSG)

    # Truly random testing
    for i in range(10):
        np.random.seed()

        res = deg.pitch_shift(BASIC_DF, min_pitch=100 * i, max_pitch=100 * (i + 1))

        # Check that only things that should have changed have changed
        diff = pd.concat([res, BASIC_DF]).drop_duplicates(keep=False)
        assert diff.shape[0] == 2, "Pitch shift changed more than 1 note."
        assert (
            diff.iloc[0]["onset"] == diff.iloc[1]["onset"]
        ), "Pitch shift changed some onset time."
        assert (
            diff.iloc[0]["track"] == diff.iloc[1]["track"]
        ), "Pitch shift changed some track."
        assert (
            diff.iloc[0]["dur"] == diff.iloc[1]["dur"]
        ), "Pitch shift changed some duration."
        assert (
            diff.iloc[0]["pitch"] != diff.iloc[1]["pitch"]
        ), "Pitch shift did not change pitch."

        # Check that changed pitch is within given range
        changed_pitch = diff.iloc[0]["pitch"]
        # changed_pitch = res[(res['pitch'] !=
        #                     BASIC_DF['pitch'])]['pitch'].iloc[0]
        assert 100 * i <= changed_pitch <= 100 * (i + 1), (
            f"Pitch {changed_pitch} outside of range " f"[{100 * i}, {100 * (i + 1)}]"
        )

        # Check a simple setting of the distribution parameter
        distribution = np.zeros(3)
        sample = np.random.randint(3)
        if sample == 1:
            sample = 2
        distribution[sample] = 1
        correct_diff = 1 - sample

        res = deg.pitch_shift(BASIC_DF, distribution=distribution)

        diff = pd.concat([res, BASIC_DF]).drop_duplicates(keep=False)
        changed_pitch = diff.iloc[0]["pitch"]
        original_pitch = diff.iloc[1]["pitch"]
        diff = original_pitch - changed_pitch

        assert diff == correct_diff, (
            f"Pitch difference {diff} is not equal to correct difference "
            f"{correct_diff} with distribution = length 50 list of 0's with "
            f"1 at index {sample}."
        )

    # Check for distribution warnings
    res = deg.pitch_shift(BASIC_DF, distribution=[0, 1, 0])
    assert_none(res, msg="Pitch shifting with distribution of 0s returned something.")
    assert_warned(
        caplog,
        msg="distribution contains only 0s after "
        "setting distribution[zero_idx] value to 0. "
        "Returning None.",
    )

    res = deg.pitch_shift(
        BASIC_DF, min_pitch=-50, max_pitch=-20, distribution=[1, 0, 1]
    )
    assert_none(res, msg="Pitch shifting with invalid distribution returned something.")
    assert_warned(caplog, msg="No valid pitches to shift given min_pitch")

    res = deg.pitch_shift(
        BASIC_DF,
        min_pitch=BASIC_DF["pitch"].min() - 1,
        max_pitch=BASIC_DF["pitch"].min() - 1,
        distribution=[1, 0, 0],
    )
    assert res is not None, "Valid shift down of 1 pitch returned None."

    res = deg.pitch_shift(
        BASIC_DF,
        min_pitch=BASIC_DF["pitch"].min() - 2,
        max_pitch=BASIC_DF["pitch"].min() - 2,
        distribution=[1, 0, 0],
    )
    assert_none(res, msg="Invalid shift down of 2 pitch returned something.")
    assert_warned(caplog, msg="No valid pitches to shift given min_pitch")

    res = deg.pitch_shift(
        BASIC_DF,
        min_pitch=BASIC_DF["pitch"].max() + 1,
        max_pitch=BASIC_DF["pitch"].max() + 1,
        distribution=[0, 0, 1],
    )
    assert res is not None, "Valid shift up of 1 pitch returned None."

    res = deg.pitch_shift(
        BASIC_DF,
        min_pitch=BASIC_DF["pitch"].max() + 2,
        max_pitch=BASIC_DF["pitch"].max() + 2,
        distribution=[0, 0, 1],
    )
    assert_none(res, msg="Invalid shift up of 2 pitch returned something.")
    assert_warned(caplog, msg="No valid pitches to shift given min_pitch")


def test_time_shift(caplog):
    assert_none(
        deg.time_shift(EMPTY_DF),
        msg="Time shifting with empty data frame did not return None.",
    )
    assert_warned(caplog, "No valid notes to time shift. Returning None.")

    if BASIC_DF.equals(BASIC_DF_FINAL):
        # Deterministic testing
        for i in range(2):
            res = deg.time_shift(BASIC_DF, seed=1)

            basic_res = pd.DataFrame(
                {
                    "onset": [0, 200, 200, 200],
                    "track": [0, 0, 1, 1],
                    "pitch": [10, 30, 20, 40],
                    "dur": [100, 100, 100, 100],
                }
            )

            assert res.equals(basic_res), (
                f"Time shifting \n{BASIC_DF}\nresulted in \n{res}\n"
                f"instead of \n{basic_res}"
            )

            assert not BASIC_DF.equals(res), "Note_df was not copied."

    # Truly random testing
    for i in range(10):
        np.random.seed()

        min_shift = 10 * i
        max_shift = 10 * (i + 1)
        res = deg.time_shift(BASIC_DF, min_shift=min_shift, max_shift=max_shift)

        # Check that only things that should have changed have changed
        diff = pd.concat([res, BASIC_DF]).drop_duplicates(keep=False)
        assert diff.shape[0] == 2, "Time shift changed more than 1 note."
        assert (
            diff.iloc[0]["onset"] != diff.iloc[1]["onset"]
        ), "Time shift did not change any onset time."
        assert (
            diff.iloc[0]["track"] == diff.iloc[1]["track"]
        ), "Time shift changed some track."
        assert (
            diff.iloc[0]["dur"] == diff.iloc[1]["dur"]
        ), "Time shift changed some duration."
        assert (
            diff.iloc[0]["pitch"] == diff.iloc[1]["pitch"]
        ), "Time shift changed some pitch."

        # Check that changed onset is within given range
        changed_onset = diff.iloc[0]["onset"]
        original_onset = diff.iloc[1]["onset"]
        shift = abs(changed_onset - original_onset)
        assert (
            min_shift <= shift <= max_shift
        ), f"Shift {shift} outside of range [{min_shift}, {max_shift}]."

        # Check with align_onset=True
        if min_shift <= 200 and max_shift >= 100:
            res = deg.time_shift(
                BASIC_DF, min_shift=min_shift, max_shift=max_shift, align_onset=True
            )

            # Check that only things that should have changed have changed
            diff = pd.concat([res, BASIC_DF]).drop_duplicates(keep=False)
            assert diff.shape[0] == 2, (
                "Time shift changed more than 1 note."
                + f"\n{BASIC_DF}\n{res}\n{min_shift}_{max_shift}"
            )
            assert (
                diff.iloc[0]["onset"] != diff.iloc[1]["onset"]
            ), "Time shift did not change any onset time."
            assert (
                diff.iloc[0]["track"] == diff.iloc[1]["track"]
            ), "Time shift changed some track."
            assert (
                diff.iloc[0]["dur"] == diff.iloc[1]["dur"]
            ), "Time shift changed some duration."
            assert (
                diff.iloc[0]["pitch"] == diff.iloc[1]["pitch"]
            ), "Time shift changed some pitch."
            assert (
                diff.iloc[0]["onset"] in BASIC_DF["onset"].unique()
            ), "Time shift didn't change to an aligned onset."

            # Check that changed onset is within given range
            changed_onset = diff.iloc[0]["onset"]
            original_onset = diff.iloc[1]["onset"]
            shift = abs(changed_onset - original_onset)
            assert (
                min_shift <= shift <= max_shift
            ), f"Shift {shift} outside of range [{min_shift}, {max_shift}]."
        else:
            res = deg.time_shift(
                BASIC_DF, min_shift=min_shift, max_shift=max_shift, align_onset=True
            )
            assert_warned(caplog)

    # Check for range too large warning
    res = deg.time_shift(BASIC_DF, min_shift=201, max_shift=202)
    assert_none(res, msg="Invalid time shift of 201 returned something.")
    assert_warned(caplog, msg="No valid notes to time shift.")

    res = deg.time_shift(BASIC_DF, min_shift=200, max_shift=201)
    assert res is not None, "Valid time shift of 200 returned None."


def test_onset_shift(caplog):
    def check_onset_shift_result(
        df, res, min_shift, max_shift, min_duration, max_duration
    ):
        assert res is not None, "Onset shift returned None unexpectedly."

        diff = pd.concat([res, df]).drop_duplicates(keep=False)
        new_note = pd.merge(diff, res).reset_index()
        changed_note = pd.merge(diff, df).reset_index()
        unchanged_notes = pd.merge(res, df).reset_index()

        assert (
            unchanged_notes.shape[0] == df.shape[0] - 1
        ), "More or less than 1 note changed when shifting onset."
        assert (
            changed_note.shape[0] == 1
        ), "More than 1 note changed when shifting onset."
        assert new_note.shape[0] == 1, "More than 1 new note added when shifting onset."
        assert (
            min_duration <= new_note.loc[0]["dur"] <= max_duration
        ), "Note duration not within bounds when onset shifting."
        assert (
            min_shift
            <= abs(new_note.loc[0]["onset"] - changed_note.loc[0]["onset"])
            <= max_shift
        ), "Note shifted outside of bounds when onset shifting."
        assert (
            new_note.loc[0]["pitch"] == changed_note.loc[0]["pitch"]
        ), "Pitch changed when onset shifting."
        assert (
            new_note.loc[0]["track"] == changed_note.loc[0]["track"]
        ), "Track changed when onset shifting."
        assert (
            changed_note.loc[0]["onset"] + changed_note.loc[0]["dur"]
            == new_note.loc[0]["onset"] + new_note.loc[0]["dur"]
        ), "Offset changed when onset shifting."
        assert (
            changed_note.loc[0]["onset"] >= 0
        ), "Changed note given negative onset time."

    assert_none(
        deg.onset_shift(EMPTY_DF),
        msg="Onset shifting with empty data frame did not return None.",
    )
    assert_warned(caplog, msg="No valid notes to onset shift. Returning None.")

    if BASIC_DF.equals(BASIC_DF_FINAL):
        # Deterministic testing
        for i in range(2):
            res = deg.onset_shift(BASIC_DF, seed=1)

            basic_res = pd.DataFrame(
                {
                    "onset": [0, 72, 100, 200],
                    "track": [0, 0, 1, 1],
                    "pitch": [10, 30, 20, 40],
                    "dur": [100, 228, 100, 100],
                }
            )

            assert res.equals(basic_res), (
                f"Onset shifting \n{BASIC_DF}\nresulted in \n{res}\n"
                f"instead of \n{basic_res}"
            )

            assert not BASIC_DF.equals(res), "Note_df was not copied."

    # Random testing
    for i in range(10):
        np.random.seed()

        min_shift = i * 10
        max_shift = (i + 1) * 10

        # Cut min/max shift in half towards less shift
        min_duration = 100 - min_shift - 5
        max_duration = 100 + min_shift + 5
        res = deg.onset_shift(
            BASIC_DF,
            min_shift=min_shift,
            max_shift=max_shift,
            min_duration=min_duration,
            max_duration=max_duration,
        )
        check_onset_shift_result(
            BASIC_DF, res, min_shift, max_shift, min_duration, max_duration
        )

        # Duration is too short
        min_duration = 0
        max_duration = 100 - max_shift - 1

        res = deg.onset_shift(
            BASIC_DF,
            min_shift=min_shift,
            max_shift=max_shift,
            min_duration=min_duration,
            max_duration=max_duration,
        )
        assert_none(
            res, msg="Onset shift with max_duration too short didn't return None."
        )
        assert_warned(caplog, msg="No valid notes to onset shift. Returning None.")

        # Duration is barely short enough
        min_duration = 0
        max_duration = 100 - max_shift
        res = deg.onset_shift(
            BASIC_DF,
            min_shift=min_shift,
            max_shift=max_shift,
            min_duration=min_duration,
            max_duration=max_duration,
        )
        check_onset_shift_result(
            BASIC_DF, res, min_shift, max_shift, min_duration, max_duration
        )

        # Duration is too long
        min_duration = 100 + max_shift + 1
        max_duration = np.inf

        res = deg.onset_shift(
            BASIC_DF,
            min_shift=min_shift,
            max_shift=max_shift,
            min_duration=min_duration,
            max_duration=max_duration,
        )
        assert_none(
            res, msg="Onset shift with min_duration too long didn't return None."
        )
        assert_warned(caplog, msg="No valid notes to onset shift. Returning None.")

        # Duration is barely short enough
        min_duration = 100 + max_shift
        max_duration = np.inf
        res = deg.onset_shift(
            BASIC_DF,
            min_shift=min_shift,
            max_shift=max_shift,
            min_duration=min_duration,
            max_duration=max_duration,
        )
        check_onset_shift_result(
            BASIC_DF, res, min_shift, max_shift, min_duration, max_duration
        )

        # Duration is shortest half of shift
        min_duration = 0
        max_duration = 100 - min_shift - 5
        res = deg.onset_shift(
            BASIC_DF,
            min_shift=min_shift,
            max_shift=max_shift,
            min_duration=min_duration,
            max_duration=max_duration,
        )
        check_onset_shift_result(
            BASIC_DF, res, min_shift, max_shift, min_duration, max_duration
        )

        # Duration is longest half of shift
        min_duration = 100 + min_shift + 5
        max_duration = np.inf
        res = deg.onset_shift(
            BASIC_DF,
            min_shift=min_shift,
            max_shift=max_shift,
            min_duration=min_duration,
            max_duration=max_duration,
        )
        check_onset_shift_result(
            BASIC_DF, res, min_shift, max_shift, min_duration, max_duration
        )

        # Test with various alignments
        align_df = pd.DataFrame(
            {
                "onset": [0, 50, 100, 150, 200],
                "track": [0, 1, 0, 0, 1],
                "pitch": [10, 20, 25, 30, 40],
                "dur": [100, 100, 50, 150, 100],
            }
        )
        # Test with align_dur
        res = deg.onset_shift(align_df, align_dur=True)
        check_onset_shift_result(align_df, res, 50, np.inf, 50, np.inf)

        assert (
            100 in list(res["dur"])
            and (50 in list(res["dur"]) or 150 in list(res["dur"]))
            and res["dur"].isin([50, 100, 150]).all()
        ), "Onset with align_dur didn't align duration."

        res = deg.onset_shift(align_df, align_dur=True, min_shift=101)
        assert_none(res)
        assert_warned(caplog)
        res = deg.onset_shift(align_df, align_dur=True, max_shift=49)
        assert_none(res)
        assert_warned(caplog)
        res = deg.onset_shift(align_df, align_dur=True, min_duration=151)
        assert_none(res)
        assert_warned(caplog)
        res = deg.onset_shift(align_df, align_dur=True, max_duration=49)
        assert_none(res)
        assert_warned(caplog)

        # Test with align_onset
        res = deg.onset_shift(align_df, align_onset=True)
        check_onset_shift_result(align_df, res, 50, np.inf, 50, np.inf)

        assert (
            len(set([0, 50, 100, 150, 200]) - set(res["onset"])) == 1
            and len(set(res["onset"])) == 4
        ), "Onset with align_onset didn't align onset."

        res = deg.onset_shift(align_df, align_dur=True, min_shift=201)
        assert_none(res)
        assert_warned(caplog)
        res = deg.onset_shift(align_df, align_dur=True, max_shift=49)
        assert_none(res)
        assert_warned(caplog)
        res = deg.onset_shift(align_df, align_dur=True, min_duration=301)
        assert_none(res)
        assert_warned(caplog)
        res = deg.onset_shift(align_df, align_dur=True, max_duration=49)
        assert_none(res)
        assert_warned(caplog)

        # Test with align both
        res = deg.onset_shift(align_df, align_onset=True, align_dur=True)
        check_onset_shift_result(align_df, res, 50, np.inf, 50, np.inf)

        assert (
            100 in list(res["dur"])
            and (50 in list(res["dur"]) or 150 in list(res["dur"]))
            and res["dur"].isin([50, 100, 150]).all()
        ), "Onset with align_dur and align_onset didn't align duration."
        assert (
            len(set([0, 50, 100, 150, 200]) - set(res["onset"])) == 1
            and len(set(res["onset"])) == 4
        ), "Onset with align_dur and align_onset didn't align onset."

        res = deg.onset_shift(align_df, align_dur=True, min_shift=101)
        assert_none(res)
        assert_warned(caplog)
        res = deg.onset_shift(align_df, align_dur=True, max_shift=49)
        assert_none(res)
        assert_warned(caplog)
        res = deg.onset_shift(align_df, align_dur=True, min_duration=151)
        assert_none(res)
        assert_warned(caplog)
        res = deg.onset_shift(align_df, align_dur=True, max_duration=49)
        assert_none(res)
        assert_warned(caplog)

    res = deg.onset_shift(BASIC_DF, min_shift=300)
    assert_none(
        res,
        msg="Onset shifting with empty data min_shift greater than "
        "possible additional duration did not return None.",
    )
    assert_warned(caplog, msg="No valid notes to onset shift. Returning None.")


def test_offset_shift(caplog):
    def check_offset_shift_result(
        df, res, min_shift, max_shift, min_duration, max_duration
    ):
        diff = pd.concat([res, df]).drop_duplicates(keep=False)
        new_note = pd.merge(diff, res).reset_index()
        changed_note = pd.merge(diff, df).reset_index()
        unchanged_notes = pd.merge(res, df).reset_index()

        assert (
            unchanged_notes.shape[0] == df.shape[0] - 1
        ), "More or less than 1 note changed when shifting offset."
        assert (
            changed_note.shape[0] == 1
        ), "More than 1 note changed when shifting offset."
        assert (
            new_note.shape[0] == 1
        ), "More than 1 new note added when shifting offset."
        assert (
            min_duration <= new_note.loc[0]["dur"] <= max_duration
        ), "Note duration not within bounds when offset shifting."
        assert (
            min_shift
            <= abs(new_note.loc[0]["dur"] - changed_note.loc[0]["dur"])
            <= max_shift
        ), "Note offset shifted outside of bounds when onset shifting."
        assert (
            new_note.loc[0]["pitch"] == changed_note.loc[0]["pitch"]
        ), "Pitch changed when offset shifting."
        assert (
            new_note.loc[0]["track"] == changed_note.loc[0]["track"]
        ), "Track changed when offset shifting."
        assert (
            changed_note.loc[0]["onset"] == new_note.loc[0]["onset"]
        ), "Onset changed when offset shifting."
        assert (
            changed_note.loc[0]["onset"] + changed_note.loc[0]["dur"]
            <= df[["onset", "dur"]].sum(axis=1).max()
        ), "Changed note offset shifted past previous last offset."

    assert_none(
        deg.offset_shift(EMPTY_DF),
        msg="Offset shifting with empty data frame did not return None.",
    )
    assert_warned(caplog, msg="No valid notes to offset shift. Returning None.")

    if BASIC_DF.equals(BASIC_DF_FINAL):
        # Deterministic testing
        for i in range(2):
            res = deg.offset_shift(BASIC_DF, seed=1)
            basic_res = pd.DataFrame(
                {
                    "onset": [0, 100, 200, 200],
                    "track": [0, 1, 0, 1],
                    "pitch": [10, 20, 30, 40],
                    "dur": [100, 200, 100, 100],
                }
            )

            assert res.equals(basic_res), (
                f"Offset shifting \n{BASIC_DF}\nresulted in \n{res}\n"
                f"instead of \n{basic_res}"
            )
            assert not BASIC_DF.equals(res), "Note_df was not copied."

            res = deg.offset_shift(BASIC_DF, seed=1, align_dur=True)
            assert_none(
                res,
                msg=(
                    "Offset shift with align_dur doesn't fail on excerpt with "
                    "only 1 duration."
                ),
            )
            assert_warned(caplog)

    # Random testing
    for i in range(10):
        np.random.seed()

        min_shift = i * 10
        max_shift = (i + 1) * 10

        # Cut min/max shift in half towards less shift
        min_duration = 100 - min_shift - 5
        max_duration = 100 + min_shift + 5
        res = deg.offset_shift(
            BASIC_DF,
            min_shift=min_shift,
            max_shift=max_shift,
            min_duration=min_duration,
            max_duration=max_duration,
        )
        check_offset_shift_result(
            BASIC_DF, res, min_shift, max_shift, min_duration, max_duration
        )

        # Duration is too short
        min_duration = 0
        max_duration = 100 - max_shift - 1

        res = deg.offset_shift(
            BASIC_DF,
            min_shift=min_shift,
            max_shift=max_shift,
            min_duration=min_duration,
            max_duration=max_duration,
        )
        assert_none(
            res, msg="Offset shift with max_duration too short didn't return None."
        )
        assert_warned(caplog, msg="No valid notes to offset shift. Returning None.")

        # Duration is barely short enough
        min_duration = 0
        max_duration = 100 - max_shift
        res = deg.offset_shift(
            BASIC_DF,
            min_shift=min_shift,
            max_shift=max_shift,
            min_duration=min_duration,
            max_duration=max_duration,
        )
        check_offset_shift_result(
            BASIC_DF, res, min_shift, max_shift, min_duration, max_duration
        )

        # Duration is too long
        min_duration = 100 + max_shift + 1
        max_duration = np.inf

        res = deg.offset_shift(
            BASIC_DF,
            min_shift=min_shift,
            max_shift=max_shift,
            min_duration=min_duration,
            max_duration=max_duration,
        )
        assert_none(
            res, msg="Offset shift with min_duration too long didn't return None."
        )
        assert_warned(caplog, msg="No valid notes to offset shift. Returning None.")

        # Duration is barely short enough
        min_duration = 100 + max_shift
        max_duration = np.inf
        res = deg.offset_shift(
            BASIC_DF,
            min_shift=min_shift,
            max_shift=max_shift,
            min_duration=min_duration,
            max_duration=max_duration,
        )
        check_offset_shift_result(
            BASIC_DF, res, min_shift, max_shift, min_duration, max_duration
        )

        # Duration is shortest half of shift
        min_duration = 0
        max_duration = 100 - min_shift - 5
        res = deg.offset_shift(
            BASIC_DF,
            min_shift=min_shift,
            max_shift=max_shift,
            min_duration=min_duration,
            max_duration=max_duration,
        )
        check_offset_shift_result(
            BASIC_DF, res, min_shift, max_shift, min_duration, max_duration
        )

        # Duration is longest half of shift
        min_duration = 100 + min_shift + 5
        max_duration = np.inf
        res = deg.offset_shift(
            BASIC_DF,
            min_shift=min_shift,
            max_shift=max_shift,
            min_duration=min_duration,
            max_duration=max_duration,
        )
        check_offset_shift_result(
            BASIC_DF, res, min_shift, max_shift, min_duration, max_duration
        )

        # Test align_dur
        align_df = BASIC_DF.copy()
        align_df.iloc[0]["dur"] = 150

        if (min_duration <= 150 and max_duration >= 100) and (
            min_shift <= 50 <= max_shift
        ):
            res = deg.offset_shift(
                align_df,
                min_shift=min_shift,
                max_shift=max_shift,
                min_duration=min_duration,
                max_duration=max_duration,
                align_dur=True,
            )
            assert (
                tuple(res["dur"]) in list(itertools.permutations([150, 150, 100, 100]))
            ) or (
                list(res["dur"]) == [100, 100, 100, 100]
            ), "Offset shift with align_dur doesn't properly align duration."

        else:
            res = deg.offset_shift(BASIC_DF, min_shift=300)
            assert_none(
                res,
                msg=(
                    "Offset shifting with align_dur but all durs outside valid "
                    "range returns something."
                ),
            )
            assert_warned(caplog)

    res = deg.offset_shift(BASIC_DF, min_shift=300)
    assert_none(
        res,
        msg=(
            "Offset shifting with empty data min_shift greater than possible "
            "additional note duration did not return None."
        ),
    )
    assert_warned(caplog, msg="No valid notes to offset shift. Returning None.")


def test_remove_note(caplog):
    assert_none(
        deg.remove_note(EMPTY_DF),
        msg="Remove note with empty data frame did not return None.",
    )
    assert_warned(caplog, "No notes to remove. Returning None.")

    if BASIC_DF.equals(BASIC_DF_FINAL):
        # Deterministic testing
        for i in range(2):
            res = deg.remove_note(BASIC_DF, seed=1)

            basic_res = pd.DataFrame(
                {
                    "onset": [0, 200, 200],
                    "track": [0, 0, 1],
                    "pitch": [10, 30, 40],
                    "dur": [100, 100, 100],
                }
            )

            assert res.equals(basic_res), (
                f"Removing note from \n{BASIC_DF}\n resulted in "
                f"\n{res}\ninstead of \n{basic_res}"
            )

            assert not BASIC_DF.equals(res), "Note_df was not copied."

    # Random testing
    for i in range(10):
        np.random.seed()

        res = deg.remove_note(BASIC_DF)
        merged = pd.merge(BASIC_DF, res)

        assert (
            merged.shape[0] == BASIC_DF.shape[0] - 1
        ), "Remove note did not remove exactly 1 note."


def test_add_note(caplog):
    assert (
        deg.add_note(EMPTY_DF) is not None
    ), "Add note to empty data frame returned None."

    # Deterministic testing
    for i in range(2):
        res = deg.add_note(BASIC_DF, seed=1)

        basic_res = pd.DataFrame(
            {
                "onset": [0, 100, 200, 200, 235],
                "track": [0, 1, 0, 1, 0],
                "pitch": [10, 20, 30, 40, 58],
                "dur": [100, 100, 100, 100, 62],
            }
        )

        assert res.equals(basic_res), (
            f"Adding note to \n{BASIC_DF}\n resulted in "
            f"\n{res}\ninstead of \n{basic_res}"
        )

        assert not BASIC_DF.equals(res), "Note_df was not copied."

    # Random testing
    for i in range(10):
        np.random.seed()

        min_pitch = i * 10
        max_pitch = (i + 1) * 10
        min_duration = i * 50
        max_duration = (i + 1) * 50

        res = deg.add_note(
            BASIC_DF,
            min_pitch=min_pitch,
            max_pitch=max_pitch,
            min_duration=min_duration,
            max_duration=max_duration,
        )

        diff = pd.concat([res, BASIC_DF]).drop_duplicates(keep=False)
        assert (
            diff.shape[0] == 1
        ), "Adding a note changed an existing note, or added note is a duplicate."
        assert res.shape[0] == BASIC_DF.shape[0] + 1, "No note was added."

        note = diff.iloc[0]
        assert min_pitch <= note["pitch"] <= max_pitch, (
            f"Added note's pitch ({note.pitch}) not within range "
            f"[{min_pitch}, {max_pitch}]."
        )
        assert min_duration <= note["dur"] <= max_duration, (
            f"Added note's duration ({note.dur}) not within range "
            f"[{min_duration}, {max_duration}]."
        )

        end_time = BASIC_DF[["onset", "dur"]].sum(axis=1).max()
        if min_duration >= end_time:
            assert note["onset"] == 0 and note["dur"] == min_duration, (
                "min_duration > df length, but note[['onset', 'dur']] != 0, "
                "min_duration"
            )
        else:
            assert (
                note["onset"] >= 0
                and note["onset"] + note["dur"]
                <= BASIC_DF[["onset", "dur"]].sum(axis=1).max()
            ), (
                "Added note's onset and duration do not lie within "
                "bounds of given dataframe."
            )

        # Test align_pitch and align_time
        if (
            min_pitch > BASIC_DF["pitch"].max()
            or max_pitch < BASIC_DF["pitch"].min()
            or min_duration > BASIC_DF["dur"].max()
            or max_duration < BASIC_DF["dur"].min()
        ):
            res = deg.add_note(
                BASIC_DF,
                min_pitch=min_pitch,
                max_pitch=max_pitch,
                min_duration=min_duration,
                max_duration=max_duration,
                align_pitch=True,
                align_time=True,
            )
            assert_warned(caplog)
            continue

        res = deg.add_note(
            BASIC_DF,
            min_pitch=min_pitch,
            max_pitch=max_pitch,
            min_duration=min_duration,
            max_duration=max_duration,
            align_pitch=True,
            align_time=True,
        )
        diff = pd.concat([res, BASIC_DF]).drop_duplicates(keep=False)
        assert diff.shape[0] == 1, (
            "Adding a note changed an existing note, or added note is a duplicate.\n"
            f"{BASIC_DF}\n{res}"
        )
        assert res.shape[0] == BASIC_DF.shape[0] + 1, "No note was added."
        note = diff.iloc[0]
        assert note["pitch"] in list(
            BASIC_DF["pitch"]
        ), f"Added note's pitch ({note.pitch}) not aligned to \n{BASIC_DF}"
        assert note["dur"] in list(
            BASIC_DF["dur"]
        ), f"Added note's duration ({note.dur}) not aligned to \n{BASIC_DF}"
        assert note["onset"] in list(
            BASIC_DF["onset"]
        ), f"Added note's onset ({note.onset}) not aligned to \n{BASIC_DF}"

    # Test min_duration too large
    res = deg.add_note(BASIC_DF, min_duration=500)
    diff = pd.concat([res, BASIC_DF]).drop_duplicates(keep=False)
    note = diff.iloc[0]
    assert note["onset"] == 0 and note["dur"] == 500, (
        "Adding note with large min_duration does not set duration "
        "to full dataframe length."
    )


def test_split_note(caplog):
    assert_none(
        deg.split_note(EMPTY_DF),
        msg="Split note with empty data frame did not return None.",
    )
    assert_warned(caplog, msg="No notes to split. Returning None.")

    if BASIC_DF.equals(BASIC_DF_FINAL):
        # Deterministic testing
        for i in range(2):
            res = deg.split_note(BASIC_DF, seed=1)

            basic_res = pd.DataFrame(
                {
                    "onset": [0, 100, 150, 200, 200],
                    "track": [0, 1, 1, 0, 1],
                    "pitch": [10, 20, 20, 30, 40],
                    "dur": [100, 50, 50, 100, 100],
                }
            )

            assert res.equals(basic_res), (
                f"Splitting note in \n{BASIC_DF}\n resulted in "
                f"\n{res}\ninstead of \n{basic_res}"
            )

            assert not BASIC_DF.equals(res), "Note_df was not copied."

    # Random testing
    for i in range(8):
        np.random.seed()

        num_splits = i + 1
        num_notes = num_splits + 1

        res = deg.split_note(BASIC_DF, min_duration=10, num_splits=num_splits)

        diff = pd.concat([res, BASIC_DF]).drop_duplicates(keep=False)
        new_notes = pd.merge(diff, res).reset_index()
        changed_notes = pd.merge(diff, BASIC_DF).reset_index()
        unchanged_notes = pd.merge(res, BASIC_DF).reset_index()

        print("READY")
        print(BASIC_DF)
        print(res)
        print(diff)
        print(new_notes)
        print(changed_notes)
        print(unchanged_notes)

        assert changed_notes.shape[0] == 1, "More than 1 note changed when splitting."
        assert (
            unchanged_notes.shape[0] == BASIC_DF.shape[0] - 1
        ), "More than 1 note changed when splitting."
        assert new_notes.shape[0] == num_notes, f"Did not split into {num_notes} notes."

        # Check first new note
        assert (
            new_notes.loc[0]["pitch"] == changed_notes.loc[0]["pitch"]
        ), "Pitch changed when splitting."
        assert (
            new_notes.loc[0]["track"] == changed_notes.loc[0]["track"]
        ), "Track changed when splitting."
        assert (
            new_notes.loc[0]["onset"] == changed_notes.loc[0]["onset"]
        ), "Onset changed when splitting."

        # Check duration and remainder of notes
        total_duration = new_notes.loc[0]["dur"]

        notes = list(new_notes.iterrows())
        for prev_note, next_note in zip(notes[:-1], notes[1:]):
            total_duration += next_note[1]["dur"]

            assert (
                prev_note[1]["pitch"] == next_note[1]["pitch"]
            ), "Pitch changed when splitting."
            assert (
                prev_note[1]["track"] == next_note[1]["track"]
            ), "Track changed when splitting."
            assert (
                prev_note[1]["onset"] + prev_note[1]["dur"] == next_note[1]["onset"]
            ), "Offset/onset times of split notes not aligned."

        assert (
            total_duration == changed_notes.loc[0]["dur"]
        ), "Duration changed when splitting."

    # Test min_duration too large for num_splits
    assert_none(
        deg.split_note(BASIC_DF, min_duration=10, num_splits=10),
        msg="Splitting note into too many pieces didn't return None.",
    )
    assert_warned(caplog, msg="No valid notes to split. Returning None.")


def test_join_notes(caplog):
    assert_none(
        deg.join_notes(EMPTY_DF),
        msg="Join notes with empty data frame did not return None.",
    )
    assert_warned(caplog, msg="No notes to join. Returning None.")

    assert_none(
        deg.join_notes(BASIC_DF),
        msg="Joining notes with none back-to-back didn't return None.",
    )
    assert_warned(caplog, msg="No valid notes to join. Returning None.")

    # Create a garbled df with indices: [0, 2, 2, 4]
    join_df = pd.DataFrame(
        {
            "onset": [0, 100, 200, 200, 200],
            "track": [0, 0, 0, 1, 1],
            "pitch": [10, 10, 10, 40, 40],
            "dur": [100, 100, 100, 100, 100],
        }
    )
    join_df = pd.concat([join_df.iloc[[0, 2]], join_df.iloc[[2, 4]]])
    join_df.iloc[1]["onset"] = 100
    join_df.iloc[1]["track"] = 0
    join_df.iloc[1]["pitch"] = 10
    join_df.iloc[1]["dur"] = 100

    # Create an unsorted join_df
    unsorted_join_df = join_df.iloc[[0, 2, 3, 1]]

    # Deterministic testing
    for i in range(2):
        res = deg.join_notes(join_df, seed=1)

        join_res = pd.DataFrame(
            {
                "onset": [0, 100, 200],
                "track": [0, 0, 1],
                "pitch": [10, 10, 40],
                "dur": [100, 200, 100],
            }
        )

        assert res.equals(join_res), (
            f"Joining \n{join_df}\nresulted in \n{res}\n" f"instead of \n{join_res}"
        )

        res = deg.join_notes(unsorted_join_df, seed=1)
        assert res.equals(join_res), (
            f"Joining \n{unsorted_join_df}\nresulted in \n{res}\n"
            f"instead of \n{join_res}"
        )

        assert not join_df.equals(res), "Note_df was not copied."

    # Check different pitch and track
    join_df.iloc[1]["pitch"] = 20
    assert_none(
        deg.join_notes(join_df),
        msg="Joining notes with different pitches didn't return None.",
    )
    assert_warned(caplog, msg="No valid notes to join. Returning None.")

    join_df.iloc[1]["pitch"] = 10
    join_df.iloc[1]["track"] = 1
    assert_none(
        deg.join_notes(join_df),
        msg="Joining notes with different tracks didn't return None.",
    )
    assert_warned(caplog, msg="No valid notes to join. Returning None.")

    # Test real example which erred (because it had multiple possible notes)
    excerpt = pd.DataFrame(
        {
            "onset": [
                0,
                250,
                625,
                875,
                1000,
                1500,
                1750,
                1875,
                2250,
                2625,
                2875,
                3000,
                3250,
                3375,
                3625,
                3750,
                3875,
                4000,
                4250,
                4625,
                4875,
                5000,
            ],
            "track": [0] * 22,
            "pitch": [
                47,
                47,
                47,
                50,
                43,
                43,
                43,
                43,
                50,
                50,
                62,
                50,
                50,
                62,
                62,
                48,
                48,
                47,
                47,
                47,
                50,
                43,
            ],
            "dur": [83] + [125] * 10 + [83] + [125] * 5 + [83] + [125] * 4,
        }
    )
    correct = pd.DataFrame(
        {
            "onset": [
                0,
                250,
                625,
                875,
                1000,
                1500,
                1750,
                1875,
                2250,
                2625,
                2875,
                3000,
                3250,
                3375,
                3625,
                3750,
                4000,
                4250,
                4625,
                4875,
                5000,
            ],
            "track": [0] * 21,
            "pitch": [
                47,
                47,
                47,
                50,
                43,
                43,
                43,
                43,
                50,
                50,
                62,
                50,
                50,
                62,
                62,
                48,
                47,
                47,
                47,
                50,
                43,
            ],
            "dur": [83] + [125] * 10 + [83] + [125] * 3 + [250, 83] + [125] * 4,
        }
    )
    res = deg.join_notes(excerpt, seed=1)
    assert res.equals(correct), (
        "join_notes failed on excerpt with multiple "
        "pitches containing joinable notes." + f"{res}"
    )

    # Check some with different max_gaps
    join_df.iloc[1]["track"] = 0
    for i in range(10):
        np.random.seed()

        max_gap = i * 10

        join_df.iloc[0]["dur"] = (
            join_df.iloc[1]["onset"] - max_gap - join_df.iloc[0]["onset"]
        )
        join_df.iloc[1]["dur"] = (
            join_df.iloc[2]["onset"] - max_gap - join_df.iloc[1]["onset"]
        )

        res = deg.join_notes(join_df, max_notes=2, max_gap=max_gap)

        # Gap should work
        diff = pd.concat([res, join_df]).drop_duplicates(keep=False)
        new_note = pd.merge(diff, res).reset_index()
        joined_notes = pd.merge(diff, join_df).reset_index()
        unchanged_notes = pd.merge(res, join_df).reset_index()

        assert (
            unchanged_notes.shape[0] == join_df.shape[0] - 2
        ), "Joining notes changed too many notes."
        assert new_note.shape[0] == 1, "Joining notes resulted in more than 1 new note."
        assert joined_notes.shape[0] == 2, "Joining notes changed too many notes."
        assert (
            new_note.loc[0]["onset"] == joined_notes.loc[0]["onset"]
        ), "Joined onset not equal to original onset."
        assert (
            new_note.loc[0]["pitch"] == joined_notes.loc[0]["pitch"]
        ), "Joined pitch not equal to original pitch."
        assert (
            new_note.loc[0]["track"] == joined_notes.loc[0]["track"]
        ), "Joined track not equal to original pitch."
        assert (
            new_note.loc[0]["dur"]
            == joined_notes.iloc[-1]["onset"]
            + joined_notes.iloc[-1]["dur"]
            - joined_notes.loc[0]["onset"]
        ), "Joined duration not equal to original durations plus gap."

        # Test joining multiple notes at first
        max_notes = max(2, i)
        num_joined = min(max_notes, 3)
        res = deg.join_notes(
            join_df, max_notes=max_notes, only_first=True, max_gap=max_gap
        )

        diff = pd.concat([res, join_df]).drop_duplicates(keep=False)
        new_note = pd.merge(diff, res).reset_index(drop=True)
        joined_notes = pd.merge(diff, join_df).reset_index(drop=True)
        unchanged_notes = pd.merge(res, join_df).reset_index(drop=True)

        assert (
            unchanged_notes.shape[0] == join_df.shape[0] - num_joined
        ), "Joining notes changed too many notes."
        assert new_note.shape[0] == 1, "Joining notes resulted in more than 1 new note."
        assert (
            joined_notes.shape[0] == num_joined
        ), "Joining notes changed too many notes."
        assert joined_notes.loc[0].equals(
            join_df.loc[0]
        ), "Joining didn't start at first."
        assert (
            new_note.loc[0]["onset"] == joined_notes.loc[0]["onset"]
        ), "Joined onset not equal to original onset."
        assert (
            new_note.loc[0]["pitch"] == joined_notes.loc[0]["pitch"]
        ), "Joined pitch not equal to original pitch."
        assert (
            new_note.loc[0]["track"] == joined_notes.loc[0]["track"]
        ), "Joined track not equal to original pitch."
        assert (
            new_note.loc[0]["dur"]
            == joined_notes.iloc[-1]["onset"]
            + joined_notes.iloc[-1]["dur"]
            - joined_notes.loc[0]["onset"]
        ), "Joined duration not equal to original durations plus gap."

        # Test joining multiple notes not at first
        res = deg.join_notes(join_df, max_notes=max_notes, max_gap=max_gap)

        diff = pd.concat([res, join_df]).drop_duplicates(keep=False)
        new_note = pd.merge(diff, res).reset_index()
        joined_notes = pd.merge(diff, join_df).reset_index()
        unchanged_notes = pd.merge(res, join_df).reset_index()

        assert (
            unchanged_notes.shape[0] >= join_df.shape[0] - max_notes
            and unchanged_notes.shape[0] <= join_df.shape[0] - 2
        ), "Joining notes changed too many notes."
        assert new_note.shape[0] == 1, "Joining notes resulted in more than 1 new note."
        assert 2 <= joined_notes.shape[0] <= 3, "Joining notes changed too many notes."
        assert (
            new_note.loc[0]["onset"] == joined_notes.loc[0]["onset"]
        ), "Joined onset not equal to original onset."
        assert (
            new_note.loc[0]["pitch"] == joined_notes.loc[0]["pitch"]
        ), "Joined pitch not equal to original pitch."
        assert (
            new_note.loc[0]["track"] == joined_notes.loc[0]["track"]
        ), "Joined track not equal to original pitch."
        assert (
            new_note.loc[0]["dur"]
            == joined_notes.iloc[-1]["onset"]
            + joined_notes.iloc[-1]["dur"]
            - joined_notes.loc[0]["onset"]
        ), "Joined duration not equal to original durations plus gap."

        join_df.iloc[0]["dur"] -= 1
        join_df.iloc[1]["dur"] -= 1

        # Gap too large
        assert_none(
            deg.join_notes(join_df, max_gap=max_gap),
            msg="Joining notes with too large of a gap didn't return None.",
        )
        assert_warned(caplog, msg="No valid notes to join. Returning None.")
