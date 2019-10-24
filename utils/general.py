import collections
import six
import os
from lxml import etree as et
import xmltodict

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


def merge_xmls(src_xml, patch_xml):
    src = xmltodict.parse(et.tostring(src_xml,  method='xml', encoding='utf-8'))
    patch = xmltodict.parse(et.tostring(patch_xml, method='xml', encoding='utf-8'))
    patched = merge_dicts(src, patch)
    return et.fromstring(xmltodict.unparse(patched, pretty=True).encode('utf-8'), parser=et.XMLParser(encoding='utf-8'))


def create_path(*args):
    return os.path.normpath(os.path.join(*args)).replace('\\', '/')


class ObjectWrapper(object):
    def __init__(self, obj):
        self._wrapped_obj = obj

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return getattr(self, attr)
        return getattr(self._wrapped_obj, attr)

