FROM debian:stable

RUN apt-get update
RUN apt-get install -y python  wget python-pip libmysqlclient-dev python-dev
RUN pip install mysql-python

RUN wget http://pentest1.soc.ovh.net/dsxs.py 

CMD python dsxs.py
