#!/usr/bin/env bash
set -x

pid=0


# SIGTERM-handler
term_handler() {
  if [ $pid -ne 0 ]; then
    sudo nginx -s stop
    kill -SIGTERM "$pid"
    wait "$pid"
  fi
  exit 143; # 128 + 15 -- SIGTERM
}

# setup handlers
# on callback, kill the last background process, which is `tail -f /dev/null` and execute the specified handler
trap 'kill ${!}; term_handler' SIGTERM

# start nginx
sudo nginx

# run application
uwsgi --ini /usr/uwsgi-nrp.ini --plugin python3 --pyargv "--verbose" &
pid="$!"

# wait forever
while true
do
  tail -f /dev/null & wait ${!}
done
