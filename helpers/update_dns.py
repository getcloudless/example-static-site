#!/usr/bin/env python
"""
Script to manage DNS via NSONE.
"""

import os
from ns1 import NS1
import click

API_KEY = os.environ["NSONE_CLOUDLESS_API_KEY"]

@click.command()
@click.argument("domain")
@click.argument("ip_address")
@click.option('--subdomain', default="aws", help='Subdomain to modify.')
@click.option('--remove', is_flag=True, help='Remove IP rather than add.')
def manage_dns(domain, ip_address, subdomain, remove):
    """Add or remove an IP to our DNS zone."""
    api = NS1(apiKey=API_KEY)
    zone = api.loadZone(domain)
    record = zone.loadRecord(subdomain, "A")
    answers = [answer["answer"] for answer in record["answers"]]
    print("Old IPs for record '%s.%s': %s" % (subdomain, domain, answers))
    if remove:
        print("Removing IP: %s" % ip_address)
        answers = [answer for answer in answers
                   if answer != ip_address and ip_address not in answer]
    else:
        print("Adding IP: %s" % ip_address)
        answers.append([ip_address])
    print("New IPs for record '%s.%s': %s" % (subdomain, domain, answers))
    record.update(answers=answers)

if __name__ == '__main__':
    #pylint: disable=no-value-for-parameter
    manage_dns()
