FROM debian
RUN apt-get -yqq update
RUN apt-get install -yqq supervisor apache2
RUN a2enmod rewrite
RUN a2enmod cgi
ADD apache-config.conf /etc/apache2/sites-enabled/000-default.conf
ADD supervisord.conf /etc/supervisor/conf.d/
CMD ["supervisord"]
