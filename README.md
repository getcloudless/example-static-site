# Static Site Service Example

This is an example of creating a service running a static site.  Note that this
blueprint references an image created by the base image scripts at
[https://github.com/getcloudless/example-base-image](https://github.com/getcloudless/example-base-image),
so this will fail unless you run that first.

## Usage

The file at `blueprint.yml` can be used in any service command, and you need to
pass in a `vars.yml` that minimally sets `consul_ips`, `jekyll_site_domain`, and
`jekyll_site_github_url`. Here's an example vars file:

```
---
consul_ips: ["10.0.0.1"]
jekyll_site_domain: "getcloudless.com"
jekyll_site_github_url: "https://github.com/getcloudless/getcloudless.com/"
```

And here's the service creation:

```
cldls service create blueprint.yml vars.yml
```

You can run the service's regression tests with:

```
cldls service-test run service_test_configuration.yml
```

Note that these are completely independent of what provider you're using,
assuming you've already built the [Base
Image](https://github.com/getcloudless/example-base-image).

## SSL Support

This module uses [sslmate](https://sslmate.com/) to configure https.

If you want the regression test to use SSL, you need to set `SSLMATE_API_KEY`,
`SSLMATE_API_ENDPOINT`, and `SSLMATE_PRIVATE_KEY_PATH` to the proper values.
It's recommended that you use the [sslmate
sandbox](https://sslmate.com/help/sandbox) for this.

By default, the tests assume the certificate is for `getcloudless.com` (which
you can get by using the SSLMate sandbox).  If you want to test that your domain
works, set the `STATIC_SITE_TEST_DOMAIN` environment variable.

If you want to use SSL when you deploy, you need to set `use_sslmate` to true in
your `vars.yml` file, and then set `SSLMATE_API_KEY`, `SSLMATE_API_ENDPOINT`,
and `{your_domain}.key` to the proper values on the Consul server that you
provide in `consul_ips`.

## DataDog Monitoring

This module uses [datadog](https://www.datadoghq.com/) for monitoring.

If you want the regression test to test for this, you need to set
`DATADOG_API_KEY` and `DATADOG_APP_KEY` to the proper values. The
`DATADOG_API_KEY` is the same one use use for the agent while the
`DATADOG_APP_KEY` identifies the client (the machine running Cloudless) that's
querying the DataDog API to test whether the service is logging.

If you want to set up monitoring, you need to set `use_datadog` to true in your
`vars.yml` file, and then set `DATADOG_API_KEY` and `DATADOG_APP_KEY` to the
proper values on the Consul server that you provide in `consul_ips`.

## Deploy Script/Python Helpers

There's a python deploy script and python helpers that are partially tested by
the regression test.  For example, to deploy "getcloudless.com" in the "cloudless"
network with a "consul-1" consul service, run:

```shell
$ SERVICE_NAME="web-$(git rev-parse --short HEAD)"
$ python helpers/deploy.py cloudless consul-1 "$SERVICE_NAME" \
    getcloudless.com https://github.com/getcloudless/cloudless "Cloudless"
```

This will deploy the service and make sure that it returns "Cloudless" somewhere
in the response.  You must also have all the datadog and sslmate configuration
set as this script uses those environment variables.  Run with no args for
usage details.

There's also a python script at `helpers/update_dns.py` to update your dns if
you use NS1.  Run with no args or `--help` for usage details.  This script isn't
currently used by the regression tests.

Finally, there's a python script at `helpers/setup_consul.py` to set the proper
configuration on your consul server.  Run with no args or `--help` for usage
details.  This script is used by the regression tests to configure the temporary
consul server.

## Development

The main value of the test framework is that it is focused on the workflow of
actually developing a service.  For example, if you want to deploy a service
(and all its dependencies) that you can work on without running the full test,
you can run:

```
cldls service-test deploy service_test_configuration.yml
```

This command saves the SSH keys locally and will display the SSH command that
you need to run to log into the instance.

Now, say you want to actually check that the service is behaving as expected:

```
cldls service-test check service_test_configuration.yml
```

You can run this as many times as you want until it's working, as you are logged
in.  Finally, clean everything up with:

```
cldls service-test cleanup service_test_configuration.yml
```

You're done!  The run step will run all these steps in order.
