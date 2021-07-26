#!/usr/bin/make

container ?= robinhood
filesystem ?= filesystem
image ?= robinhood

database_root_pass ?= ******

lru_max_age_0 = 3900000
lru_max_age_1 ?= 10000

help:
        @echo ''
        @echo 'Usage: make [command]'
        @echo ''
        @echo 'Commands:'
        @echo ''
        @echo '  build         Build Docker Container'
        @echo '  exec          Open Interactive Session onto Docker Container'
        @echo '  exec-clean    Execute Robinhood Cleanup inside Docker Container'
        @echo '  exec-scan     Execute Robinhood Scan inside Docker Container'
        @echo '  logs          Display Logs for Container'
        @echo '  run           Run Docker Container'
        @echo '  stop          Stop (and Remove) Container'
        @echo ''

build:
        @echo "Building Image: [$(image)]"
        docker build --build-arg DATABASE_ROOT_PASS=$(database_root_pass) --no-cache --tag $(image) .

clean:
        @echo "Executing Robinhood Cleanup on Filesystem: [$(filesystem)]"
        docker exec --tty $(container) /bin/bash robinhood.sh --clean $(filesystem)

exec:
        @echo "Connecting to Container: [$(container)]"
        docker exec --interactive --tty $(container) /bin/bash

exec-clean: run clean influxdb stop flush

exec-scan: run scan stop

logs:
        docker logs $(container)

flush:
        echo > $(filesystem).log

influxdb:
        @echo "Send Run Details to Influxdb"
        /path_to_scripts/bin/rbh2influxdb.py --log $(filesystem).log
        
run:
        @echo "Setting Lustre Parameter: [lru_max_age]=[$(lru_max_age_1)]"
        /usr/sbin/lctl set_param ldlm.namespaces.*.lru_max_age=$(lru_max_age_1)
        @echo "Running Container: [$(container)]"
        docker run --detach \
                --hostname $(container) \
                --name $(container) \
                --privileged \
                --volume ${CURDIR}:/rbh \
                --volume /$(filesystem):/$(filesystem) \
                --volume /sys/fs/cgroup:/sys/fs/cgroup:ro $(image)

scan:
        @echo "Executing Robinhood Scan on Filesystem: [$(filesystem)]"
        docker exec --tty $(container) /bin/bash robinhood.sh --scan $(filesystem)

stop:
        @echo "Setting Lustre Parameter: [lru_max_age]=[$(lru_max_age_0)]"
        /usr/sbin/lctl set_param ldlm.namespaces.*.lru_max_age=$(lru_max_age_0)
        @echo "Stopping Container: [$(container)]"
        docker stop $(container)
        @echo "Removing Container: [$(container)]"
        docker rm $(container)
