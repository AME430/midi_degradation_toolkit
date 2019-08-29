import pandas as pd
import numpy as np
import re
import pytest

import mdtk.data_structures as ds
import mdtk.degradations as deg

EMPTY_DF = pd.DataFrame({
    'onset': [],
    'track' : [],
    'pitch': [],
    'dur': []
})

BASIC_DF = pd.DataFrame({
    'onset': [0, 100, 200, 200],
    'track': [0, 1, 0, 1],
    'pitch': [10, 20, 30, 40],
    'dur': [100, 100, 100, 100]
})

def test_pitch_shift():
    comp = ds.Composition(EMPTY_DF)
    
    with pytest.warns(UserWarning, match=re.escape("WARNING: No notes to pitch "
                                                   "shift. Returning None.")):
        assert deg.pitch_shift(comp) == None, ("Pitch shifting with empty data "
                                               "frame did not return None.")
    
    comp = ds.Composition(BASIC_DF)
    
    # Deterministic testing
    for i in range(2):
        comp2 = deg.pitch_shift(comp, seed=1)
    
        basic_res = pd.DataFrame({'onset': [0, 100, 200, 200],
                                  'track': [0, 1, 0, 1],
                                  'pitch': [10, 107, 30, 40],
                                  'dur': [100, 100, 100, 100]})
        
        assert (comp2.note_df == basic_res).all().all(), (f"Pitch shifting \n{BASIC_DF}\n"
                                                          f"resulted in \n{comp2.note_df}\n"
                                                          f"instead of \n{basic_res}")
        
        changed = comp != comp2 and BASIC_DF is not comp2.note_df
        assert changed, "Composition or note_df was not cloned."
        
    
    # Truly random testing
    for i in range(10):
        np.random.seed()
        
        comp2 = deg.pitch_shift(comp, min_pitch=100 * i, max_pitch=100 * (i + 1))
        
        equal = (comp2.note_df == BASIC_DF)
        
        # Check that only things that should have changed have changed
        assert equal['onset'].all(), "Pitch shift changed some onset time."
        assert equal['track'].all(), "Pitch shift changed some track."
        assert equal['dur'].all(), "Pitch shift changed some duration."
        assert (1 - equal['pitch']).sum() == 1, ("Pitch shift did not change "
                                                 "exactly one pitch.")
        
        # Check that changed pitch is within given range
        changed_pitch = comp2.note_df[(comp2.note_df['pitch'] !=
                                       BASIC_DF['pitch'])]['pitch'].iloc[0]
        assert 100 * i <= changed_pitch <= 100 * (i + 1), (f"Pitch {changed_pitch} "
                                                           f"outside of range [{100 * i}"
                                                           f", {100 * (i + 1)}]")
        
        # Check a simple setting of the distribution parameter
        distribution = np.zeros(3)
        sample = np.random.randint(3)
        if sample == 1:
            sample = 2
        distribution[sample] = 1
        correct_diff = 1 - sample
        
        comp2 = deg.pitch_shift(comp, distribution=distribution)
        
        not_equal = (comp2.note_df['pitch'] != BASIC_DF['pitch'])
        changed_pitch = comp2.note_df[not_equal]['pitch'].iloc[0]
        original_pitch = BASIC_DF[not_equal]['pitch'].iloc[0]
        diff = original_pitch - changed_pitch
        
        assert diff == correct_diff, (f"Pitch difference {diff} is not equal to correct "
                                      f" difference {correct_diff} with distribution = "
                                      f"length 50 list of 0's with 1 at index {sample}.")
        
    # Check for distribution warnings
    with pytest.warns(UserWarning, match=re.escape('WARNING: distribution contains only '
                                                   '0s after setting middle value to 0. '
                                                   'Returning None.')):
        comp2 = deg.pitch_shift(comp, distribution=[0, 1, 0])
        assert comp2 == None, "Pitch shifting with distribution of 0s returned something."
        
    with pytest.warns(UserWarning, match=re.escape('WARNING: No valid pitches to shift '
                                                   'given min_pitch')):
        comp2 = deg.pitch_shift(comp, min_pitch=-50, max_pitch=-20, distribution=[1, 0, 1])
        assert comp2 == None, "Pitch shifting with invalid distribution returned something."
        
    comp2 = deg.pitch_shift(comp, min_pitch=BASIC_DF['pitch'].min() - 1,
                            max_pitch=BASIC_DF['pitch'].min() - 1, distribution=[1, 0, 0])
    assert comp2 is not None, "Valid shift down of 1 pitch returned None."
    
    with pytest.warns(UserWarning, match=re.escape('WARNING: No valid pitches to shift '
                                                   'given min_pitch')):
        comp2 = deg.pitch_shift(comp, min_pitch=BASIC_DF['pitch'].min() - 2,
                                max_pitch=BASIC_DF['pitch'].min() - 2, distribution=[1, 0, 0])
        assert comp2 is None, "Invalid shift down of 2 pitch returned something."
    
    comp2 = deg.pitch_shift(comp, min_pitch=BASIC_DF['pitch'].max() + 1,
                            max_pitch=BASIC_DF['pitch'].max() + 1, distribution=[0, 0, 1])
    assert comp2 is not None, "Valid shift up of 1 pitch returned None."
    
    with pytest.warns(UserWarning, match=re.escape('WARNING: No valid pitches to shift '
                                                   'given min_pitch')):
        comp2 = deg.pitch_shift(comp, min_pitch=BASIC_DF['pitch'].max() + 2,
                                max_pitch=BASIC_DF['pitch'].max() + 2, distribution=[0, 0, 1])
        assert comp2 is None, "Invalid shift up of 2 pitch returned something."



def test_time_shift():
    comp = ds.Composition(EMPTY_DF)
    
    with pytest.warns(UserWarning, match=re.escape("WARNING: No valid notes to time "
                                                   "shift. Returning None.")):
        assert deg.time_shift(comp) == None, ("Time shifting with empty data "
                                              "frame did not return None.")
    
    comp = ds.Composition(BASIC_DF)
    
    # Deterministic testing
    for i in range(2):
        comp2 = deg.time_shift(comp, seed=1)
    
        basic_res = pd.DataFrame({'onset': [0, 158, 200, 200],
                                  'track': [0, 1, 0, 1],
                                  'pitch': [10, 20, 30, 40],
                                  'dur': [100, 100, 100, 100]})
        
        assert (comp2.note_df == basic_res).all().all(), (f"Time shifting \n{BASIC_DF}\n"
                                                          f"resulted in \n{comp2.note_df}\n"
                                                          f"instead of \n{basic_res}")
        
        changed = comp != comp2 and BASIC_DF is not comp2.note_df
        assert changed, "Composition or note_df was not cloned."
        
    # Truly random testing
    for i in range(10):
        np.random.seed()
        
        comp2 = deg.time_shift(comp, min_shift=10 * i, max_shift=10 * (i + 1))
        
        equal = (comp2.note_df == BASIC_DF)
        
        # Check that only things that should have changed have changed
        assert equal['track'].all(), "Time shift changed some track."
        assert equal['pitch'].all(), "Time shift changed some pitch."
        assert equal['dur'].all(), "Time shift changed some duration."
        assert (1 - equal['onset']).sum() == 1, ("Time shift did not change "
                                                 "exactly one onset.")
        
        # Check that changed onset is within given range
        changed_onset = comp2.note_df[(comp2.note_df['onset'] !=
                                       BASIC_DF['onset'])]['onset'].iloc[0]
        original_onset = BASIC_DF[(comp2.note_df['onset'] !=
                                   BASIC_DF['onset'])]['onset'].iloc[0]
        shift = abs(changed_onset - original_onset)
        assert 10 * i <= shift <= 10 * (i + 1), (f"Shift {shift} outside of range"
                                                 f" [{10 * i}, {10 * (i + 1)}].")
        
    # Check for range too large warning
    with pytest.warns(UserWarning, match=re.escape('WARNING: No valid notes to '
                                                   'time shift.')):
        comp2 = deg.time_shift(comp, min_shift=201, max_shift=202)
        assert comp2 is None, "Invalid time shift of 201 returned something."
    
    comp2 = deg.time_shift(comp, min_shift=200, max_shift=201)
    assert comp2 is not None, "Valid time shift of 200 returned None."
    

    
def test_onset_shift():
    pass



def test_offset_shift():
    pass



def test_remove_note():
    comp = ds.Composition(EMPTY_DF)
    
    with pytest.warns(UserWarning, match=re.escape("WARNING: No notes to "
                                                   "remove. Returning None.")):
        assert deg.remove_note(comp) == None, ("Remove note with empty data "
                                               "frame did not return None.")
        
    comp = ds.Composition(BASIC_DF)
        
    # Deterministic testing
    for i in range(2):
        comp2 = deg.remove_note(comp, seed=1)
    
        basic_res = pd.DataFrame({'onset': [0, 200, 200],
                                  'track': [0, 0, 1],
                                  'pitch': [10, 30, 40],
                                  'dur': [100, 100, 100]})
        
        assert (comp2.note_df == basic_res).all().all(), (f"Removing note from \n"
                                                          f"{BASIC_DF}\n resulted"
                                                          f" in \n{comp2.note_df}\n"
                                                          f"instead of \n{basic_res}")
        
        changed = comp != comp2 and BASIC_DF is not comp2.note_df
        assert changed, "Composition or note_df was not cloned."
        
    # Random testing
    for i in range(10):
        np.random.seed()
        
        comp2 = deg.remove_note(comp)
        merged = pd.merge(BASIC_DF, comp2.note_df)
        
        assert merged.shape[0] == BASIC_DF.shape[0] - 1, ("Remove note did not remove"
                                                          " exactly 1 note.")



def test_add_note():
    comp = ds.Composition(EMPTY_DF)
    assert deg.add_note(comp) is not None, ("Add note to empty data "
                                            "frame returned None.")
    
    comp = ds.Composition(BASIC_DF)
    
    # Deterministic testing
    for i in range(2):
        comp2 = deg.add_note(comp, seed=1)
    
        basic_res = pd.DataFrame({'onset': [0, 100, 200, 200, 235],
                                  'track': [0, 1, 0, 1, 0],
                                  'pitch': [10, 20, 30, 40, 37],
                                  'dur': [100, 100, 100, 100, 62]})
        
        assert (comp2.note_df == basic_res).all().all(), (f"Adding note to \n"
                                                          f"{BASIC_DF}\n resulted"
                                                          f" in \n{comp2.note_df}\n"
                                                          f"instead of \n{basic_res}")
        
    # Random testing
    for i in range(10):
        min_pitch = i * 10
        max_pitch = (i + 1) * 10
        min_duration = i * 10
        max_duration = (i + 1) * 10
        
        comp2 = deg.add_note(comp, min_pitch=min_pitch, max_pitch=max_pitch,
                             min_duration=min_duration, max_duration=max_duration)
        
        assert (comp2.note_df[:BASIC_DF.shape[0]] == BASIC_DF).all().all(), ("Adding a note"
                                                                             "changed an "
                                                                             "existing note.")
        assert comp2.note_df.shape[0] == BASIC_DF.shape[0] + 1, "No note was added."
        
        note = comp2.note_df.loc[BASIC_DF.shape[0]]
        assert min_pitch <= note['pitch'] <= max_pitch, (f"Added note's pitch ({note.pitch})"
                                                         f" not within range "
                                                         f" [{min_pitch}, {max_pitch}].")
        assert min_duration <= note['dur'] <= max_duration, (f"Added note's duration "
                                                             f"({note.pitch}) not within"
                                                             f" range [{min_duration}, "
                                                             f"{max_duration}].")
        assert (note['onset'] >= 0 and note['onset'] + note['dur'] <=
                BASIC_DF[['onset', 'dur']].sum(axis=1).max()), ("Added note's onset and "
                                                                "duration do not lie within"
                                                                " bounds of given dataframe.")
        
    # Test min_duration too large
    comp2 = deg.add_note(comp, min_duration=500)
    assert (comp2.note_df.loc[BASIC_DF.shape[0]]['onset'] == 0 and
            comp2.note_df.loc[BASIC_DF.shape[0]]['dur'] == 500), ("Adding note with large "
                                                                  "min_duration does not set"
                                                                  " to full dataframe length.")
        



def test_split_note():
    comp = ds.Composition(EMPTY_DF)
    
    with pytest.warns(UserWarning, match=re.escape("WARNING: No notes to "
                                                   "split. Returning None.")):
        assert deg.split_note(comp) == None, ("Split note with empty data "
                                              "frame did not return None.")
    
    comp = ds.Composition(BASIC_DF)
    
    # Deterministic testing
    for i in range(2):
        comp2 = deg.split_note(comp, seed=1)
    
        basic_res = pd.DataFrame({'onset': [0, 100, 200, 200, 150],
                                  'track': [0, 1, 0, 1, 1],
                                  'pitch': [10, 20, 30, 40, 20],
                                  'dur': [100, 50, 100, 100, 50]})
        
        assert (comp2.note_df == basic_res).all().all(), (f"Splitting note in \n"
                                                          f"{BASIC_DF}\n resulted"
                                                          f" in \n{comp2.note_df}\n"
                                                          f"instead of \n{basic_res}")
        
    # Random testing
    for i in range(8):
        num_splits = i + 1
        num_notes = num_splits + 1
        
        comp2 = deg.split_note(comp, min_duration=10, num_splits=num_splits)
        
        diff = pd.concat([comp2.note_df, BASIC_DF]).drop_duplicates(keep=False)
        new_notes = pd.merge(diff, comp2.note_df).reset_index()
        changed_notes = pd.merge(diff, BASIC_DF).reset_index()
        unchanged_notes = pd.merge(comp2.note_df, BASIC_DF).reset_index()
        
        assert changed_notes.shape[0] == 1, "More than 1 note changed when splitting."
        assert unchanged_notes.shape[0] == BASIC_DF.shape[0] - 1, ("More than 1 note "
                                                                   "changed when "
                                                                   "splitting.")
        assert new_notes.shape[0] == num_notes, f"Did not split into {num_notes} notes."
        
        # Check first new note
        assert (new_notes.loc[0]['pitch'] ==
                changed_notes.loc[0]['pitch']), "Pitch changed when splitting."
        assert (new_notes.loc[0]['track'] ==
                changed_notes.loc[0]['track']), "Track changed when splitting."
        assert (new_notes.loc[0]['onset'] ==
                changed_notes.loc[0]['onset']), "Onset changed when splitting."
        
        # Check duration and remainder of notes
        total_duration = new_notes.loc[0]['dur']
        
        notes = list(new_notes.iterrows())
        for prev_note, next_note in zip(notes[:-1], notes[1:]):
            total_duration += next_note[1]['dur']
            
            assert prev_note[1]['pitch'] == next_note[1]['pitch'], ("Pitch changed "
                                                                    "when splitting.")
            assert prev_note[1]['track'] == next_note[1]['track'], ("Track changed "
                                                                    "when splitting.")
            assert (prev_note[1]['onset'] + prev_note[1]['dur']
                    == next_note[1]['onset']), ("Offset/onset times of split notes "
                                                "not aligned.")
            
            
        assert total_duration == changed_notes.loc[0]['dur'], ("Duration changed "
                                                               "when splitting.")
        
    # Test min_duration too large for num_splits
    with pytest.warns(UserWarning, match=re.escape("WARNING: No valid notes to"
                                                   " split. Returning None.")):
        assert deg.split_note(comp,
                              min_duration=10,
                              num_splits=10) == None, ("Splitting note into "
                                                       "too many pieces didn't"
                                                       " return None.")



def test_join_notes():
    pass