from libcloud.compute.base import NodeImage, NodeSize
from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider, NodeState
import time
from littlechef_rackspace.lib import Host


class RackspaceApi(object):

    def __init__(self, username, password, region):
        self.username = username
        self.password = password
        self.region = region

    def _get_conn(self):
        if self.region is Regions.DFW:
            provider = Provider.RACKSPACE_NOVA_DFW
        else:
            provider = Provider.RACKSPACE_NOVA_ORD

        Driver = get_driver(provider)
        return Driver(self.username, self.password)

    def list_images(self):
        conn = self._get_conn()

        return [{ "id": image.id, "name": image.name}
                for image in conn.list_images()]

    def create_node(self, image_id, flavor_id, node_name, public_key_io, progress=None):
        conn = self._get_conn()
        fake_image = NodeImage(id=image_id, name=None, driver=conn)
        fake_flavor = NodeSize(id=flavor_id, name=None, ram=None, disk=None,
                               bandwidth=None, price=None, driver=conn)

        if progress:
            progress.write("Creating node {0} (image: {1}, flavor: {2})...\n".format(node_name, image_id, flavor_id))

        node = conn.create_node(name=node_name, image=fake_image,
                         size=fake_flavor, ex_files={
                             "/root/.ssh/authorized_keys": public_key_io.read()
                         })
        password = node.extra.get("password")

        if progress:
            progress.write("Created node {0} (id: {1}, password: {2})\n".format(node_name, node.id, password))
            progress.write("Waiting for node to become active")

        while node.state != NodeState.RUNNING:
            time.sleep(5)

            if progress:
                progress.write(".")
            node = conn.ex_get_node_details(node.id)

        # Dumb hack to not select the ipv6 address
        public_ipv4_address = [ip for ip in node.public_ips if ":" not in ip][0]

        if progress:
            progress.write("\n")
            progress.write("Node active! (host: {0})".format(public_ipv4_address))
        return Host(name=node_name,
                    host_string=public_ipv4_address,
                    password=password)

class Regions(object):
    DFW = 0
    ORD = 1