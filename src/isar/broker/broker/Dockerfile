FROM erlang:23.3-slim as build

ENV TZ=Europe/Oslo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN \
    apt-get update && \
    apt-get install -y libsnappy-dev && \
    apt-get -y install git && \
    apt-get -y install make && \ 
    apt-get -y install gcc && \
    apt-get -y install curl && \
    apt-get -y install g++ && \
    apt-get -y install libssl-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /root/
RUN \
    mkdir src && \
    cd src && \
    git clone https://github.com/vernemq/vernemq.git && \
    cd vernemq && \
    git checkout 1.11.0

WORKDIR /root/src/vernemq
RUN make rel

RUN mv ./_build/default/rel/vernemq ~/vernemq
ENV PATH="~/vernemq/bin:$PATH"

FROM erlang:23.3-alpine
WORKDIR /root
COPY --from=build /root/vernemq/ /root/vernemq/
COPY /configuration /root/vernemq/etc

ENV VERNEMQ_USER=$VERNEMQ_USER
ENV VERNEMQ_PASSWORD=$VERNEMQ_PASSWORD

CMD /root/vernemq/bin/vernemq start && /bin/bash
