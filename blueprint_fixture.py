"""
Static Site Test Fixture
"""
import os
from retrying import retry
import requests
import consul
from cloudless.testutils.blueprint_tester import call_with_retries
from cloudless.testutils.fixture import BlueprintTestInterface, SetupInfo
from cloudless.types.networking import CidrBlock

SERVICE_BLUEPRINT = os.path.join(os.path.dirname(__file__), "example-consul/blueprint.yml")

RETRY_DELAY = float(10.0)
RETRY_COUNT = int(60)

class BlueprintTest(BlueprintTestInterface):
    """
    Fixture class that creates the dependent resources.
    """
    def setup_before_tested_service(self, network):
        """
        Create the dependent services needed to test this service.
        """
        # Create consul since our web server needs it to pull API keys.
        service_name = "consul"
        service = self.client.service.create(network, service_name, SERVICE_BLUEPRINT, count=1)

        use_sslmate = 'SSLMATE_API_KEY' in os.environ

        @retry(wait_fixed=5000, stop_max_attempt_number=24)
        def add_api_keys(service):
            public_ips = [i.public_ip for s in service.subnetworks for i in s.instances]
            assert public_ips, "No services are running..."
            for public_ip in public_ips:
                consul_client = consul.Consul(public_ip)
                if use_sslmate:
                    consul_client.kv.put('SSLMATE_API_KEY', os.environ['SSLMATE_API_KEY'])
                    consul_client.kv.put('SSLMATE_API_ENDPOINT', os.environ['SSLMATE_API_ENDPOINT'])
                    consul_client.kv.put('getcloudless.com.key',
                                         open(os.environ['SSLMATE_PRIVATE_KEY_PATH']).read())
            return True

        # Now let's add any necessary API keys to Consul.
        my_ip = requests.get("http://ipinfo.io/ip")
        test_machine = CidrBlock(my_ip.content.decode("utf-8").strip())
        self.client.paths.add(test_machine, service, 8500)
        add_api_keys(service)
        self.client.paths.remove(test_machine, service, 8500)

        blueprint_variables = {
            "consul_ips": [i.private_ip for s in service.subnetworks for i in s.instances],
            "jekyll_site_github_url": "https://github.com/getcloudless/getcloudless.com.git",
            "jekyll_site_domain": "getcloudless.com"}

        if use_sslmate:
            blueprint_variables["use_sslmate"] = True

        return SetupInfo(
            {"service_name": service_name},
            blueprint_variables)

    def setup_after_tested_service(self, network, service, setup_info):
        """
        Do any setup that must happen after the service under test has been
        created.
        """
        consul_service_name = setup_info.deployment_info["service_name"]
        consul_service = self.client.service.get(network, consul_service_name)
        my_ip = requests.get("http://ipinfo.io/ip")
        test_machine = CidrBlock(my_ip.content.decode("utf-8").strip())
        self.client.paths.add(service, consul_service, 8500)
        self.client.paths.add(test_machine, service, 80)
        self.client.paths.add(test_machine, service, 443)

    def verify(self, network, service, setup_info):
        """
        Given the network name and the service name of the service under test,
        verify that it's behaving as expected.
        """
        use_sslmate = ("use_sslmate" in setup_info.blueprint_vars and
                       setup_info.blueprint_vars["use_sslmate"])
        def check_responsive():
            public_ips = [i.public_ip for s in service.subnetworks for i in s.instances]
            assert public_ips
            for public_ip in public_ips:
                if use_sslmate:
                    # Don't verify the certificate so we can test using the sslmate sandbox
                    response = requests.get("https://%s" % public_ip, verify=False)
                else:
                    response = requests.get("http://%s" % public_ip)
                expected_content = "Cloudless"
                assert response.content, "No content in response"
                assert expected_content in str(response.content), (
                    "Unexpected content in response: %s" % response.content)

        call_with_retries(check_responsive, RETRY_COUNT, RETRY_DELAY)
