"""
Simple Python Deployment Script for Cloudless!
"""
import os
import sys
import click
import cloudless
import cloudless.profile
from cloudless.types.networking import CidrBlock
from health import check_health

def load_client(profile_name):
    """
    Load the client using the given profile.

    Need to do this outside our client because of
    https://github.com/getcloudless/cloudless/issues/56
    """
    if profile_name:
        profile_name = profile_name
    elif "CLOUDLESS_PROFILE" in os.environ:
        profile_name = os.environ["CLOUDLESS_PROFILE"]
    else:
        profile_name = "default"
    profile = cloudless.profile.load_profile(profile_name)
    if not profile:
        click.echo("Profile: \"%s\" not found." % profile_name)
        click.echo("Try running \"cldls --profile %s init\"." % profile_name)
        sys.exit(1)
    return cloudless.Client(provider=profile['provider'], credentials=profile['credentials'])

@click.command()
@click.argument("network-name")
@click.argument("consul-name")
@click.argument("service-name")
@click.argument("domain")
@click.argument("git-url")
@click.argument("expected-content")
@click.option("--count", default=1, help="Number of web services.")
@click.option("--profile-name", default=None, help="Profile to use.")
# pylint: disable=too-many-arguments,too-many-locals
def deploy(network_name, consul_name, service_name, domain, git_url, expected_content, profile_name,
           count):
    """Deploy the service in the given network in the given profile with health checks."""
    client = load_client(profile_name)
    network = client.network.get(network_name)
    if not network:
        click.echo("Network: \"%s\" not found." % network_name)
        sys.exit(1)
    service = client.service.get(network, service_name)
    if service:
        print("Service: %s already exists!" % service_name)
    else:
        print("Service: %s not found!  Creating." % service_name)
        consul_service = client.service.get(network, consul_name)
        consul_instances = client.service.get_instances(consul_service)
        blueprint_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                      "blueprint.yml")
        blueprint_vars = {
            "jekyll_site_domain": domain,
            "jekyll_site_github_url": git_url,
            "consul_ips": [instance.private_ip for instance in consul_instances],
            "use_sslmate": True,
            "use_datadog": True}
        internet = CidrBlock("0.0.0.0/0")
        service = client.service.create(network, service_name,
                                        blueprint=blueprint_path, count=count,
                                        template_vars=blueprint_vars)
        client.paths.add(service, consul_service, 8500)
        client.paths.add(internet, service, 80)
        client.paths.add(internet, service, 443)
        print("Created service: %s!" % service_name)
        check_health(service, expected_content, use_datadog=True, use_sslmate=True)
        print("")
        print("Deploy Successful!")
        print("")
        print("Public IPs: %s" % [i.public_ip for i in client.service.get_instances(service)])
    print("Use 'cldls service get %s %s' for more info." % (network_name, service_name))

if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    deploy()
