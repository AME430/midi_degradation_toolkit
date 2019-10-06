#!/usr/bin/env python
"""Script to generate Altered and Corrupted Midi Exerpt (ACME) datasets"""
import os
import json
import argparse
from glob import glob
import warnings

import numpy as np
from tqdm import tqdm

from mdtk import degradations, downloaders, data_structures, midi
from mdtk.filesystem_utils import make_directory, copy_file

## For dev mode warnings...
#import sys
#if not sys.warnoptions:
#    import warnings
#    warnings.simplefilter("always") # Change the filter in this process
#    os.environ["PYTHONWARNINGS"] = "always" # Also affect subprocesses



with open('./img/logo.txt', 'r') as ff:
    LOGO = ff.read()


DESCRIPTION = "Make datasets of altered and corrupted midi exerpts."



def parse_degradation_kwargs(kwarg_dict):
    """Convenience function to parse a dictionary of keyword arguments for
    the functions within the degradations module. All keys in the kwarg_dict
    supplied should start with the function name and be followed by a double
    underscore. For example: func_name__kwarg_name. An example supplied
    dictionary:
        {
            'func1__kwarg1': 7,
            'func2__kwarg1': "hello",
            'func2__kwarg2': "world"
        }
    This results in the returned dictionary:
        {
            'func1': {'kwarg1': 7},
            'func2': {'kwarg1': "hello", 'kwarg2': "world}
        }

    Parameters
    ----------
    kwarg_dict : dict
        Dict containing keyword arguments to parse

    Returns
    -------
    func_kwargs : dict
        Dict with keys matching the names of the functions. The corresponding
        value is a dictionary of the keyword arguments for the function.
    """
    func_names = degradations.DEGRADATIONS.keys()
    func_kwargs = {name: {} for name in func_names}
    if kwarg_dict is None:
        return func_kwargs
    for kk, kwarg_value in kwarg_dict.items():
        try:
            func_name, kwarg_name = kk.split('__', 1)
        except ValueError:
            raise ValueError(f"Supplied keyword [{kk}] must have a double "
                             "underscore")
        assert func_name in func_names, f"{func_name} not in {func_names}"
        func_kwargs[func_name][kwarg_name] = kwarg_value
    return func_kwargs



def parse_args(args_input=None):
    """Convenience function for parsing user supplied command line args"""
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    default_outdir = os.path.join(os.getcwd(), 'acme')
    parser.add_argument('-o', '--output-dir', type=str, default=default_outdir,
                        help='the directory to write the dataset to (defaults '
                        f'to current working directory: {default_outdir})')
    default_indir = os.path.join(os.getcwd(), 'input_data')
    parser.add_argument('-i', '--input-dir', type=str, default=default_indir,
                        help='the directory to store the preprocessed '
                        'downloaded data to (defaults to current working '
                        f'directory: {default_indir})')
    # TODO: implement this - users could have directories containing midi they
    #       want to use in conjunction with any downloaded for them
    parser.add_argument('--local-midi-dirs', metavar='midi_dir', type=str,
                        nargs='*', help='directories containing midi files to '
                        'include in the dataset', default=[])
    # TODO: implement this - users could have csv data of their own
    parser.add_argument('--local-csv-dirs', metavar='csv_dir', type=str,
                        nargs='*', help='directories containing csv files to '
                        'include in the dataset', default=[])
    parser.add_argument('--datasets', metavar='dataset_name',
                        nargs='*', choices=downloaders.DATASETS,
                        default=downloaders.DATASETS,
                        help='datasets to download and use. Must match names '
                        'of classes in the downloaders module. By default, '
                        'will use cached downloaded data if available, see '
                        '--download-cache-dir and --clear-download-cache',
                        )
    # TODO: check this works!
    parser.add_argument('--download-cache-dir', type=str,
                        default=downloaders.DEFAULT_CACHE_PATH, help='The '
                        'directory to use for storing intermediate downloaded '
                        'data e.g. zip files, and prior to preprocessing. By '
                        f'default is set to {downloaders.DEFAULT_CACHE_PATH}')
    # TODO: check this works!
    parser.add_argument('--clear-download-cache', action='store_true',
                        help='clear downloaded data cache')
    parser.add_argument('--degradations', metavar='deg_name', nargs='*',
                        choices=list(degradations.DEGRADATIONS.keys()),
                        default=list(degradations.DEGRADATIONS.keys()),
                        help='degradations to use on the data. Must match '
                        'names of functions in the degradations module. By '
                        'default, will use them all.')
    # TODO: Check these
    parser.add_argument('--excerpt-length', metavar='ms', type=int,
                        help='The length of the excerpt (in ms) to take from '
                        'each piece. The excerpt will start on a note onset '
                        'and include all notes whose onset lies within this '
                        'number of ms after the first note.', default=5000)
    parser.add_argument('--min-notes', metavar='N', type=int, default=10,
                        help='The minimum number of notes required for an '
                        'excerpt to be valid.')
    # TODO: check this works!
    parser.add_argument('--degradation-kwargs', metavar='json_string',
                        help='json with keyword arguments for the '
                        'degradation functions. First provide the degradation '
                        'name, then a double underscore, then the keyword '
                        'argument name, followed by the value to use for the '
                        'kwarg. e.g. {"pitch_shift__distribution": "poisson", '
                        '"pitch_shift__min_pitch: 5"}',
                        type=json.loads, default=None)
    # TODO: check this works!
    parser.add_argument('--degradation-kwarg-json', metavar='json_file',
                        help='A file containing parameters as described in '
                        '--degradation-kwargs', type=json.load, default=None)
    # TODO: check this works!
    parser.add_argument('--degradation-dist', metavar='relative_probability',
                        nargs='*', default=None, help='a list of relative '
                        'probabilities that each degradation will used. Must '
                        'be the same length as --degradations')
    # TODO: Test these
    parser.add_argument('--clean-prop', type=float, help='The proportion of '
                        'excerpts in the final dataset that should be clean.',
                        default=1 / (1 + len(degradations.DEGRADATIONS)))
    parser.add_argument('--splits', metavar=('train', 'test', 'valid'),
                        nargs=3, type=float, help='The relative sizes of the '
                        'train, test, and validation sets respectively.',
                        default=[0.8, 0.1, 0.1])
    args = parser.parse_args(args=args_input)
    return args


if __name__ == '__main__':
    # TODO: set warning level such that we avoid warning fatigue
    ARGS = parse_args()
    assert (ARGS.degradation_kwargs is None or
            ARGS.degradation_kwarg_json is None), ("Don't specify both "
                "--degradation-kwargs and --degradation-kwarg-json")
    if ARGS.degradation_kwarg_json is None:
        degradation_kwargs = parse_degradation_kwargs(ARGS.degradation_kwargs)
    else:
        degradation_kwargs = parse_degradation_kwargs(
            ARGS.degradation_kwarg_json
        )
    # TODO: warn user they specified kwargs for degradation not being used
    # TODO: bomb out if degradation-dist is a diff length to degradations
    # TODO: handle csv downloading if csv data is available in downloader...
    #       then there's no need for midi conversion

    # Instantiate downloaders =================================================
    # TODO: make OVERWRITE this an arg for the script
    OVERWRITE = None
    ds_names = ARGS.datasets
    # Instantiated downloader classes
    downloader_dict = {
        ds_name: getattr(downloaders, ds_name)(
                     cache_path=ARGS.download_cache_dir
                 )
        for ds_name in ds_names
    }
    midi_input_dirs = {name: os.path.join(ARGS.input_dir, 'midi', name)
                       for name in ds_names}
    csv_input_dirs = {name: os.path.join(ARGS.input_dir, 'csv', name)
                      for name in ds_names}

    # Set up directories ======================================================
    for path in midi_input_dirs.values():
        make_directory(path)
    for path in csv_input_dirs.values():
        make_directory(path)
    for out_subdir in ['clean', 'altered']:
        output_dirs = [os.path.join(ARGS.output_dir, out_subdir, name)
                       for name in ds_names]
        for path in output_dirs:
            make_directory(path)


    # Download data ===========================================================
    for name in downloader_dict:
        downloader = downloader_dict[name]
        output_path = midi_input_dirs[name]
        downloader.download_midi(output_path=output_path,
                                 overwrite=OVERWRITE)

    # Copy over user midi =====================================================
    for path in ARGS.local_midi_dirs:
        dirname = os.path.basename(path)
        outdir = os.path.join(ARGS.input_dir, 'csv', dirname)
        for filepath in glob(os.path.join(path, '*.mid')):
            copy_file(filepath, outdir)

    # Convert from midi to csv ================================================
    for name in tqdm(midi_input_dirs, desc=f"Converting midi from "
                     f"{list(midi_input_dirs.values())} to csv at "
                     f"{list(csv_input_dirs.values())}"):
        midi.midi_dir_to_csv(midi_input_dirs[name], csv_input_dirs[name])

    # Create all Composition objects and write clean data to output ===========
    # output to output_dir/clean/dataset_name/filename.csv
    # The reason for this is we know there will be no filename duplicates
    csv_paths = glob(os.path.join(ARGS.input_dir, 'csv', '*', '*.csv'))
    read_note_csv_kwargs = dict(
        onset=0,
        pitch=2,
        dur=3,
        track=1,
        sort=False,
        header=None,
        overlap_check=False
    )
    compositions = [data_structures.Composition(
                        csv_path=csv_path,
                        read_note_csv_kwargs=read_note_csv_kwargs)
                    for csv_path in tqdm(csv_paths, desc="Cleaning csv data")]
    np.random.shuffle(compositions) # This is important for join_notes

    meta_file = open(os.path.join(ARGS.output_dir, 'metadata.csv'), 'w')

    # Perform degradations and write degraded data to output ==================
    # output to output_dir/degraded/dataset_name/filename.csv
    # The reason for this is that there could be filename duplicates (as above,
    # it's assumed there shouldn't be duplicates within each dataset!), and
    # this allows for easy matching of source and target data
    deg_choices = ARGS.degradations
    goal_dist = ARGS.degradation_dist
    if goal_dist is None:
        # Default of None implies uniform
        goal_dist = np.ones(len(deg_choices)) / len(deg_choices)

    # Remove any degs with goal_dist == 0
    non_zero = [i for i, p in enumerate(goal_dist) if p != 0]
    deg_choices = np.array(deg_choices)[non_zero]
    goal_dist = np.array(goal_dist)[non_zero]

    # Add none for no degradation
    if ARGS.clean_prop > 0:
        deg_choices = np.insert(deg_choices, 0, 'none')
        goal_dist/= 1 - ARGS.clean_prop
        goal_dist = np.insert(goal_dist, 0, ARGS.clean_prop)

    # Normalize split proportions
    split_props = np.array(ARGS.splits)
    split_props /= np.sum(split_props)

    # Write out deg_choices to labels.csv
    with open(os.path.join(ARGS.output_dir, 'labels.csv'), 'w') as file:
        for i, deg_name in enumerate(deg_choices):
            file.write(f'{i},{deg_name}\n')

    # The idea is to keep track of the current distribution of degradations
    # and then sample in reverse order of the difference between this and
    # the goal distribution.
    current_counts = np.zeros(len(deg_choices))
    num_skipped = 0

    for i, comp in enumerate(tqdm(compositions, desc="Making target data")):
        # First, get the degradation order for this iteration.
        # Get the current distribution of degradations
        if i == 0: # for first iteration, set to uniform
            current_dist = np.ones(len(goal_dist)) / len(goal_dist)
        else:
            current_dist = current_counts / np.sum(current_counts)

        # Grab an excerpt from this composition
        excerpt = None
        for iter in range(10):
            note_index = np.random.choice(list(comp.note_df.index.values)
                                          [:-ARGS.min_notes])
            note_onset = comp.note_df[note_index]['onset']
            excerpt = comp.note_df.loc[(comp.note_df['onset'] >= note_onset) &
                                       (comp.note_df['onset'] <
                                        note_onset + ARGS.excerpt_length)]

            # Check for validity of excerpt
            if len(excerpt) < ARGS.min_notes:
                excerpt = None
            else:
                break

        # If no valid excerpt was found, skip this piece
        if excerpt is None:
            warnings.warn(UserWarning, "Unable to find valid excerpt from "
                          f"composition {comp.csv_path}. Skipping.")
            num_skipped += 1
            continue

        # Initially, we will never sample if current >= goal
        # We will do so only if all degs where current < goal fail
        diffs = goal_dist - current_dist
        degs_sorted = sorted(zip(diffs, deg_choices))[::-1]

        # Make labels for no degradation
        fn = os.path.basename(comp.csv_path)
        dataset = os.path.basename(os.path.dirname(comp.csv_path))
        clean_path = os.path.join('clean', dataset, fn)
        altered_path = clean_path
        deg_binary = 0
        deg_num = 0
        # Can calculate splits in order because the comps are shuffled
        prop = (i - num_skipped) / (len(compositions) - num_skipped)
        if prop < split_props[0]:
            split = 'train'
        elif prop < split_props[0] + split_props[1]:
            split = 'test'
        else:
            split = 'valid'
        # Try to perform a degradation
        for diff, deg_name in degs_sorted:
            # Break for no degradation
            if deg_name == 'none':
                current_counts[deg_num] += 1
                break

            # Try the degradation
            deg_fun = degradations.DEGRADATIONS[deg_name]
            deg_fun_kwargs = degradation_kwargs[deg_name] # degradation_kwargs
                                                          # at top of main call
            degraded = deg_fun(comp.note_df, **deg_fun_kwargs)

            if degraded is not None:
                # Write clean csv
                clean_path = os.path.join('clean', dataset, fn)
                clean_outpath = os.path.join(ARGS.output_dir, clean_path)
                excerpt.to_csv(clean_outpath)
                # Write degraded csv
                altered_path = os.path.join('altered', dataset, fn)
                altered_outpath = os.path.join(ARGS.output_dir, altered_path)
                degraded.to_csv(altered_outpath)
                # Update labels
                deg_binary = 1
                deg_num = np.where(deg_choices == deg_name)[0][0]
                current_counts[deg_num] += 1
                break

        # Write meta
        if degraded is not None or ARGS.clean_prop > 0:
            meta_file.write(f'{altered_outpath},{deg_binary},{deg_num},'
                            f'{clean_outpath},{split}\n')
        else:
            warnings.warn(UserWarning, "Unable to degrade chose excerpt from "
                          f"{comp.csv_path} and no clean excerpts wanted. "
                          "Skipping.")
            num_skipped += 1

    meta_file.close()

    print('Finished!')
    print(f'Count of degradations {deg_choices} = {current_counts}')
    print(f'You will find the generated dataset at {ARGS.output_dir}')
    print('The clean and altered files are located under directories named as '
          'such.')
    print('The (integer) labels and splits for each excerpt are located in '
          'metadata.csv')
    print('The labels are defined in labels.csv')

    print(LOGO)
