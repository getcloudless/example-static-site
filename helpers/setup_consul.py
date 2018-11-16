"""
Helper script to set up consul for the static site.
"""
import sys
import os
import consul
from retrying import retry

def check_environment(use_datadog, use_sslmate):
    """
    Check whether the correct environment variables are set.
    """
    if use_sslmate:
        if 'SSLMATE_API_KEY' not in os.environ:
            raise Exception('SSLMATE_API_KEY must be set!')
        if 'SSLMATE_API_ENDPOINT' not in os.environ:
            raise Exception('SSLMATE_API_ENDPOINT must be set!')
        if 'SSLMATE_PRIVATE_KEY_PATH' not in os.environ:
            raise Exception('SSLMATE_PRIVATE_KEY_PATH must be set!')
    if use_datadog:
        if 'DATADOG_API_KEY' not in os.environ:
            raise Exception('DATADOG_API_KEY must be set!')
        if 'DATADOG_APP_KEY' not in os.environ:
            raise Exception('DATADOG_API_KEY must be set!')

def setup_consul(consul_ips, domain, use_datadog, use_sslmate):
    """
    Add necessary configuration to the consul cluster for this static site deployment.
    """
    check_environment(use_datadog, use_sslmate)

    @retry(wait_fixed=10000, stop_max_attempt_number=24)
    def put_with_retries(consul_ip, key, value):
        print("Setting %s on %s..." % (key, consul_ip))
        consul_client = consul.Consul(consul_ip)
        consul_client.kv.put(key, value)
    if use_sslmate:
        put_with_retries(consul_ips[0], 'SSLMATE_API_KEY', os.environ['SSLMATE_API_KEY'])
        put_with_retries(consul_ips[0], 'SSLMATE_API_ENDPOINT', os.environ['SSLMATE_API_ENDPOINT'])
        put_with_retries(consul_ips[0], '%s.key' % domain,
                         open(os.environ['SSLMATE_PRIVATE_KEY_PATH']).read())
    if use_datadog:
        put_with_retries(consul_ips[0], 'DATADOG_API_KEY', os.environ['DATADOG_API_KEY'])

def main():
    """
    Main script entry point.
    """
    if len(sys.argv) != 4:
        print("Usage: %s <consul_ip> <domain> <datadog|sslmate|both|none>" % sys.argv[0])
        sys.exit(1)
    use_sslmate = False
    use_datadog = False
    if sys.argv[3] == "both":
        use_datadog = True
        use_sslmate = True
    elif sys.argv[3] == "datadog":
        use_datadog = True
    elif sys.argv[3] == "sslmate":
        use_sslmate = True
    elif sys.argv[3] != "none":
        raise Exception("Unrecognized argument: %s" % sys.argv[3])
    setup_consul([sys.argv[1]], sys.argv[2], use_datadog, use_sslmate)

if __name__ == '__main__':
    main()
