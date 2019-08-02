"""Code to perform the degradations i.e. edits to the midi data"""
import numpy as np
import warnings
from numpy.random import randint, uniform, choice

from mdtk.data_structures import Composition



MIN_PITCH = 0
MAX_PITCH = 127



def set_random_seed(func, seed=None):
    """This is a function decorator which just adds the keyword argument `seed`
    to the end of the supplied function that it decorates. It seeds numpy's
    random state with the provided value before the call of the function.

    Parameters
    ----------
    func : function
        function to be decorated
    seed : int or None
        A seed to be supplied to np.random.seed(). Defaults to None, which
        leaves numpy's random state unchanged.

    Returns
    -------
    seeded_func : function
        The originally supplied function, but now with an aditional optional
        seed keyword argument.
    """
    def seeded_func(*args, seed=seed, **kwargs):
        if seed is not None:
            np.random.seed(seed)
        return func(*args, **kwargs)
    return seeded_func



def split_range_sample(split_range, p=None):
    """
    Return a value sampled randomly from the given split range.
    
    Parameters
    ----------
    split_range : list(tuple)
        A list of [min, max) tuples defining ranges from which to sample.
        The sample will be drawn uniformly from the ranges, as if they were
        contiguous. For example, on an input of [(0,1),(2,3)], a sampled
        value of 1.5 will return 2.5.
        
    p : list(float)
        If given, should be a list the same length as split_range, and
        contains the probability of sampling from each range. p will be
        normalized before use. Defaults to None.
        
    Returns
    -------
    A value sampled uniformly from the given split range.
    """
    if p is None:
        total = sum([val[1] - val[0] for val in split_range])

        sample = uniform(0, total)

        for bottom, top in split_range:
            if sample < top - bottom:
                return bottom + sample
            sample -= top - bottom

        raise ValueError('ERROR: split_range_sample tried to return value ' +
                         'outside of any range.')
    
    # Here, p is used to sample a range first
    p = p / np.sum(p)
    index = choice(range(len(split_range)), p=p)
    
    return uniform(split_range[index][0], split_range[index][1])



@set_random_seed
def pitch_shift(excerpt, min_pitch=MIN_PITCH, max_pitch=MAX_PITCH,
                distribution=None):
    """
    Shift the pitch of one note from the given excerpt.

    Parameters
    ----------
    excerpt : Composition
        A Composition object of an excerpt from a piece of music.

    min_pitch : int
        The minimum pitch to which a note may be shifted.

    max_pitch : int
        The maximum pitch to which a note may be shifted.
        
    distribution : list(float)
        If given, a list describing the distribution of pitch shifts.
        Element (len(distribution) // 2) refers to the note's original
        pitch, and will be set to 0. Additionally, pitches outside of the
        range [min_pitch, max_pitch] will also be set to 0. The distribution
        will then be normalized to sum to 1, and used to generate a new
        pitch. Defaults to None, which implies a uniform distribution.

    seed : int
        A seed to be supplied to np.random.seed(). Defaults to None, which
        leaves numpy's random state unchanged.


    Returns
    -------
    degraded : Composition
        A copy of the given excerpt, with the pitch of one note changed.
    """
    if excerpt.note_df.shape[0] == 0:
        warnings.warn('WARNING: No notes to remove. Returning None.',
                      category=UserWarning)
        return None
    
    degraded = excerpt.copy()

    # Sample a random note
    note_index = randint(0, degraded.note_df.shape[0])
    pitch = degraded.note_df.loc[note_index, 'pitch']
    
    # Shift its pitch
    if distribution is None:
        # Uniform distribution
        while degraded.note_df.loc[note_index, 'pitch'] == pitch:
            degraded.note_df.loc[note_index, 'pitch'] = randint(min_pitch,
                                                                max_pitch + 1)
    else:
        middle = len(distribution) // 2
        pitches = np.array(range(pitch - middle,
                                 pitch - middle + len(distribution)))
        distribution[middle] = 0
        distribution = np.where(pitches < min_pitch, 0, distribution)
        distribution = np.where(pitches > max_pitch, 0, distribution)
        distribution = distribution / np.sum(distribution)
        degraded.note_df.loc[note_index, 'pitch'] = choice(pitches,
                                                           p=distribution)

    return degraded



@set_random_seed
def time_shift(excerpt, min_shift=50, max_shift=np.inf):
    """
    Shift the onset and offset times of one note from the given excerpt,
    leaving its duration unchanged.

    Parameters
    ----------
    excerpt : Composition
        A Composition object of an excerpt from a piece of music.

    min_shift : float
        The minimum amount by which the note will be shifted. Defaults to 50.
        
    max_shift : float
        The maximum amount by which the note will be shifted. Defaults to
        infinity.

    seed : int
        A seed to be supplied to np.random.seed(). Defaults to None, which
        leaves numpy's random state unchanged.


    Returns
    -------
    degraded : Composition
        A copy of the given excerpt, with the timing of one note changed,
        or None if there are no notes that can be changed given the
        parameters.
    """
    end_time = excerpt.note_df[['onset', 'dur']].sum(axis=1).max()
    
    # Find all editable notes
    valid_notes = []
    
    # Use indices because saving the df.loc objects creates copies
    for note_index in range(excerpt.note_df.shape[0]):
        onset = excerpt.note_df.loc[note_index, 'onset']
        offset = onset + excerpt.note_df.loc[note_index, 'dur']
        
        # Early-shift bounds (decrease onset)
        earliest_earlier_onset = max(onset - max_shift, 0)
        latest_earlier_onset = onset - min_shift
        
        # Late-shift bounds (increase onset)
        earliest_later_onset = onset + min_shift
        latest_later_onset = onset + min(max_shift,
                                         end_time - offset)
        
        # Check that sampled note is valid (can be lengthened or shortened)
        if (earliest_earlier_onset < latest_earlier_onset or
            earliest_later_onset < latest_later_onset):
            valid_notes.append((note_index,
                                onset,
                                earliest_earlier_onset,
                                latest_earlier_onset,
                                earliest_later_onset,
                                latest_later_onset))
            
    if len(valid_notes) == 0:
        warnings.warn('WARNING: No valid notes to time shift. Returning ' +
                      'None.', category=UserWarning)
        return None
    
    # Sample a random note
    (note_index,
     onset,
     earliest_earlier_onset,
     latest_earlier_onset,
     earliest_later_onset,
     latest_later_onset) = valid_notes[randint(len(valid_notes))]
    
    onset = split_range_sample([(earliest_earlier_onset,
                                 latest_earlier_onset),
                                (earliest_later_onset,
                                 latest_later_onset)])
    
    degraded = excerpt.copy()
    
    degraded.note_df.loc[note_index, 'onset'] = onset
    
    return degraded

    


@set_random_seed
def onset_shift(excerpt, min_shift=50, max_shift=np.inf, min_duration=50,
                max_duration=np.inf):
    """
    Shift the onset time of one note from the given excerpt.

    Parameters
    ----------
    excerpt : Composition
        A Composition object of an excerpt from a piece of music.
        
    min_shift : float
        The minimum amount by which the onset time will be changed. Defaults
        to 50.
        
    max_shift : float
        The maximum amount by which the onset time will be changed. Defaults
        to infinity.
        
    min_duration : float
        The minimum duration for the resulting note. Defaults to 50.
        
    max_duration : float
        The maximum duration for the resulting note. Defaults to infinity.
        (The offset time will never go beyond the current last offset
        in the excerpt.)

    seed : int
        A seed to be supplied to np.random.seed(). Defaults to None, which
        leaves numpy's random state unchanged.

    Returns
    -------
    degraded : Composition
        A copy of the given excerpt, with the onset time of one note changed.
    """
    # Find all editable notes
    valid_notes = []
    
    # Use indices because saving the df.loc objects creates copies
    for note_index in range(excerpt.note_df.shape[0]):
        onset = excerpt.note_df.loc[note_index, 'onset']
        offset = onset + excerpt.note_df.loc[note_index, 'dur']
        
        # Lengthen bounds (decrease onset)
        earliest_lengthened_onset = max(offset - max_duration,
                                        onset - max_shift,
                                        0)
        latest_lengthened_onset = onset - min_shift
        
        # Shorten bounds (increase onset)
        earliest_shortened_onset = onset + min_shift
        latest_shortened_onset = min(offset - min_duration,
                                     onset + max_shift)
        
        # Check that sampled note is valid (can be lengthened or shortened)
        if (earliest_lengthened_onset < latest_lengthened_onset or
            earliest_shortened_onset < latest_shortened_onset):
            valid_notes.append((note_index,
                                onset,
                                offset,
                                earliest_lengthened_onset,
                                latest_lengthened_onset,
                                earliest_shortened_onset,
                                latest_shortened_onset))
            
    if len(valid_notes) == 0:
        warnings.warn('WARNING: No valid notes to onset shift. Returning ' +
                      'None.', category=UserWarning)
        return None
    
    # Sample a random note
    (note_index,
     onset,
     offset,
     earliest_lengthened_onset,
     latest_lengthened_onset,
     earliest_shortened_onset,
     latest_shortened_onset) = valid_notes[randint(len(valid_notes))]
    
    onset = split_range_sample([(earliest_lengthened_onset,
                                 latest_lengthened_onset),
                                (earliest_shortened_onset,
                                 latest_shortened_onset)])
    
    degraded = excerpt.copy()
    
    degraded.note_df.loc[note_index, 'onset'] = onset
    degraded.note_df.loc[note_index, 'dur'] = offset - onset
    
    return degraded



@set_random_seed
def offset_shift(excerpt, min_shift=50, max_shift=np.inf, min_duration=50,
                max_duration=np.inf):
    """
    Shift the offset time of one note from the given excerpt.

    Parameters
    ----------
    excerpt : Composition
        A Composition object of an excerpt from a piece of music.
        
    min_shift : float
        The minimum amount by which the offset time will be changed. Defaults
        to 50.
        
    max_shift : float
        The maximum amount by which the offset time will be changed. Defaults
        to infinity.
        
    min_duration : float
        The minimum duration for the resulting note. Defaults to 50.
        
    max_duration : float
        The maximum duration for the resulting note. Defaults to infinity.
        (The offset time will never go beyond the current last offset
        in the excerpt.)

    seed : int
        A seed to be supplied to np.random.seed(). Defaults to None, which
        leaves numpy's random state unchanged.


    Returns
    -------
    degraded : Composition
        A copy of the given excerpt, with the offset time of one note changed.
    """
    end_time = excerpt.note_df[['onset', 'dur']].sum(axis=1).max()

    # Find all editable notes
    valid_notes = []
    
    # Use indices because saving the df.loc objects creates copies
    for note_index in range(excerpt.note_df.shape[0]):
        onset = excerpt.note_df.loc[note_index, 'onset']
        duration = excerpt.note_df.loc[note_index, 'dur']
        
        # Lengthen bounds (increase duration)
        longest_lengthened_dur = min(duration + max_shift,
                                     end_time - onset,
                                     max_duration)
        shortest_lengthened_dur = max(duration + min_shift,
                                      min_duration)
        
        # Shorten bounds (decrease duration)
        longest_shortened_dur = min(duration - min_shift,
                                    max_duration)
        shortest_shortened_dur = max(duration - max_shift,
                                     min_duration)
        
        # Check that sampled note is valid (can be lengthened or shortened)
        if (shortest_lengthened_dur < longest_lengthened_dur or
            shortest_shortened_dur < longest_shortened_dur):
            valid_notes.append((note_index,
                                duration,
                                longest_lengthened_dur,
                                shortest_lengthened_dur,
                                longest_shortened_dur,
                                shortest_shortened_dur))
            
    if len(valid_notes) == 0:
        warnings.warn('WARNING: No valid notes to offset shift. Returning ' +
                      'None.', category=UserWarning)
        return None
    
    # Sample a random note
    (note_index,
     duration,
     longest_lengthened_dur,
     shortest_lengthened_dur,
     longest_shortened_dur,
     shortest_shortened_dur) = valid_notes[randint(len(valid_notes))]
    
    duration = split_range_sample([(shortest_shortened_dur,
                                    longest_shortened_dur),
                                   (shortest_lengthened_dur,
                                    longest_lengthened_dur)])
        
    degraded = excerpt.copy()
    
    degraded.note_df.loc[note_index, 'dur'] = duration
    
    return degraded



@set_random_seed
def remove_note(excerpt):
    """
    Remove one note from the given excerpt.

    Parameters
    ----------
    excerpt : Composition
        A Composition object of an excerpt from a piece of music.

    seed : int
        A seed to be supplied to np.random.seed(). Defaults to None, which
        leaves numpy's random state unchanged.


    Returns
    -------
    degraded : Composition
        A copy of the given excerpt, with one note removed.
    """
    if excerpt.note_df.shape[0] == 0:
        warnings.warn('WARNING: No notes to remove. Returning None.',
                      category=UserWarning)
        return None
        
    degraded = excerpt.copy()

    # Sample a random note
    note_index = randint(0, degraded.note_df.shape[0])

    # Remove that note
    degraded.note_df.drop(note_index, inplace=True)
    degraded.note_df.reset_index(drop=True, inplace=True)

    return degraded



@set_random_seed
def add_note(excerpt, min_pitch=MIN_PITCH, max_pitch=MAX_PITCH,
             min_duration=50, max_duration=np.inf):
    """
    Add one note to the given excerpt.

    Parameters
    ----------
    excerpt : Composition
        A Composition object of an excerpt from a piece of music.
    min_pitch : int
        The minimum pitch at which a note may be added.
    max_pitch : int
        The maximum pitch at which a note may be added.
    min_duration : float
        The minimum duration for the note to be added. Defaults to 50.
    max_duration : float
        The maximum duration for the added note. Defaults to infinity.
        (The offset time will never go beyond the current last offset
        in the excerpt.)
    seed : int
        A seed to be supplied to np.random.seed(). Defaults to None, which
        leaves numpy's random state unchanged.


    Returns
    -------
    degraded : Composition
        A copy of the given excerpt, with one note added.
    """
    degraded = excerpt.copy()

    end_time = degraded.note_df[['onset', 'dur']].sum(axis=1).max()

    pitch = randint(min_pitch, max_pitch + 1)

    if min_duration > end_time:
        onset = 0
        duration = min_duration
    else:
        onset = uniform(degraded.note_df['onset'].min(),
                        end_time - min_duration)
        duration = uniform(min_duration,
                           min(end_time - onset, max_duration))

    # Track is random one of existing tracks
    track = choice(degraded.note_df['track'].unique())

    degraded.note_df = degraded.note_df.append({'pitch': pitch,
                                                'onset': onset,
                                                'dur': duration,
                                                'track': track},
                                               ignore_index=True)
    return degraded



@set_random_seed
def split_note(excerpt, params):
    """Split a note into two notes."""
    raise NotImplementedError()



@set_random_seed
def join_notes(excerpt, params):
    """Combine two notes into one note."""
    raise NotImplementedError()



DEGRADATIONS = {
    'pitch_shift': pitch_shift,
    'time_shift': time_shift,
    'onset_shift': onset_shift,
    'offset_shift': offset_shift,
    'remove_note': remove_note,
    'add_note': add_note,
    'split_note': split_note,
    'join_notes': join_notes
}



def get_degradations(degradation_list):
    """
    A convenience function to get degradation functions from strings.

    Parameters
    ----------
    degradation_list : list of strings
        list containing the names of the degradation functions to get

    Returns
    -------
    degradations : dict(string -> func)
        A dict containing the name of each degradation mapped to a pointer to
        the method which performs that degradation.
    """
    deg_funcs = [DEGRADATIONS[deg_str] for deg_str in degradation_list]
    return deg_funcs
