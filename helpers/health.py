"""
Helper script to check health of static site.
"""
import sys
import os
import time
import requests
from retrying import retry
from datadog import initialize, api
from collections import namedtuple

def print_and_raise(message):
    """
    Helper to print an error before raising an exception.  Could probably use the retrying library
    to do this, but really should probably have some custom decarator in Cloudless that can make
    this nicer for the user.
    """
    print("Error: %s" % message)
    raise Exception(message)

def check_health(service, expected_content, use_datadog, use_sslmate):
    """
    Check that a service is working properly, optionally with datadog and sslmate.
    """
    instances = [i for s in service.subnetworks for i in s.instances]
    @retry(wait_fixed=10000, stop_max_attempt_number=24)
    def check_responsive():
        for instance in instances:
            if use_sslmate:
                # Don't verify the certificate so we can test using the sslmate sandbox
                check_url = "https://%s" % instance.public_ip
                print("Checking url: %s" % check_url)
                response = requests.get(check_url, verify=False)
            else:
                check_url = "http://%s" % instance.public_ip
                print("Checking url: %s" % check_url)
                response = requests.get(check_url)
            if not response.content:
                print_and_raise("No content in response")
            if expected_content not in str(response.content):
                print_and_raise("Unexpected content in response: %s" % response.content)

    @retry(wait_fixed=10000, stop_max_attempt_number=24)
    def is_agent_reporting(private_ip):
        print("Checking to see if agent is reporting for host: %s." % private_ip)
        end_time = time.time()
        # Just go ten minutes back
        start_time = end_time - 6000
        events = api.Event.query(
            start=start_time,
            end=end_time,
            priority="normal"
        )
        def check_event_match(event):
            for tag in event['tags']:
                if tag == "private_ip:%s" % private_ip:
                    return True
            if 'is_aggregate' in event and event['is_aggregate']:
                for child in event['children']:
                    child_event = api.Event.get(child['id'])
                    if check_event_match(child_event['event']):
                        return True
            return False
        for event in events['events']:
            if check_event_match(event):
                return True
        print_and_raise("Could not find this instance in datadog events!  %s" % events)

    @retry(wait_fixed=10000, stop_max_attempt_number=24)
    def is_agent_sending_metrics(query, query_type, private_ip):
        print("Checking query: %s to check for %s metrics." % (query, query_type))
        now = int(time.time())
        series = api.Metric.query(start=now - 600, end=now, query=query)
        for datapoint in series['series']:
            if datapoint['scope'] == "private_ip:%s" % private_ip:
                return
            # Delete this because we don't care about it here and it muddies the error message
            del datapoint['pointlist']
        print_and_raise("No %s stats in datadog metrics for this instance!  %s" % (query_type,
                                                                                   series))

    check_responsive()
    if use_datadog:
        options = {
            'api_key': os.environ['DATADOG_API_KEY'],
            'app_key': os.environ['DATADOG_APP_KEY']
        }

        initialize(**options)

        for instance in instances:
            is_agent_reporting(instance.private_ip)
            is_agent_sending_metrics('nginx.net.connections{*}by{private_ip}', 'nginx',
                                     instance.private_ip)
            is_agent_sending_metrics('consul.catalog.total_nodes{*}by{private_ip}', 'consul',
                                     instance.private_ip)

def main():
    """
    Main script entry point.
    """
    if len(sys.argv) != 5:
        print(("Usage: %s <service_private_ip> <service_public_ip> <expected_content> "
               "<datadog|sslmate|both|none>") % sys.argv[0])
        sys.exit(1)
    Service = namedtuple('Service', 'subnetworks')
    Subnetwork = namedtuple('Subnetwork', 'instances')
    Instance = namedtuple('Instance', 'private_ip public_ip')
    private_ip = sys.argv[1]
    public_ip = sys.argv[2]
    expected_content = sys.argv[3]
    mode = sys.argv[4]
    use_sslmate = False
    use_datadog = False
    if mode == "both":
        use_datadog = True
        use_sslmate = True
    elif mode == "datadog":
        use_datadog = True
    elif mode == "sslmate":
        use_sslmate = True
    elif mode != "none":
        raise Exception("Unrecognized mode argument: %s" % mode)
    check_health(Service([Subnetwork([Instance(private_ip, public_ip)])]), expected_content,
                 use_datadog, use_sslmate)

if __name__ == '__main__':
    main()
