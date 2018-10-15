#! /bin/bash

# https://urbanautomaton.com/blog/2014/09/09/redirecting-bash-script-output-to-syslog/
exec 1> >(logger -s -t "$(basename "$0")") 2>&1

{% if cloudless_test_framework_ssh_key %}
adduser "{{ cloudless_test_framework_ssh_username }}" --disabled-password --gecos "Cloudless Test User"
echo "{{ cloudless_test_framework_ssh_username }} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
mkdir /home/{{ cloudless_test_framework_ssh_username }}/.ssh/
echo "{{ cloudless_test_framework_ssh_key }}" >> /home/{{ cloudless_test_framework_ssh_username }}/.ssh/authorized_keys
{% endif %}

apt-get update
apt-get install -y python3-pip
pip3 install python-consul
cat <<EOF > /tmp/fetch_key.py
import consul
consul_client = consul.Consul("{{ consul_ips[0] }}")
dummy_api_key = consul_client.kv.get('dummy_api_key')
print(dummy_api_key[1]["Value"].decode("utf-8").strip())
EOF

python3 /tmp/fetch_key.py >> /tmp/dummy_key.txt

apt-get install -y nginx git ruby-dev build-essential zlib1g-dev
echo Cloning: "{{ jekyll_site_github_url }}"
git clone "{{ jekyll_site_github_url }}"
gem install bundler
cd getcloudless.com/
bundle install
bundle exec jekyll build --destination /var/www/html
