import os
import random

import numpy as np

import config
from spectrogram_dicts import build_class_dictionaries

np.random.seed(15)  # for reproducibility


"""
There exists a large data imbalance between positive and negative samples,
which incurs a large bias in classification. The number of non-depressed
subjects is about four times bigger than that of depressed ones. If these
samples for learning, the model will have a strong bias to the non-depressed
class. Moreover, regarding the length of each sample, a much longer signal of
an individual may emphasize some characteristics that are person specific.
To solve the problem, I perform random cropping on each of the participant's
spectrograms of a specified width (time) and constant height (frequency), to
ensure the CNN has an equal proportion for every subject and each class. The
size of the Hanning window is 1024, and the audio sample rate is 16000 Hz,
which leads to a covering domain of 1024/16000 Hz=0.064s; accordingly, the
hop size is 32ms, half of the analysis window. Meaning each pixel of width
represents 32ms. Some success has been found using random crops of 3-5
seconds [1]. I'll start with 4 seconds and tune it like a hyperparameter.
A width of 4 seconds means 4/0.032 = 125 pixel window size.
[1] DeepAudioNet: An Efficient Deep Model for Audio based
Depression Classification.
"""


def determine_num_crops(depressed_dict, normal_dict, crop_width=125):
    """
    Finds the shortest clip in the entire dataset which, according to our
    random sampling strategy, will limit the number of samples we take from
    each clip to make sure our classes are balanced.

    Parameters
    ----------
    depressed_dict : dictionary
        a dictionary of depressed participants with the participant id as the
        key and the segmented and concatenated matrix representation of
        their spectrograms as the values.
    crop_width : integer
        the desired pixel width of the crop samples
        (125 pixels = 4 seconds of audio)

    Returns
    -------
    num_samples_from_clips : int
        the maximum number of samples that should be sampled from each clip
        to ensure balanced classes can be built.
    """
    merged_dict = {**normal_dict, **depressed_dict}
    shortest_clip = min(merged_dict.items(), key=lambda x: x[1].shape[1])
    shortest_pixel_width = shortest_clip[1].shape[1]
    num_samples_from_clips = shortest_pixel_width // crop_width
    return num_samples_from_clips


def build_class_sample_dict(segmented_audio_dict, n_samples, crop_width):
    """
    Get N (num_samples) pseudo random non-overlapping samples from the all
    the depressed participants.

    Parameters
    ----------
    segmented_audio_dict : dictionary
        a dictionary of a class of participants with keys of participant ids
        and values of the segmented audio matrix spectrogram representation
    n_samples : integer
        number of random non-overlapping samples to extract from each
        segmented audio matrix spectrogram
    crop_width : integer
        the desired pixel width of the crop samples
        (125 pixels = 4 seconds of audio)

    Returns
    -------
    class sample dict : dictionary
        a dictionary of a class of participants with keys of participant ids
        and values of a list of the cropped samples from the spectrogram
        matrices. The lists are n_samples long and the entries within the
        list have dimension (numFrequencyBins * crop_width)
    """
    class_samples_dict = dict()
    for partic_id, clip_mat in segmented_audio_dict.items():
        samples = get_random_samples(clip_mat, n_samples, crop_width)
        class_samples_dict[partic_id] = samples
    return class_samples_dict


def get_random_samples(matrix, n_samples, crop_width):
    """
    Get N random samples with width of crop_width from the numpy matrix
    representing the participant's audio spectrogram.
    """
    # crop full spectrogram into segments of width = crop_width
    clipped_mat = matrix[:, (matrix.shape[1] % crop_width) :]
    n_splits = clipped_mat.shape[1] / crop_width
    cropped_sample_ls = np.split(clipped_mat, n_splits, axis=1)

    # get random samples
    samples = random.sample(cropped_sample_ls, n_samples)
    return samples


def create_sample_dicts(crop_width):
    """
    Utilizes the above function to return two dictionaries, depressed
    and normal. Each dictionary has only participants in the specific class,
    with participant ids as key, a values of a list of the cropped samples
    from the spectrogram matrices. The lists are vary in length depending
    on the length of the interview clip. The entries within the list are
    numpy arrays with dimennsion (513, 125).
    """
    # build dictionaries of participants and segmented audio matrix
    depressed_dict, normal_dict = build_class_dictionaries(
        os.path.join(config.BASE_DIR, "data", "interim")
    )
    n_samples = determine_num_crops(depressed_dict, normal_dict, crop_width=crop_width)
    # get n_sample random samples from each depressed participant
    depressed_samples = build_class_sample_dict(depressed_dict, n_samples, crop_width)
    # get n_sample random samples from each non-depressed participant
    normal_samples = build_class_sample_dict(normal_dict, n_samples, crop_width)
    # iterate through samples dictionaries and save a npz file
    # with the radomly sleected n_samples for each participant.
    # save arrays to .npz
    path = os.path.join(config.BASE_DIR, "data", "processed")
    for key, values in depressed_samples.items():
        np.savez(os.path.join(path, f"D{key}.npz"), *values)
    for key, values in normal_samples.items():
        np.savez(os.path.join(path, f"N{key}.npz"), *values)


def rand_samp_train_test_split(npz_file_dir):
    """
    Given the cropped segments from each class and particpant, this fucntion
    determines how many samples we can draw from each particpant and how many
    participants we can draw from each class.

    Parameters
    ----------
    npz_file_dir : directory
        directory contain the
    crop_width : integer
        the desired pixel width of the crop samples
        (125 pixels = 4 seconds of audio)

    Returns
    -------
    num_samples_from_clips : int
        the maximum number of samples that should be sampled from each clip
        to ensure balanced classes can be built.
    """
    # files in directory
    npz_files = os.listdir(npz_file_dir)

    dep_samps = [f for f in npz_files if f.startswith("D")]
    norm_samps = [f for f in npz_files if f.startswith("N")]
    # calculate how many samples to balance classes
    max_samples = min(len(dep_samps), len(norm_samps))

    # randomly select max participants from each class without replacement
    dep_select_samps = np.random.choice(dep_samps, size=max_samples, replace=False)
    norm_select_samps = np.random.choice(norm_samps, size=max_samples, replace=False)

    # randomly select n_samples_per_person (40 in the case of a crop width
    # of 125) from each of the participant lists

    # REFACTOR this code!
    test_size = 0.2
    num_test_samples = int(len(dep_select_samps) * test_size)

    train_samples = []
    for sample in dep_select_samps[:-num_test_samples]:
        npz_file = npz_file_dir + "/" + sample
        with np.load(npz_file) as data:
            for key in data.keys():
                train_samples.append(data[key])
    for sample in norm_select_samps[:-num_test_samples]:
        npz_file = npz_file_dir + "/" + sample
        with np.load(npz_file) as data:
            for key in data.keys():
                train_samples.append(data[key])
    train_labels = np.concatenate(
        (np.ones(len(train_samples) // 2), np.zeros(len(train_samples) // 2))
    ).astype(int)

    test_samples = []
    for sample in dep_select_samps[-num_test_samples:]:
        npz_file = npz_file_dir + "/" + sample
        with np.load(npz_file) as data:
            for key in data.keys():
                test_samples.append(data[key])
    for sample in norm_select_samps[-num_test_samples:]:
        npz_file = npz_file_dir + "/" + sample
        with np.load(npz_file) as data:
            for key in data.keys():
                test_samples.append(data[key])
    test_labels = np.concatenate(
        (np.ones(len(test_samples) // 2), np.zeros(len(test_samples) // 2))
    ).astype(int)

    return np.array(train_samples), train_labels, np.array(test_samples), test_labels


if __name__ == "__main__":
    # build participant's cropped npz files
    # this is of the whole no_silence particpant's no_silence interview,
    # but each array in the npz files was width of crop_width
    create_sample_dicts(crop_width=125)

    # random sample from particpants npz files to ensure class balance
    train_samples, train_labels, test_samples, test_labels = rand_samp_train_test_split(
        os.path.join(config.BASE_DIR, "data", "processed")
    )

    # save as npz locally
    print("Saving npz file locally...")
    np.savez(
        os.path.join(config.BASE_DIR, "data", "processed", "train_samples.npz"),
        train_samples,
    )
    np.savez(
        os.path.join(config.BASE_DIR, "data", "processed", "train_labels.npz"),
        train_labels,
    )
    np.savez(
        os.path.join(config.BASE_DIR, "data", "processed", "test_samples.npz"),
        test_samples,
    )
    np.savez(
        os.path.join(config.BASE_DIR, "data", "processed", "test_labels.npz"),
        test_labels,
    )
