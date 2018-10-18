#! /bin/bash

# https://urbanautomaton.com/blog/2014/09/09/redirecting-bash-script-output-to-syslog/
exec 1> >(logger -s -t "$(basename "$0")") 2>&1

{% if cloudless_test_framework_ssh_key %}
adduser "{{ cloudless_test_framework_ssh_username }}" --disabled-password --gecos "Cloudless Test User"
echo "{{ cloudless_test_framework_ssh_username }} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
mkdir /home/{{ cloudless_test_framework_ssh_username }}/.ssh/
echo "{{ cloudless_test_framework_ssh_key }}" >> /home/{{ cloudless_test_framework_ssh_username }}/.ssh/authorized_keys
{% endif %}

# STATIC SECTION: This section has all things that should probably be baked into
# the image or built as containers or something.

# Update Packages
apt-get update

# Install Base Packages
apt-get install -y nginx git

# Install Bundler for Jekyll
apt-get install -y ruby-dev build-essential zlib1g-dev
gem install bundler

# Install Python Script to Pull from Consul
apt-get install -y python3-pip
pip3 install python-consul
cat <<EOF > /tmp/fetch_key.py
import sys
import consul
consul_client = consul.Consul("{{ consul_ips[0] }}")
dummy_api_key = consul_client.kv.get(sys.argv[1])
print(dummy_api_key[1]["Value"].decode("utf-8").strip())
EOF

# Install sslmate (https://sslmate.com/help/cmdline/install)
wget -P /etc/apt/sources.list.d https://sslmate.com/apt/ubuntu1804/sslmate1.list
wget -P /etc/apt/trusted.gpg.d https://sslmate.com/apt/ubuntu1804/sslmate.gpg
apt-get update
apt-get install -y sslmate
mkdir -p /etc/sslmate

# Install Datadog Agent
{% if use_datadog %}
apt-get install -y apt-transport-https
sh -c "echo 'deb https://apt.datadoghq.com/ stable 6' > /etc/apt/sources.list.d/datadog.list"
apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 382E94DE
apt-get update
apt-get install -y datadog-agent
{% endif %}

# DYNAMIC SECTION: This section has all the blocks that take template variables
# or should probably happen at runtime.  This could be done by having
# configuration scripts built into the image (for example, a "configure nginx"
# script that has some defaults set).  As is, these could not be built into the
# base image.

{% if use_sslmate %}
# Install sslmate certificate download script
cat <<EOF > /opt/sslmate_download.sh
cd /etc/sslmate/
export SSLMATE_CONFIG=/etc/sslmate.conf
if sslmate download {{ jekyll_site_domain }}
then
    service nginx restart
fi
EOF
chmod a+x /opt/sslmate_download.sh
{% endif %}

# Configure Nginx
cat <<EOF >| /etc/nginx/sites-available/getcloudless.com.conf
server {
{% if use_sslmate %}
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name _;

    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    ssl_certificate_key /etc/sslmate/getcloudless.com.key;
    ssl_certificate /etc/sslmate/getcloudless.com.chained.crt;

    # Recommended security settings from https://wiki.mozilla.org/Security/Server_Side_TLS
    ssl_ciphers 'ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA256:DHE-RSA-AES256-SHA:ECDHE-ECDSA-DES-CBC3-SHA:ECDHE-RSA-DES-CBC3-SHA:EDH-RSA-DES-CBC3-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:DES-CBC3-SHA:!DSS';
    ssl_dhparam /usr/share/sslmate/dhparams/dh2048-group14.pem;
    ssl_session_timeout 5m;
    ssl_session_cache shared:SSL:5m;
    # Enable this if you want HSTS (recommended)
    add_header Strict-Transport-Security max-age=15768000;
{% else %}
    listen 80 default_server;
    listen [::]:80 default_server;
{% endif %}

    root /var/www/html;

    index index.html index.htm

    server_name _;

    location / {
        # First attempt to serve request as file, then
        # as directory, then fall back to displaying a 404.
        try_files \$uri \$uri/ =404;
    }
}
EOF
ln -s /etc/nginx/sites-available/getcloudless.com.conf \
      /etc/nginx/sites-enabled/getcloudless.com.conf
rm /etc/nginx/sites-enabled/default

# Build Jekyll Site
echo Cloning: "{{ jekyll_site_github_url }}"
git clone "{{ jekyll_site_github_url }}"
cd getcloudless.com/ || exit
bundle install
bundle exec jekyll build --destination /var/www/html

{% if use_sslmate %}
# Configure sslmate
cat <<EOF >| /etc/sslmate.conf
api_key $(python3 /tmp/fetch_key.py SSLMATE_API_KEY)
api_endpoint $(python3 /tmp/fetch_key.py SSLMATE_API_ENDPOINT)
EOF

# Fetch ssl private key first so sslmate can check that it's correct
python3 /tmp/fetch_key.py "{{ jekyll_site_domain }}.key" >> "/etc/sslmate/{{ jekyll_site_domain }}.key"

# Download ssl certificates
/opt/sslmate_download.sh

# Install certificate download as a cron job
# (https://stackoverflow.com/a/16068840)
(crontab -l ; echo "0 1 * * * /opt/sslmate_download.sh") | crontab -
{% endif %}

# Run Datadog Agent And Configure Nginx Integration https://docs.datadoghq.com/integrations/nginx/
{% if use_datadog %}
sh -c "sed \"s/api_key:.*/api_key: $(python3 /tmp/fetch_key.py DATADOG_API_KEY)/\" /etc/datadog-agent/datadog.yaml.example > /etc/datadog-agent/datadog.yaml"
cat <<EOF >| /etc/nginx/conf.d/status.conf
server {
  listen 81;
  server_name localhost;

  access_log off;
  allow 127.0.0.1;
  deny all;

  location /nginx_status {
    stub_status;
  }
}
EOF
cat <<EOF >| /etc/datadog-agent/conf.d/nginx.d/conf.yaml
init_config:
instances:
  - nginx_status_url: http://localhost:81/nginx_status/
EOF
systemctl start datadog-agent
{% endif %}

# Restart nginx
service nginx restart
