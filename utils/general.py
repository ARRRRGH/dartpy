import collections
import os

import six


def create_path(*args):
    return os.path.normpath(os.path.join(*args)).replace('\\', '/')


def merge_dicts(src_dict, patch_dict, ignore=None):
    """
    Merge nested directory by overriding src_dict values with patch_dict values.

    :param ignore:
    :param add:
    :param src_dict:
    :param patch_dict:
    :return:
    """
    # python 3.8+ compatibility
    try:
        collectionsAbc = collections.abc
    except:
        collectionsAbc = collections

    if ignore is None:
        ignore = []

    for k, v in six.iteritems(patch_dict):
        if v in ignore:
            continue

        dv = src_dict.get(k, {})
        if not isinstance(dv, collectionsAbc.Mapping):
            src_dict[k] = v
        elif isinstance(v, collectionsAbc.Mapping):
            src_dict[k] = merge_dicts(dv, v, ignore=ignore)
        else:
            src_dict[k] = v
    return src_dict