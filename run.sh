#!/bin/bash
docker run --rm -p 8050:8050 -v $PWD:/code --name dashly-server dash-images python app.py
exit 0


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



