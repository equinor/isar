FROM erlang:23.3

ENV TZ=Europe/Oslo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN \
    apt-get update && \
    apt-get install -y libsnappy-dev

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

WORKDIR /root
COPY /configuration /root/vernemq/etc

ENV VERNEMQ_USER=$VERNEMQ_USER
ENV VERNEMQ_PASSWORD=$VERNEMQ_PASSWORD

CMD /root/vernemq/bin/vernemq start && /bin/bash
