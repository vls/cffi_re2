#!/usr/bin/env python

import cffi_re2

def test_match_basic():
    robj = cffi_re2.compile('b+')
    flag = robj.search('abbcd')
    assert flag

def test_match_chinese():
    robj = cffi_re2.compile('梦[^一-龥]*幻[^一-龥]*西[^一-龥]*游')

    assert robj.search('梦1幻2西3游')
    assert not robj.search('梦倩女幻幽魂西2游')

def test_sub_basic():
    robj = cffi_re2.compile('b+')

    assert robj.sub('', 'abbcbbd') == 'acd'

def test_sub_chinese():
    robj = cffi_re2.compile('梦[^一-龥]*幻[^一-龥]*西[^一-龥]*游')

    assert robj.sub('倩女', '梦幻西游好玩吗?') == '倩女好玩吗?'

