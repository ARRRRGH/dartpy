import collections
import six


def merge_dicts(src_dict, patch_dict, add=False):
    """
    Merge nested directory by overriding src_dict values with patch_dict values. If add=True keys
    can be added to src_dict.

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

    for k, v in six.iteritems(patch_dict):
        dv = src_dict.get(k, {})
        if not isinstance(dv, collectionsAbc.Mapping):
            src_dict[k] = v
        elif isinstance(v, collectionsAbc.Mapping):
            src_dict[k] = merge_dicts(dv, v)
        else:
            src_dict[k] = v
    return src_dict


class ObjectWrapper(object):
    def __init__(self, obj):
        self._wrapped_obj = obj
    def __getattr__(self, attr):
        if attr in self.__dict__:
            return getattr(self, attr)
        return getattr(self._wrapped_obj, attr)


def NoneDict(ObjectWrapper):
    def __getitem__(self, key):
        if key not in self._wrapped_obj.keys():
            return self