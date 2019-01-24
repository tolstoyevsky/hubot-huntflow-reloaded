FROM alpine:3.8
MAINTAINER Evgeny Golyshev <eugulixes@gmail.com>

ENV BRANCH master

ARG VCS_REF

LABEL org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/tolstoyevsky/hubot-huntflow-reloaded"

RUN apk --update add \
    curl \
    bash \
    git \
    python3 \
 && cd \
 && git clone -b $BRANCH https://github.com/tolstoyevsky/hubot-huntflow-reloaded.git \
 && cd hubot-huntflow-reloaded \
 && pip3 install -r server/requirements.txt \
 && cd server/bin \
 && curl -O https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh \
 && chmod +x wait-for-it.sh \
 # Cleanup
 && apk del \
    git \
 && rm -rf /var/cache/apk/*

COPY ./docker-entrypoint.sh /usr/bin/docker-entrypoint.sh

WORKDIR /root/hubot-huntflow-reloaded/server

ENTRYPOINT ["docker-entrypoint.sh"]

