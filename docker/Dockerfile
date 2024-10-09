FROM httpd:bullseye
RUN apt -yqq update
RUN apt install -yqq software-properties-common
RUN ln -s /usr/bin/python3.9 /usr/bin/python
RUN apt install -yqq python3-pip && python -m pip install six
RUN apt-get install -yqq supervisor apache2
RUN a2enmod rewrite
RUN a2enmod cgi
ADD apache-config.conf /etc/apache2/sites-enabled/000-default.conf
ADD supervisord.conf /etc/supervisor/conf.d/
CMD ["supervisord"]
