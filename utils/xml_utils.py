import collections
from lxml import etree as et
from utils.general import merge_dicts

def merge_xmls(src_xml, patch_xml, remove_empty_paths=False, removing_level=3):
    src = etree_to_dict(src_xml)
    patch = etree_to_dict(patch_xml)
    patched = merge_dicts(src, patch, ignore=[None])
    patched_xml = dict_to_etree(patched)

    if remove_empty_paths:
        tree = et.ElementTree(patched_xml)
        empty = patched_xml.xpath(".//*[not(node())]")

        ok_empty = set()
        while len(empty) != 0:
            for element in empty:
                path = tree.getpath(element).split('/')[1:]

                if len(element.attrib) == 0 and len(path) > removing_level:
                    element.getparent().remove(element)
                else:
                    ok_empty.add(element)
            empty = set(patched_xml.xpath(".//*[not(node())]")).difference(ok_empty)

    return patched_xml


def etree_to_dict(t):
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = collections.defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {t.tag: {k: v[0] if len(v) == 1 else v
                     for k, v in dd.items()}}
    if t.attrib:
        d[t.tag].update(('@' + k, v)
                        for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d


def dict_to_etree(d):
    def _to_etree(d, root):
        if root is None:
            return
        if not d:
            pass
        elif isinstance(d, str):
            root.text = d
        elif isinstance(d, dict):
            for k, v in d.items():
                assert isinstance(k, str)
                if k.startswith('#'):
                    assert k == '#text' and isinstance(v, str)
                    root.text = v
                elif k.startswith('@'):
                    assert isinstance(v, str)
                    root.set(k[1:], v)
                elif isinstance(v, list):
                    for e in v:
                        _to_etree(e, et.SubElement(root, k))
                else:
                    _to_etree(v, et.SubElement(root, k))
        else:
            assert d == 'invalid type', (type(d), d)
    assert isinstance(d, dict) and len(d) == 1
    tag, body = next(iter(d.items()))
    node = et.Element(tag)
    _to_etree(body, node)
    return node