import os
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


def main():
    creds = Credentials()
    servers = Servers(creds)
    for server in servers.get_servers():
        print(server.name)
        print(server.addresses)
        print(server.metadata)


if __name__ == "__main__":
    main()
