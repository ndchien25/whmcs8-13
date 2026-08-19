FROM php:8.2-apache-bookworm

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libcurl4-openssl-dev \
    libfreetype6-dev \
    libjpeg62-turbo-dev \
    libpng-dev \
    libgmp-dev \
    libc-client-dev \
    libkrb5-dev \
    libicu-dev \
    libxml2-dev \
    libzip-dev \
    libonig-dev \
    libssl-dev \
    unzip \
    wget \
    cron \
    && rm -rf /var/lib/apt/lists/*

# PHP extensions required by WHMCS 9.0
RUN docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-configure imap --with-kerberos --with-imap-ssl \
    && docker-php-ext-install -j$(nproc) \
        curl \
        gd \
        gmp \
        imap \
        intl \
        mbstring \
        mysqli \
        pdo_mysql \
        soap \
        xml \
        zip \
        opcache

# Install ionCube Loader for PHP 8.2 (required by WHMCS)
RUN cd /tmp \
    && wget https://downloads.ioncube.com/loader_downloads/ioncube_loaders_lin_x86-64.tar.gz \
    && tar xzf ioncube_loaders_lin_x86-64.tar.gz \
    && PHP_EXT_DIR=$(php -r 'echo ini_get("extension_dir");') \
    && cp ioncube/ioncube_loader_lin_8.2.so "$PHP_EXT_DIR/" \
    && echo "zend_extension=ioncube_loader_lin_8.2.so" > /usr/local/etc/php/conf.d/00-ioncube.ini \
    && rm -rf /tmp/ioncube*

# Enable Apache modules
RUN a2enmod rewrite headers expires

# PHP configuration for WHMCS
COPY docker/php.ini /usr/local/etc/php/conf.d/whmcs.ini

# Apache VirtualHost configuration
COPY docker/apache-vhost.conf /etc/apache2/sites-available/000-default.conf

# Set working directory
WORKDIR /var/www/html

# Copy WHMCS into the image so Apache/PHP do not serve files through
# Docker Desktop's slow Windows bind mount.
COPY --chown=www-data:www-data . /var/www/html
RUN rm -rf /var/www/html/docker /var/www/html/.dockerignore

# Entrypoint to fix permissions on startup
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 80

ENTRYPOINT ["entrypoint.sh"]
CMD ["apache2-foreground"]
