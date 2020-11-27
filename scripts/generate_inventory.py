#!/usr/bin/env python
import os
import sys
from collections import defaultdict
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient import client as keystone_client
from novaclient import client as nova_client


class Credentials:
    def __init__(self):
        self.auth_url = os.environ['OS_AUTH_URL']
        self.username = os.environ['OS_USERNAME']
        self.password = os.environ['OS_PASSWORD']
        self.project_name = os.environ['OS_PROJECT_NAME']
        self.user_domain_id = 'default'
        self.project_domain_id = 'default'
        self.client = self.get_client()

    def get_client(self):
        auth = v3.Password(auth_url=self.auth_url,
                           username=self.username,
                           password=self.password,
                           project_name=self.project_name,
                           user_domain_id=self.user_domain_id,
                           project_domain_id=self.project_domain_id)
        sess = session.Session(auth=auth)
        return keystone_client.Client(version=3, session=sess)

    def get_session(self):
        if self.client:
            return self.client.session


class Servers(object):
    def __init__(self, creds):
        # OS_ENDPOINT_TYPE can have the same values as OS_INTERFACE,
        # i.e. public (default), internal, admin
        endpoint_type = os.environ.get('OS_ENDPOINT_TYPE')
        self.client = nova_client.Client(version=2,
                                         session=creds.get_session(),
                                         endpoint_type=endpoint_type)

    def get_servers(self):
        return self.client.servers.list(detailed=True)


def main(argv):
    if len(argv) < 2:
        sys.stderr.write('Usage: ' + sys.argv[0] + ' <output>\n')
        sys.stderr.write('<output> - file to write inventory to\n')
        return 1
    inv_filename = argv[1]

    creds = Credentials()
    servers = Servers(creds)
    networks = defaultdict(int)
    # host groupings
    groupings = defaultdict(list)
    # servers with floating IPs
    floaters = dict()
    # name of the tag used for grouping
    group_tag = 'groups'

    for server in servers.get_servers():
        metadata = server.metadata
        if metadata:
            try:
                for net in server.addresses.keys():
                    # When looking for the most common network, only consider
                    # ones to which instances with the group_tag are attached
                    if group_tag in metadata:
                        networks[net] += 1

                    # Detect servers with floating IPs
                    for interface in server.addresses.get(net):
                        if (interface.get('OS-EXT-IPS:type') == 'floating'):
                            print("INFO: Server '{}' has a floating IP"
                                  .format(server.name))
                            floaters[server] = interface.get('addr')
                name = server.name

                # Assigns servers to groups based on comma separated values
                # of the `group_tag` metadata tag
                if group_tag in metadata:
                    for group in metadata.get(group_tag).split(','):
                        groupings[group].append(server)
            except Exception as e:
                print('WARNING: Got exception for {}: {}'.format(name, e))
                pass
    # Sort (in descending order) the network counter by its values
    hist_nets = sorted(networks.items(), key=lambda x: x[1], reverse=True)
    print(hist_nets)
    # First element of the first tuple on the list
    # (most instances are connected to this network)
    if hist_nets:
        common_net = hist_nets[0][0]
        print('most common network: ' + common_net)
    else:
        sys.stderr.write('ERROR: No hosts with the "' + group_tag +
                         '" tag found!\n')
        return 1
    print(groupings)

    try:
        # inventory file
        inv_out = open(inv_filename, 'w')
    except Exception as e:
        print(e)

    print('== INVENTORY ==')
    for (group_name, servers) in groupings.items():
        sys.stdout.write('[' + group_name + ']\n')
        inv_out.write('[' + group_name + ']\n')
        for server in servers:
            try:
                # Use floating IP when available
                if floaters and server in floaters.keys():
                    ip = floaters[server]
                else:
                    '''
                    The data structure holding the IPs looks like this:
                    'addresses': {
                      'net0': [{ ... 'addr': 'x.x.x.x', ... }],
                      'net1': [{ ... 'addr': 'y.y.y.y', ... }],
                      ...
                    }
                    '''
                    ip = server.addresses.get(common_net)[0].get('addr')

                line = '{} ansible_host={} ' \
                       'ansible_user=ubuntu ansible_become=yes\n' \
                       .format(server.name, ip)
                sys.stdout.write(line)
                inv_out.write(line)
            except Exception as e:
                print('WARNING: Got exception: {}. Skipping {}'
                      .format(e, server.name))
                pass
        # empty line after each grouping
        sys.stdout.write('\n')
        inv_out.write('\n')
    inv_out.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
