import os
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

    @staticmethod
    def get_all_ips_of(server):
        all_addresses = server.addresses
        ips = [all_addresses[addr][0].get('addr') for addr in all_addresses]
        return sorted(ips)


def main():
    creds = Credentials()
    servers = Servers(creds)
    inventory = defaultdict(list)
    for server in servers.get_servers():
        metadata = server.metadata
        if metadata:
            try:
                name = server.name
                ips = servers.get_all_ips_of(server)
                groups = metadata.get('groups').split(',')
                for group in groups:
                    inventory[group].append((name, ips))
            except Exception as e:
                print('WARNING: Got exception for {}: {}'.format(name, e))
                pass
    print(inventory)


if __name__ == "__main__":
    main()
