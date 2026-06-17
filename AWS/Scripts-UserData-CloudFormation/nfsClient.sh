#!/bin/bash

#  Instalando NFS no Cliente

sudo apt-get -y update

sudo apt-get -y install nfs-common

#   Montando a pasta no Cliente

sudo mkdir -p /home

sudo mount $ipS:/home /home

#  verificando montagem da pasta

df -h
