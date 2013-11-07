#!/bin/bash

cd `dirname $0`

mkdir -p tmp
cd tmp

if [[ "`uname -m`" == "x86_64" ]]; then
    libdir="lib64"
else
    libdir="lib"
fi

echo $libdir
wget https://re2.googlecode.com/files/re2-20131024.tgz -O re2.tgz && tar zxvf re2.tgz && cd re2 && make && sudo make install && \
sudo ln -sf /usr/local/lib/libre2.so /${libdir}/libre2.so && \
sudo ln -sf /usr/local/lib/libre2.so.0 /${libdir}/libre2.so.0
