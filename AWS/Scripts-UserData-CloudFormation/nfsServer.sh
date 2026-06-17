#!/bin/bash
#ipC1_private=`curl -s http://169.254.169.254/latest/meta-data/local-ipv4`
#ipS_private=`curl -s http://169.254.169.254/latest/meta-data/local-ipv4`

IpSub=`curl -s http://169.254.169.254/latest/meta-data/local-ipv4`

echo $IpSub > ip.txt

export typeset ipSub=$(cat ip.txt | cut -d"." -f3)

if [ $ipSub -le 15 ];
then
        IP=172.31.0.0/20
        echo $IP
elif ([ $ipSub -ge 16  ]) && ([ $ipSub -le 31 ]);
then
        IP=172.31.16.0/20
        echo $IP
elif ([ $ipSub -ge 32  ]) && ([ $ipSub -le 47 ]);
then
        IP=172.31.32.0/20
        echo $IP
elif ([ $ipSub -ge 48  ]) && ([ $ipSub -le 63 ]);
then
        IP=172.31.48.0/20
        echo $IP
elif ([ $ipSub -ge 64  ]) && ([ $ipSub -le 79 ]);
then
        IP=172.31.64.0/20
        echo $IP
elif [ $ipSub -ge 80  ];
then
        IP=172.31.80.0/20
        echo $IP
fi
rm -rf ip.txt


#   Instalando NFS no Servidor

sudo apt-get -y update

sudo apt-get -y install nfs-kernel-server

#   Configurando a exportação do NFS no Servidor

chmod 777 /etc/exports

echo /home       $IP'(rw,sync,no_root_squash,no_subtree_check)' >> /etc/exports
#echo /home       $ipC2'(rw,sync,no_root_squash,no_subtree_check)' >> /etc/exports

chmod 644 /etc/exports
systemctl restart nfs-kernel-server
