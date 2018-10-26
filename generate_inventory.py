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
        self.client = nova_client.Client(version=2,
                                         session=creds.get_session())

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
    # name of the tag used for grouping
    group_tag = 'groups'

    for server in servers.get_servers():
        metadata = server.metadata
        if metadata:
            try:
                for net in server.addresses.keys():
                    networks[net] += 1
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
    common_net = hist_nets[0][0]
    print('most common network: ' + common_net)
    print(groupings)

    try:
        # inventory file
        inv_out = open(inv_filename, 'w')
    except Exception as e:
        print(e)

    print('== INVENTORY ==')
    for (group_name, servers) in groupings.items():
        print('[' + group_name + ']')
        inv_out.write('[' + group_name + ']\n')
        for server in servers:
            try:
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
                       'ansible_user=ubuntu ansible_become=yes' \
                       .format(server.name, ip)
                print(line)
                inv_out.write(line)
            except Exception as e:
                print('WARNING: Got exception: {}. Skipping {}'
                      .format(e, server.name))
                pass
        # empty line after each grouping
        print('')
        inv_out.write('\n')
    inv_out.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))