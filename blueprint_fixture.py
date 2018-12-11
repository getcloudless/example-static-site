"""
Static Site Test Fixture
"""
import os
import requests
from cloudless.testutils.fixture import BlueprintTestInterface, SetupInfo
from cloudless.types.networking import CidrBlock
from helpers.setup_consul import setup_consul, check_environment
from helpers.health import check_health

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

        # For the test framework, check if these environment variables are set.
        use_sslmate = 'SSLMATE_API_KEY' in os.environ
        use_datadog = 'DATADOG_API_KEY' in os.environ
        check_environment(use_sslmate=use_sslmate, use_datadog=use_datadog)

        # Get our domain name
        # Unfortunately we have to do this manually because Cloudless doesn't have a native way to
        # configure parameters.  See https://github.com/getcloudless/cloudless/issues/78
        # We also can't do a random domain, because generating the certificate is done out of band.
        if 'STATIC_SITE_TEST_DOMAIN' in os.environ:
            domain_name = os.environ['STATIC_SITE_TEST_DOMAIN']
        else:
            domain_name = "getcloudless.com"

        # Now let's add any necessary API keys to Consul.
        my_ip = requests.get("http://ipinfo.io/ip")
        test_machine = CidrBlock(my_ip.content.decode("utf-8").strip())
        self.client.paths.add(test_machine, service, 8500)
        consul_ips = [i.public_ip for s in service.subnetworks for i in s.instances]
        setup_consul(consul_ips, domain_name, use_sslmate=use_sslmate, use_datadog=use_datadog)
        self.client.paths.remove(test_machine, service, 8500)

        blueprint_variables = {
            "consul_ips": [i.private_ip for s in service.subnetworks for i in s.instances],
            "jekyll_site_github_url": "https://github.com/getcloudless/getcloudless.com.git",
            "jekyll_site_domain": domain_name}

        if use_sslmate:
            blueprint_variables["use_sslmate"] = True
        if use_datadog:
            blueprint_variables["use_datadog"] = True

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
        self.client.paths.add(test_machine, service, 80)
        self.client.paths.add(test_machine, service, 443)
        # Add this last because we want to make sure that our service can handle a delay before
        # getting connectivity to consul.
        self.client.paths.add(service, consul_service, 8500)

    def verify(self, network, service, setup_info):
        """
        Given the network name and the service name of the service under test,
        verify that it's behaving as expected.
        """
        use_sslmate = ("use_sslmate" in setup_info.blueprint_vars and
                       setup_info.blueprint_vars["use_sslmate"])
        use_datadog = 'DATADOG_API_KEY' in os.environ
        expected_content = "Cloudless"
        check_health(service, expected_content, use_datadog, use_sslmate)
