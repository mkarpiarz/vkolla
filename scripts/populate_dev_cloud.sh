#!/bin/bash
# A script for populating dev environment with basic cloud resources.
# NOTE: Only run this from a kolla-deploy container.
set -e # exit on error

source /etc/kolla/admin-openrc.sh
set -x
IMAGE_LOC=~/cirros-x86_64-disk.img
if [ ! -f $IMAGE_LOC ]
then
    wget http://download.cirros-cloud.net/0.3.5/cirros-0.3.5-x86_64-disk.img -O $IMAGE_LOC
fi
openstack image create --container-format bare --disk-format raw --public --file $IMAGE_LOC CirrOS
openstack keypair create --public-key ~/.ssh/id_rsa.pub mykey
openstack flavor create --public m1.tiny --id 099 --ram 512 --disk 1 --vcpus 1 --rxtx-factor 1
openstack security group create ssh-and-ping
openstack security group rule create --proto icmp ssh-and-ping
openstack security group rule create --proto tcp --dst-port 22 ssh-and-ping
openstack network create --provider-network-type flat --provider-physical-network physnet1 --external external
openstack subnet create --no-dhcp --allocation-pool start=172.18.0.100,end=172.18.0.200 --network external --subnet-range 172.18.0.0/24 public
openstack network create internal
openstack subnet create --subnet-range 192.168.100.0/24 --network internal --dns-nameserver 8.8.8.8 private
openstack router create router1
openstack router set --external-gateway external router1
openstack router add subnet router1 private
