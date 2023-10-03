#!/bin/bash
docker run -it --rm --net=host  -v $PWD:/code --name dashly-server dash-images.3.10 python app.py
# docker run -it --rm --net=host  -v $PWD:/code --name dashly-server dash-images python app.py
exit 0
docker run --rm --net=host  -v $PWD:/code --name dashly-server dash-images python app.py
-p 9955:9955/udp

docker container stop dashly-server
docker container prune
# create a new image
docker build ./ -t dash-images
docker save -o dash-images.tar dash-images
or
docker save dash-images | gzip > dash-images.tgz

#install image to filesystem
docker load -i dash-images.tar
or
gunzip -c mycontainer.tgz | docker load



