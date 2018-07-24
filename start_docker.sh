#!/bin/bash
CURDIR=`pwd`/$(dirname $0)
docker rm -f rstweb
docker run -d -p 8085:80 --name rstweb -v $CURDIR:/var/www/html/rstweb rstweb