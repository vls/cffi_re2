#!/usr/bin/env python
#encoding=utf-8
"""
This module runs the performance tests to compare the ``re`` module with the
``re2`` module. You can just run it from the command line, assuming you have re2
installed, and it will output a table in ReST format comparing everything.

To add a test, you can add a function to the bottom of this page that uses the
@register_test() decorator. Alternatively, you can create a module that uses it and
import it.
"""
from timeit import Timer
import sys

import re

try:
    import subprocess_re2
except ImportError:
    subprocess_re2 = None

try:
    import re2
except ImportError:
    re2 = None

try:
    import ctypes_re2
except ImportError:
    ctypes_re2 = None

try:
    import cffi_re2
    pass
except ImportError:
    cffi_re2 = None

import os
import gzip

os.chdir(os.path.dirname(__file__) or '.')

tests = {}

MODULE_NAME_LIST = ['subprocess_re2', 'ctypes_re2', 'cffi_re2', 're2']

_locals = locals()
MODULE_LIST = filter(None, [_locals.get(mname) for mname in MODULE_NAME_LIST])

MODULE_LIST.insert(0, re)

setup_code = """\
import re
from __main__ import tests, current_re
test = tests[%r]
"""

for mod in MODULE_LIST:
    setup_code += 'import %s\n' % (mod.__name__)

current_re = [None]


def force_unicode(s, encoding='utf-8'):
    return unicode(s, encoding)

def main():
    benchmarks = {}
    # Run all of the performance comparisons.
    print tests

    modules = MODULE_LIST
    for testname, method in tests.iteritems():
        benchmarks[testname] = {}
        results = [None for module in modules]
        for i, module in enumerate(modules):
            print 'module', module
            # We pre-compile the pattern, because that's
            # what people do.
            current_re[0] = module.compile(method.pattern)

            results[i] = method(current_re[0], **method.data)

            # Run a test.
            t = Timer("test(current_re[0],**test.data)",
                      setup_code % testname)
            benchmarks[testname][module.__name__] = (t.timeit(method.num_runs),
                                                     method.__doc__.strip(),
                                                     method.pattern,
                                                     method.num_runs)

        for i in xrange(len(results)):
            print >> sys.stderr, 'result', modules[i], results[i]

        for i in range(len(results) - 1):
            if results[i] != results[i + 1]:
                print >> sys.stderr, modules[i], results[i]
                print >> sys.stderr, modules[i+1], results[i+1]
                #raise ValueError("re2 output is not the same as re output: %s" % testname)
                print >> sys.stderr, "re2 output is not the same as re output: %s" % testname

    txt = benchmarks_to_ReST(benchmarks, modules)

    from docutils.core import publish_string
    print publish_string(txt, writer_name='html')
    print txt


def benchmarks_to_ReST(benchmarks, modules):
    """
    Convert dictionary to a nice table for ReST.
    """
    headers = ['Test', '# total runs', '``re`` time(s)', ]
    for mod in modules:
        mname = mod.__name__
        if mname != 're':
            headers.extend(['``%s`` time(s)' % (mname), '% ``re`` time'])
    table = [headers]
    f = lambda x: "%0.3f" % x
    p = lambda x: "%0.2f%%" % (x * 100)

    for test, data in benchmarks.items():
        row = [test, str(data["re"][3]), f(data["re"][0])]
        
        for mod in modules:
            mname = mod.__name__
            if mname != 're':
                row.append(f(data[mname][0]))
                row.append(p(data[mname][0] / data["re"][0]))
        table.append(row)
    col_sizes = [0] * len(table[0])
    for col in range(len(table[0])):
        col_sizes[col] = max(len(row[col]) for row in table)

    def get_divider(symbol='-'):
        s = '+' + '+'.join(symbol*col_size for col_size in col_sizes) + '+'
        return s
    def get_row(row):
        s = '|' + '|'.join(item.ljust(col_sizes[i]) for i, item in enumerate(row)) + '|'
        return s

    sarr = []
    sarr.append(get_divider())
    sarr.append(get_row(table[0]))
    sarr.append(get_divider('='))
    for row in table[1:]:
        sarr.append(get_row(row))
        sarr.append(get_divider())


    return '\n'.join(sarr)



###############################################
# Tests for performance
###############################################


# Convenient decorator for registering a new test.
def register_test(name, pattern, num_runs = 100, **data):
    def decorator(method):
        tests[name] = method
        method.pattern = pattern
        method.num_runs = num_runs
        method.data = data

        return method
    return decorator


# This is the only function to get data right now,
# but I could imagine other functions as well.
_wikidata = None
def getwikidata():
    _wikidata = open('testdata/small.wiki_dump.xml')
    return _wikidata

def getwikidata_big():
    _wikidata = open('testdata/wiki_dump.xml')
    return _wikidata
    



@register_test("Findall URI|Email",
              r'([a-zA-Z][a-zA-Z0-9]*)://([^ /]+)(/[^ ]*)?|([^ @]+)@([^ @]+)',
              3,
              dataf=getwikidata)
def findall_uriemail(pattern, dataf):
    """
    Find list of '([a-zA-Z][a-zA-Z0-9]*)://([^ /]+)(/[^ ]*)?|([^ @]+)@([^ @]+)'
    """
    count = 0
    for line in dataf():
        m = pattern.search(line)
        if m:
            count += 1

    return count

TEST_RE = re.compile('test')

@register_test("Chinese",
            #ur'梦[^一-龥]{0,4}幻[^一-龥]{0,4}西[^一-龥]{0,4}游',
            ur'梦[^一-龥]*幻[^一-龥]*西[^一-龥]*游',
            3,
            dataf=getwikidata)
def findall_chinese(pattern, dataf):
    """
    Find chinese match
    """
    flag_re = isinstance(pattern, TEST_RE.__class__)
    count = 0
    data = dataf()
    for line in data:
        if flag_re:
            line = force_unicode(line)
        m = pattern.search(line)
        if m:
            count += 1

    if hasattr(data, 'close'):
        data.close()

    return count




@register_test("Replace WikiLinks",
              r'(\[\[.*?\]\])',
              dataf=getwikidata)
def replace_wikilinks(pattern, dataf):
    """
    This test replaces links of the form [[Obama|Barack_Obama]] to Obama.
    """
    return len(pattern.sub(r'\1', dataf().read()))



@register_test("Remove WikiLinks",
              r'(\[\[.*?\]\])',
              dataf=getwikidata)
def remove_wikilinks(pattern, dataf):
    """
    This test replaces links of the form [[Obama|Barack_Obama]] to the empty string
    """
    return len(pattern.sub(r'', dataf().read()))





#register_test("Remove WikiLinks",
#              r'(<page[^>]*>)',
#              data=getwikidata())
def split_pages(pattern, data):
    """
    This test splits the data by the <page> tag.
    """
    return len(pattern.split(data))


def getweblogdata():
    return open(os.path.join(os.path.dirname(__file__), 'access.log'))

#@register_test("weblog scan",
               #r'^(\S+) (\S+) (\S+) \[(\d{1,2})/(\w{3})/(\d{4}):(\d{2}):(\d{2}):(\d{2}) -(\d{4})\] "(\S+) (\S+) (\S+)" (\d+) (\d+|-) "([^"]+)" "([^"]+)"\n',
#               '(\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) ? (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (".*?"|-) (\S+) (\S+) (\S+) (\S+)',
#               '(\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) ? (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+)',
#               data=getweblogdata())
def weblog_matches(pattern, data):
    """
    Match weblog data line by line.
    """
    total=0
    for line in data.read()[:20000].splitlines():
        p = pattern.search(line)
        #for p in pattern.finditer(data.read()[:20000]):
        if p:
            total += len(p.groups())
    data.seek(0)

    return 0

if __name__ == '__main__':
    main()
