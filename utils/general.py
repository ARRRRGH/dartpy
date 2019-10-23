import collections
import six
import os
from lxml import etree as et


def merge_dicts(src_dict, patch_dict, ignore=None):
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

    if ignore is None:
        ignore = []

    for k, v in six.iteritems(patch_dict):
        if v in ignore:
            continue

        dv = src_dict.get(k, {})
        if not isinstance(dv, collectionsAbc.Mapping):
            src_dict[k] = v
        elif isinstance(v, collectionsAbc.Mapping):
            src_dict[k] = merge_dicts(dv, v)
        else:
            src_dict[k] = v
    return src_dict


class XMLCombiner(object):
    def __init__(self, filenames):
        assert len(filenames) > 0, 'No filenames!'
        # save all the roots, in order, to be processed later
        self.roots = [et.parse(f).getroot() for f in filenames]

    def combine(self):
        for r in self.roots[1:]:
            # combine each element with the first one, and update that
            self.combine_element(self.roots[0], r)
        # return the string representation
        return et.tostring(self.roots[0])

    @classmethod
    def combine_element(cls, one, other):
        """
        This function recursively updates either the text or the children
        of an element if another element is found in `one`, or adds it
        from `other` if not found.
        """
        # Create a mapping from tag name to element, as that's what we are fltering with
        mapping = {el.tag: el for el in one}
        for el in other:
            if len(el) == 0:
                # Not nested
                try:
                    # Update the text
                    mapping[el.tag].text = el.text
                except KeyError:
                    # An element with this name is not in the mapping
                    mapping[el.tag] = el
                    # Add it
                    one.append(el)
            else:
                try:
                    # Recursively process the element, and update it in the same way
                    cls.combine_element(mapping[el.tag], el)
                except KeyError:
                    # Not in the mapping
                    mapping[el.tag] = el
                    # Just add it
                    one.append(el)


def merge_xmls(src_xml, patch_xml):
    return XMLCombiner.combine_element(src_xml, patch_xml)


def create_path(*args):
    return os.path.normpath(os.path.join(*args)).replace('\\', '/')


class ObjectWrapper(object):
    def __init__(self, obj):
        self._wrapped_obj = obj

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return getattr(self, attr)
        return getattr(self._wrapped_obj, attr)

