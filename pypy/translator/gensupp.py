"""
Some support for genxxx implementations of source generators.
Another name could be genEric, but well...
"""

from __future__ import generators

import sys

from pypy.objspace.flow.model import Block
from pypy.objspace.flow.model import traverse

# ordering the blocks of a graph by source position

def ordered_blocks(graph):
    # collect all blocks
    allblocks = []
    def visit(block):
        if isinstance(block, Block):
            # first we order by offset in the code string
            if block.operations:
                ofs = block.operations[0].offset
            else:
                ofs = sys.maxint
            # then we order by input variable name or value
            if block.inputargs:
                txt = str(block.inputargs[0])
            else:
                txt = "dummy"
            allblocks.append((ofs, txt, block))
    traverse(visit, graph)
    allblocks.sort()
    #for ofs, txt, block in allblocks:
    #    print ofs, txt, block
    return [block for ofs, txt, block in allblocks]

# a unique list, similar to a list.
# append1 appends an object only if it is not there,already.

class UniqueList(list):
    def __init__(self, *args, **kwds):
        list.__init__(self, *args, **kwds)
        self.dic = {}

    def append1(self, arg):
        try:
            self.dic[arg]
        except KeyError:
            self.dic[arg] = 1
            list.append(self, arg)
        except TypeError: # not hashable
            if arg not in self:
                list.append(self, arg)

def builtin_base(obj):
    typ = type(obj)
    while typ.__module__ != '__builtin__':
        typ = typ.__base__
    return typ

def c_string(s):
    return '"%s"' % (s.replace('\\', '\\\\').replace('"', '\"'),)

def uniquemodulename(name, SEEN={}):
    # never reuse the same module name within a Python session!
    i = 0
    while True:
        i += 1
        result = '%s_%d' % (name, i)
        if result not in SEEN:
            SEEN[result] = True
            return result

# a translation table suitable for str.translate() to remove
# non-C characters from an identifier
C_IDENTIFIER = ''.join([(('0' <= chr(i) <= '9' or
                          'a' <= chr(i) <= 'z' or
                          'A' <= chr(i) <= 'Z') and chr(i) or '_')
                        for i in range(256)])

# a name manager knows about all global and local names in the
# program and keeps them disjoint. It provides ways to generate
# shorter local names with and without wrapping prefixes,
# while always keeping all globals visible.

class NameManager(object):
    def __init__(self):
        self.seennames = {}
        self.scope = 0
        self.scopelist = []

    def make_reserved_names(self, txt):
        """add names to list of known names. If one exists already,
        then we raise an exception. This function should be called
        before generating any new names."""
        for name in txt.split():
            if name in self.seennames:
                raise NameError, "%s has already been seen!"
            self.seennames[name] = 1

    def uniquename(self, basename):
        basename = basename.translate(C_IDENTIFIER)
        n = self.seennames.get(basename, 0)
        self.seennames[basename] = n+1
        if basename in ('v', 'w_'):
            if n == 0:
                return '%s%d' % (basename, n)
            else:
                return self.uniquename('%s%d' % (basename, n))
        if n == 0:
            return basename
        else:
            return self.uniquename('%s_%d' % (basename, n))

    def localScope(self, parent=None):
        ret = _LocalScope(self, parent)
        while ret.scope >= len(self.scopelist):
            self.scopelist.append({})
        return ret

class _LocalScope(object):
    """track local names without hiding globals or nested locals"""
    def __init__(self, glob, parent):
        self.glob = glob
        if not parent:
            parent = glob
        self.parent = parent
        self.mapping = {}
        self.usednames = {}
        self.scope = parent.scope + 1

    def uniquename(self, basename):
        basename = basename.translate(C_IDENTIFIER)
        glob = self.glob
        p = self.usednames.get(basename, 0)
        self.usednames[basename] = p+1
        namesbyscope = glob.scopelist[self.scope]
        namelist = namesbyscope.setdefault(basename, [])
        if p == len(namelist):
            namelist.append(glob.uniquename(basename))
        return namelist[p]

    def localname(self, name, wrapped=False):
        """modify and mangle local names"""
        if name in self.mapping:
            return self.mapping[name]
        scorepos = name.rfind("_")
        if name.startswith("v") and name[1:].isdigit():
            basename = ('v', 'w_') [wrapped]
        elif scorepos >= 0 and name[scorepos+1:].isdigit():
            basename = name[:scorepos]
            if wrapped:
                basename = "w_" + basename
            else:
                basename = "l_" + basename
        else:
            basename = name
        ret = self.uniquename(basename)
        self.mapping[name] = ret
        return ret

