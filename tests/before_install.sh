#!/bin/bash

cd `dirname $0`

mkdir -p tmp
cd tmp

echo $libdir
wget https://re2.googlecode.com/files/re2-20131024.tgz -O re2.tgz && tar zxvf re2.tgz && cd re2 && make && sudo make install
