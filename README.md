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

If you want to use SSL, you need to set `use_sslmate` to true in your `vars.yml`
file, and then set `SSLMATE_API_KEY`, `SSLMATE_API_ENDPOINT`, and
`{your_domain}.key` to the proper values on the Consul server that you provide
in `consul_ips`.

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
