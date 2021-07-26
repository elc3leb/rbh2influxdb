FROM registry.access.redhat.com/ubi8/ubi:8.2

ARG rbh_prefix="/opt/robinhood/3.1.7"
ARG DATABASE_ROOT_PASS

USER root
LABEL maintainer="<your_name>"
ENV container docker

ENV http_proxy=<http://<PROXY>/
ENV https_proxy=<http://<PROXY>/
ENV no_proxy=<IPS_ADDRESS>
ENV CFLAGS="-Wno-error=format"
ENV PATH="/opt/robinhood/3.1.7/sbin/:/opt/robinhood/3.1.7/sbin/:${PATH}"

RUN echo "sslverify=false" >> /etc/yum.conf
RUN (cd /lib/systemd/system/sysinit.target.wants/; \
     for i in *; do [ $i == systemd-tmpfiles-setup.service ] || rm -f $i; done); \
        rm -f /lib/systemd/system/multi-user.target.wants/* && \
        rm -f /etc/systemd/system/*.wants/* && \
        rm -f /lib/systemd/system/local-fs.target.wants/* && \
        rm -f /lib/systemd/system/sockets.target.wants/*udev* && \
        rm -f /lib/systemd/system/sockets.target.wants/*initctl* && \
        rm -f /lib/systemd/system/basic.target.wants:/* && \
        rm -f /lib/systemd/system/anaconda.target.wants/*

RUN unlink /etc/localtime && \
   cd /etc && \
   ln -s /usr/share/zoneinfo/Europe/Paris localtime

RUN mkdir -p /var/lib/mysql

ADD robinhood-3.1.7.tar.gz ${rbh_prefix}/src

COPY container.repo /etc/yum.repos.d/
RUN sed -i 's/enabled=1/enabled=0/' /etc/yum.repos.d/ubi.repo

RUN yum --assumeyes --nobest --nogpgcheck --quiet install @base autoconf automake bison flex glib2-devel jemalloc jemalloc-devel libattr-devel libtool mailx make mariadb-devel mariadb-server rpm-build wget which

RUN cd ${rbh_prefix}/src/robinhood-3.1.7 && \
   autoreconf --install && \
   CFLAGS="-Wno-error=format" ./configure --enable-lustre=yes --prefix="${rbh_prefix}" && \
   make && \
   make install

RUN mkdir ${rbh_prefix}/etc && \
    mkdir ${rbh_prefix}/etc/robinhood.d && \
    mkdir ${rbh_prefix}/log/ && \
    ln -sf -t ${rbh_prefix}/ /rbh/

RUN echo '<PASSWORD>' > ${rbh_prefix}/etc/robinhood.d/.dbpassword

ADD robinhood.sh /robinhood.sh
ADD entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
RUN chmod +x /robinhood.sh

VOLUME [ "/sys/fs/cgroup" ]
VOLUME [ "/rbh" ]

CMD [ "/entrypoint.sh" ]
